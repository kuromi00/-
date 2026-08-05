import base64
import csv
import io
import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from dataclasses import asdict, dataclass

import fitz  # PyMuPDF
import streamlit as st
from openai import OpenAI


LABELS = {
    "URLA_1003": "Uniform Residential Loan Application (Form 1003) / 대출 신청서",
    "INCOME_DOC": "Paystub, W-2, 1040, 1099, VOE 등 소득 증빙",
    "CREDIT_REPORT": "Tri-merge Credit Report / 신용 보고서",
    "TITLE_REPORT": "Title Commitment 또는 Preliminary Title Report / 권원 보고서",
    "OTHER": "위 항목에 속하지 않거나 판별이 어려운 페이지",
}
BASE_DIR = Path(__file__).resolve().parent
DEMO_RESULT_PATH = BASE_DIR / "demo_result.json"

SYSTEM_PROMPT = """You classify one page from a US mortgage-loan document package.
Choose exactly one label from: URLA_1003, INCOME_DOC, CREDIT_REPORT, TITLE_REPORT, OTHER.
Use the visual layout and readable document text. Do not infer a label merely from a borrower name.
Return valid JSON only, with keys label, confidence (0 to 1), and reason (a short Korean explanation).
"""
OLLAMA_PROMPT = SYSTEM_PROMPT + "\nClassify this image now."


@dataclass
class PageResult:
    page: int
    label: str
    confidence: float
    reason: str


def render_page(page: fitz.Page, zoom: float = 1.5) -> bytes:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return pix.tobytes("png")


def parse_classification(raw: str) -> tuple[str, float, str]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    result = json.loads(raw)
    label = result.get("label", "OTHER")
    if label not in LABELS:
        label = "OTHER"
    return label, max(0, min(1, float(result.get("confidence", 0)))), str(result.get("reason", ""))


def classify_page(client: OpenAI, image_bytes: bytes, model: str) -> tuple[str, float, str]:
    image_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "input_text", "text": "Classify this page."}, {"type": "input_image", "image_url": image_url, "detail": "high"}]},
        ],
    )
    return parse_classification(response.output_text)


