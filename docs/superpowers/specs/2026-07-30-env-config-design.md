# .env 기반 설정 관리 개선 설계

**날짜**: 2026-07-30
**범위**: 최소 범위 — `.env` 로딩 연결 + 문서화된 환경 변수와 코드 일치화

## 배경 / 문제

- `python-dotenv`가 `requirements.txt`에 있지만 `load_dotenv()` 호출이 코드 어디에도 없다. 루트에 `.env`를 만들어도 로컬 실행 시 무시되며, `OPENAI_API_KEY`를 셸에서 직접 export해야만 동작한다 (Docker는 compose의 `env_file`이 주입해줘서 동작).
- `env.example`에 문서화된 변수들이 코드에서 무시된다: `academic_rag_api.py`는 `API_PORT`와 무관하게 `port=5000` 하드코딩.
- Streamlit Step 2·API Test 페이지에 기본 API URL `http://localhost:5000`이 하드코딩되어 있다.
- `env.example`에 죽은 변수가 있다: `MILVUS_PORT`(Milvus Lite는 포트 없음), `FLASK_ENV`/`FLASK_APP`(어디서도 안 씀), `STREAMLIT_PORT`(Streamlit이 인식하지 못하는 이름), `PYTHONPATH`(compose가 직접 설정).
- 별개 버그: `docker_dir/docker-compose.yml`이 존재하지 않는 `streamlit/streamlit_page.py`를 실행한다 (현재 진입점은 `streamlit/Home.py`).

## 설계 결정

- **구현 방식**: 진입점별 `load_dotenv()` (공용 settings 모듈은 만들지 않음 — 최소 범위 유지)
- **기본값 정책**: 모든 변수 미설정 시 기존 동작(5000, 8501, localhost)과 동일. `.env` 파일이 없어도 `load_dotenv`는 조용히 넘어가므로 기존 사용자 워크플로 무변경.
- **conda 환경 이름, 모델명 등은 범위 외** (기존 `CONDA_BASE_PATH`, `CONDA_ENV_<NAME>_PYTHON` override 장치 유지).

## 변경 사항

### 1. 진입점에 `.env` 로딩 추가

각 파일 상단에 `load_dotenv(<프로젝트 루트>/.env)` 추가:

| 파일 | 추가 내용 |
|------|-----------|
| `academic_rag_api.py` | `load_dotenv()` + `API_PORT = int(os.getenv("API_PORT", "5000"))`를 `app.run()`과 시작 안내 출력문에 적용. 시작 시 `OPENAI_API_KEY` 미설정이면 명확한 경고 출력 |
| `streamlit/utils.py` | 모든 페이지가 import하므로 여기서 한 번 로딩 (루트 `.env` 경로는 `Path(__file__).parent.parent / ".env"`). `get_default_api_url()` 헬퍼 추가 |
| `datamorgana/datamorgana_generator.py` | 독립 실행 대비 로딩 추가 (현재 `os.getenv("OPENAI_API_KEY")`를 import 시점에 읽음) |

`get_default_api_url()` 우선순위: `RAG_API_URL` → `http://localhost:{API_PORT}` → `http://localhost:5000`

### 2. 하드코딩 URL 교체

- `streamlit/pages/2_Step_2_RAG_Inference.py` — 입력란 기본값(51행), 세션 기본값(171행) → `get_default_api_url()`
- `streamlit/pages/4_API_Test.py` — 입력란 기본값(45행) → `get_default_api_url()`
- UI에서 사용자가 덮어쓰는 동작은 그대로 유지.

### 3. env.example 재작성

```bash
# ── 공통 (필수) ──
OPENAI_API_KEY=your_openai_api_key_here

# ── 로컬 실행 (선택, 기본값 있음) ──
API_PORT=5000                        # Baseline RAG API 포트 (Docker에서는 5000 유지)
RAG_API_URL=http://localhost:5000    # Streamlit이 호출할 RAG API 기본 URL
STREAMLIT_SERVER_PORT=8501           # Streamlit 네이티브 변수

# ── Docker 전용 ──
# VERSION=latest                     # compose 이미지 태그 (rag-eval-framework:v${VERSION})
```

- 삭제: `MILVUS_PORT`, `FLASK_ENV`, `FLASK_APP`, `PYTHONPATH`, `STREAMLIT_PORT`
- 추가: `RAG_API_URL`, `STREAMLIT_SERVER_PORT`, `VERSION`(주석, compose가 실제로 읽음)

### 4. docker-compose.yml 버그 수정

`streamlit run streamlit_page.py` → 루트 기준 `streamlit run Home.py` (compose command가 `cd streamlit` 후 실행하므로 `Home.py`). 한 줄 수정.

### 5. 문서 갱신

- `README.md` 환경 변수 표를 새 변수 목록과 일치시킴
- `academic_rag_api_README.md` 환경 변수 절의 "코드는 포트 5000 고정" 문구를 `API_PORT` 반영으로 수정

## 에러 처리

- 변수 미설정·`.env` 부재 시 전부 기존 기본값으로 동작 (하위 호환).
- `OPENAI_API_KEY` 미설정 시: API 서버 시작 시 경고 출력 (서버는 기동하되, 어떤 변수가 왜 필요한지 안내). 기존에는 첫 요청에서야 OpenAI SDK 에러가 발생했다.

## 검증

1. `.env` 없이 `python academic_rag_api.py` → 기존과 동일하게 5000 포트 기동
2. `API_PORT=5001 python academic_rag_api.py` → 5001 포트 기동, 안내 출력문에도 5001 표시
3. `RAG_API_URL=http://example:9999` 설정 후 Streamlit Step 2·API Test 페이지 기본 URL 반영 확인
4. `OPENAI_API_KEY` 미설정 시 시작 경고 출력 확인
5. `docker compose config`로 compose 문법 유효성 확인
