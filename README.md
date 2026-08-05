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

## API 키 없이 시연하기

첫 화면의 **데모 결과 보기**를 누르면 `demo_result.json`에 포함된 사전 생성 예시 결과를 즉시 확인할 수 있습니다.
이 모드는 API 키와 인터넷 연결이 필요 없으며, 평가자가 분류표·그룹화·JSON/CSV 내려받기 흐름을 확인하기 위한 용도입니다.

PDF를 직접 올린 경우에는 **데모 모드: 전체 페이지 분석**을 누르세요.
업로드한 PDF의 모든 페이지를 로컬 텍스트 규칙으로 판정하고, 페이지별 결과와 문서 그룹 결과를 보여 줍니다. 스캔 이미지처럼 텍스트가 없는 페이지는 `OTHER`로 표시될 수 있습니다.

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
- 실제 제출에서는 제공된 샘플 PDF로 결과를 검증하고, 낮은 신뢰도 페이지를 사람이 검토하는 흐름을 추가하면 좋습니다.

## 3. 사용한 기술 스택
사용 언어: Python
- AI개발엔 여러 라이브러리가 필요한데, C,Java,C++로는 해당 라이브러리들을 구현하는 데 한계가 있음.
- 여러 라이브러리를 import하기에 쉽고 유리한 Python언어를 선택함.