def classify_page_ollama(image_bytes: bytes, model: str, host: str) -> tuple[str, float, str]:
    """Ollama의 로컬 REST API로 PDF 페이지 이미지를 비전 AI 분석합니다."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": OLLAMA_PROMPT, "images": [base64.b64encode(image_bytes).decode("ascii")]}],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
    }
    request = Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_classification(payload["message"]["content"])


def classify_page_demo(page: fitz.Page) -> tuple[str, float, str]:
    """API 키 없이 업로드한 PDF 전체를 시연하기 위한 로컬 판정기입니다."""
    text = page.get_text("text").lower()
    rules = [
        ("URLA_1003", ["uniform residential loan application", "form 1003", "url a", "urla"], "대출 신청서 양식 관련 문구"),
        ("CREDIT_REPORT", ["credit report", "credit score", "equifax", "experian", "transunion"], "신용 보고서 관련 문구"),
        ("TITLE_REPORT", ["title commitment", "preliminary title", "title report", "vesting"], "권원 보고서 관련 문구"),
        ("INCOME_DOC", ["paystub", "pay stub", "w-2", "wage and tax statement", "form 1040", "1099", "verification of employment"], "소득 증빙 관련 문구"),
    ]
    for label, keywords, reason in rules:
        matched = [keyword for keyword in keywords if keyword in text]
        if matched:
            return label, 0.80, f"데모 판정: {reason}를 확인했습니다 ({matched[0]})."
    if not text.strip():
        return "OTHER", 0.30, "데모 판정: 스캔 이미지 페이지여서 추출 가능한 텍스트가 없습니다."
    return "OTHER", 0.45, "데모 판정: 지정된 문서 유형을 가리키는 대표 문구를 찾지 못했습니다."


def group_pages(pages: list[PageResult]) -> list[dict]:
    groups = []
    for result in pages:
        if not groups or groups[-1]["document_type"] != result.label:
            groups.append({
                "document_type": result.label,
                "document_name": LABELS[result.label],
                "start_page": result.page,
                "end_page": result.page,
                "pages": [result.page],
                "average_confidence": result.confidence,
            })
        else:
            group = groups[-1]
            group["end_page"] = result.page
            group["pages"].append(result.page)
            count = len(group["pages"])
            group["average_confidence"] = round(
                ((group["average_confidence"] * (count - 1)) + result.confidence) / count, 3
            )
    return groups


def csv_bytes(groups: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["document_type", "document_name", "start_page", "end_page", "pages", "average_confidence"])
    writer.writeheader()
    writer.writerows([{**group, "pages": ",".join(map(str, group["pages"]))} for group in groups])
    return output.getvalue().encode("utf-8-sig")


def load_demo_results() -> tuple[list[PageResult], list[dict]]:
    data = json.loads(DEMO_RESULT_PATH.read_text(encoding="utf-8"))
    pages = [PageResult(**item) for item in data["pages"]]
    return pages, data["documents"]


st.set_page_config(page_title="대출 서류 AI 분류", page_icon="📄", layout="wide")
st.title("📄 대출 서류 AI 분류기")
st.caption("하나의 PDF에서 페이지 유형을 판별하고, 연속된 같은 유형의 페이지를 문서 단위로 묶습니다.")

with st.sidebar:
    st.header("설정")
    api_key = st.text_input("OpenAI API Key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
    model = st.text_input("모델", value=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    st.caption("API 키는 이 실행 세션에서만 사용되며 저장하지 않습니다.")
    st.divider()
    st.subheader("로컬 AI (Ollama)")
    ollama_model = st.text_input("Ollama 비전 모델", value=os.getenv("OLLAMA_MODEL", "gemma3"))
    ollama_host = st.text_input("Ollama 주소", value=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    st.caption("Ollama와 비전 모델이 설치돼 있으면 API 키 없이 분석합니다.")

uploaded = st.file_uploader("분류할 PDF를 올려주세요", type="pdf")

# demo_col, _ = st.columns([1, 3])
# with demo_col:
#     use_demo = st.button("데모 결과 보기")

# if use_demo:
#     st.session_state["results"], st.session_state["groups"] = load_demo_results()
#     st.session_state["result_source"] = "saved_demo"
#     st.success("API 키 없이 사전 생성된 데모 결과를 불러왔습니다.")

if uploaded:
    document = fitz.open(stream=uploaded.getvalue(), filetype="pdf")
    st.info(f"총 {len(document)}페이지를 찾았습니다.")
    action_col, ollama_action_col, demo_action_col = st.columns(3)
    with action_col:
        run_ai = st.button("AI로 분류 시작", type="primary")
    with ollama_action_col:
        run_ollama = st.button("로컬 AI로 전체 분석")
    with demo_action_col:
        run_pdf_demo = st.button("데모 모드: 전체 페이지 분석")

    if run_pdf_demo:
        results = []
        progress = st.progress(0, text="업로드한 PDF의 모든 페이지를 데모 분석 중")
        for index, page in enumerate(document):
            label, confidence, reason = classify_page_demo(page)
            results.append(PageResult(index + 1, label, confidence, reason))
            progress.progress((index + 1) / len(document), text=f"{index + 1}/{len(document)} 페이지 판정 완료")
        st.session_state["results"] = results
        st.session_state["groups"] = group_pages(results)
        st.session_state["result_source"] = "uploaded_demo"
        progress.empty()
        st.success(f"업로드한 PDF의 전체 {len(document)}페이지 결과를 생성했습니다.")

    if run_ollama:
        results = []
        progress = st.progress(0, text="로컬 AI가 모든 페이지를 분석 중입니다.")
        try:
            for index, page in enumerate(document):
                label, confidence, reason = classify_page_ollama(render_page(page), ollama_model, ollama_host)
                results.append(PageResult(index + 1, label, confidence, reason))
                progress.progress((index + 1) / len(document), text=f"{index + 1}/{len(document)} 페이지 AI 분석 완료")
        except (URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            progress.empty()
            st.error(f"로컬 AI 분석에 실패했습니다: {exc}")
            st.info(f"Ollama 앱을 실행한 뒤 터미널에서 `ollama pull {ollama_model}`로 비전 모델을 받아 주세요.")
        else:
            st.session_state["results"] = results
            st.session_state["groups"] = group_pages(results)
            st.session_state["result_source"] = "ollama"
            progress.empty()
            st.success(f"로컬 AI가 업로드한 PDF의 전체 {len(document)}페이지를 분석했습니다.")

    if run_ai:
        if not api_key:
            st.error("OpenAI API Key를 입력해 주세요.")
        else:
            client = OpenAI(api_key=api_key)
            results: list[PageResult] = []
            progress = st.progress(0, text="페이지를 준비하고 있습니다.")
            try:
                for index, page in enumerate(document):
                    image = render_page(page)
                    label, confidence, reason = classify_page(client, image, model)
                    results.append(PageResult(index + 1, label, confidence, reason))
                    progress.progress((index + 1) / len(document), text=f"{index + 1}/{len(document)} 페이지 분석 중")
            except Exception as exc:
                st.error(f"분석 중 오류가 발생했습니다: {exc}")
                st.stop()

            groups = group_pages(results)
            st.session_state["results"] = results
            st.session_state["groups"] = groups
            st.session_state["result_source"] = "ai"
            progress.empty()

if "groups" in st.session_state:
    results = st.session_state["results"]
    groups = st.session_state["groups"]
    if st.session_state.get("result_source") == "uploaded_demo":
        st.warning("데모 모드는 업로드한 PDF의 모든 페이지를 텍스트 규칙으로 판정합니다. 실제 AI 분류 결과는 API 키를 입력한 뒤 ‘AI로 분류 시작’을 사용하세요.")
    elif st.session_state.get("result_source") == "ollama":
        st.success("결과는 내 컴퓨터에서 실행된 Ollama 로컬 비전 AI가 생성했습니다. OpenAI API 키는 사용하지 않았습니다.")
    st.subheader("문서 단위 결과")
    st.dataframe(groups, use_container_width=True, hide_index=True)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("JSON 다운로드", json.dumps({"documents": groups}, ensure_ascii=False, indent=2), "classification_result.json", "application/json")
    with col2:
        st.download_button("CSV 다운로드", csv_bytes(groups), "classification_result.csv", "text/csv")

    st.subheader("페이지별 판정")
    st.dataframe([asdict(item) | {"document_name": LABELS[item.label]} for item in results], use_container_width=True, hide_index=True)
