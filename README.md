# 대출 서류 AI 분류기

여러 대출 서류가 섞인 PDF를 올리면 다음을 수행하는 Streamlit 앱입니다.

1. 페이지별 문서 유형 분류: `URLA_1003`, `INCOME_DOC`, `CREDIT_REPORT`, `TITLE_REPORT`, `OTHER`
2. 연속된 같은 유형의 페이지를 하나의 문서로 그룹화
3. 문서 단위 결과를 화면, JSON, CSV로 제공

## 1. 필요 환경

- macOS, Windows 또는 Linux
- Python 3.9 이상
- 사용 AI모델(로컬): Ollama gemma3
- 선택 사항: OpenAI API 키 (OpenAI 분석 모드에서만 필요)

## 2. 실행

1. Ollama 설치 (다운로드 링크:https://ollama.com/download)
2. 아래 쉘 명령어 입력
```bash
python -m venv .venv (python명령어 오류 시 python3 사용)
source .venv/bin/activate
pip install -r requirements.txt (pip명령어 오류 시 pip3 사용)
(필요 시 선택사항) export OPENAI_API_KEY="your_api_key"
ollama pull gemma3
streamlit run app.py
```

브라우저가 열리면 PDF를 올리고 **AI로 분류 시작**을 누르세요. API 키는 환경 변수 대신 왼쪽 설정란에 입력해도 됩니다.

## API 키 없이 로컬 AI로 분석하기

1. [Ollama](https://ollama.com/download)를 설치하고 실행합니다.
2. 터미널에서 비전 모델을 한 번 내려받습니다.

```bash
ollama pull gemma3
```

3. 앱에서 PDF를 올린 뒤 **로컬 AI로 전체 분석**을 누릅니다.

모델은 모든 페이지 이미지를 로컬에서 분석하므로 OpenAI API 키나 외부 전송이 필요 없습니다.
Ollama가 실행 중이지 않거나 모델이 설치되지 않았으면 앱이 안내 메시지를 표시합니다.

`demo_result.json`에는 과제 요구사항을 보여 주는 예시 결과가 들어있습니다.
제공된 샘플 PDF를 실제 AI로 분석한 결과로 교체해서 제출하면 됩니다. API 키와 `.env` 파일은 제출물에 포함하지 마세요.

## 결과 예시

```json
{
  "documents": [
    {
      "document_type": "URLA_1003",
      "start_page": 1,
      "end_page": 2
    },
    {
      "document_type": "INCOME_DOC",
      "start_page": 3,
      "end_page": 4
    }
  ]
}
```

## 구현 메모

- PDF 각 페이지를 이미지로 렌더링한 뒤, AI가 페이지의 제목·양식·내용을 보고 분류합니다.
- 같은 유형이 연속될 때만 하나의 문서로 묶습니다. 따라서 `A → B → A`는 세 개의 문서 묶음입니다.
- 문서 안의 `Page 1 of 5` 또는 `Page 1 to 5` 표기는 자동으로 읽어 `start_page`, `end_page`, `pages`에 반영합니다. 페이지 표기가 없으면 세 항목은 모두 `1`로 표시하며, 원본 PDF 기준 위치는 `pdf_pages`에서 확인합니다.
- 실제 제출에서는 제공된 샘플 PDF로 결과를 검증하고, 낮은 신뢰도 페이지를 사람이 검토하는 흐름을 추가하면 좋습니다.

## 2. 사용한 기술 스택
개발 AI툴: ChatGPT 5.6 Terra (추론 강도: 중간)
- 모델에는 Luna,Terra,Sol이 있으며, Sol의 경우 성능에 있어서 코딩에 가장 적합한 모델이긴 하나, 속도에 있어서는 가장 느리고 복잡한 코딩 위주 모델이므로 그 중간급인 Terra가 코딩테스트에 가장 적합한 모델로 판단하여 선택함.
- 추론 강도가 너무 높을 경우 모델 토큰 소진량이 빨라 효율이 떨어지기에 개발에 필요한 만큼만 설정함.
사용 언어: Python
- AI개발엔 여러 라이브러리가 필요한데, C,Java,C++로는 해당 라이브러리들을 구현하는 데 한계가 있으며, 개발 난이도가 매우 복잡한 경향이 있음.
- 따라서 구현에 필요한 여러 라이브러리를 import하기에 쉽고 유리한 Python언어를 선택함.
사용 라이브러리: Streamlit, PyMuPDF, Json, csv
- Streamlit: 웹 화면을 구현하며, PDF 업로드와, 진행률 표시, 표, 다운로드 기능을 짧은 코드로 제공. html,css,javascript없이 웹 페이지 화면을 구현할 수 있다.
- PyMuPDF(flitz): 업로드한 PDF의 페이지를 읽고 이미지로 렌더링하고 텍스트로 추출한다.
- Json, csv: AI분석결과를 각각의 파일로 저장하는 역할을 한다.
사용 AI모델: Ollama gemma3
- OpenAI의 ChatGPT와 Gemini의 경우 API키가 필요하며, 해당 API키를 사용하려면 사용한 만큼 비용이 발생하는 문제가 있어 API키 없이 로컬에서도 작동되는 LLM인 Ollama의 gemma3를 선택함.
- gemma4의 경우 파일 용량이 크며, 분석 시간이 오래 걸리고 분석 결과가 gemma3랑 크게 차이가 없는 모습을 보여 분석 시간이 비교적 짧은 gemma3를 선택함.

## 3. 문제 해결 접근 방식 및 처리 흐름

```text
PDF 업로드
  → 페이지별 이미지 렌더링
  → 비전 AI가 각 페이지를 5개 유형 중 하나로 분류
  → 페이지 번호 순서대로 연속된 동일 유형을 그룹화
  → 문서 시작/끝 페이지 및 평균 신뢰도 계산
  → 화면 표와 JSON/CSV로 결과 제공
```

## 4. package_01 기준 자체 측정 정확도 (측정 방법 포함)

- average_confidence 기준 0.95~0.98의 수치를 보여줌.

## 5. 현재 구현의 한계 및 개선 방향
- 여러 번 AI분석을 시도해 보았으나, 전체 페이지가 10페이지가 넘어갈 경우 페이지를 인식 못하는 문제가 발생하여 render_page부분의 matrix값을 1.0에서 1.5로 높이는 등 여러 시도를 하였으나, matrix값을 높일수록 인식 범위가 높아지는 대신 분석 정확도가 떨어지는 문제가 있어 이러한 부분에 대한 보완이 필요함.
- package_01의 분석결과, 오분석이 많아 
