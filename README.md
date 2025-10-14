# RAG 평가 프레임워크 - Streamlit 웹 인터페이스

이 프로젝트는 ENd-to-End RAG 평가 프레임워크로 테스트 데이터셋 생성부터 평가 리포팅까지 RAG 평가를 위한 전과정을 지원합니다. RAG의 응답을 받기 위해서 참가자는 API를 제공해해야합니다.

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Academic RAG API 서버 시작

```bash
python academic_rag_api.py
```

서버가 `http://localhost:5000`에서 실행됩니다.
(상황에 맞게 주소, 포트 변경)

### 3. Streamlit 앱 시작

```bash
cd streamlit
streamlit run streamlit_page.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.
(상황에 맞게 주소, 포트 변경)

## 📋 사용법

![End-to-End RAG 평가 프레임워크](assets/page_sample.png)
![RAG 평가 다이어그램](assets/diagram.png)

### Step 1: Benchmark Generation
1. JSON 형식의 corpus 파일을 업로드합니다
2. DataMorgana를 사용하여 QA 데이터를 생성합니다
3. 생성된 QA 데이터를 미리보기하고 다운로드할 수 있습니다

### Step 2: RAG 실행 (배치 API 호출)
1. 참가자의 RAG API URL을 입력합니다 (기본값 : http://localhost:5000)
2. API 연결을 테스트합니다
3. 처리할 질문 개수와 검색할 문서 개수를 설정합니다
4. QA 데이터를 사용하여 배치 방식으로 RAG API를 호출합니다
5. 결과를 `results_for_eval.json`에 저장합니다

### Step 3: Evaluation
1. RAG 실행 결과를 평가합니다
2. RAGChecker를 사용하여 성능 메트릭을 계산합니다
3. 평가 결과를 다운로드할 수 있습니다

### API 테스트
1. 참가자의 API를 직접 테스트할 수 있습니다
2. 단일 질의 및 배치 질의 테스트가 가능합니다
3. API 상태 및 설정 정보를 확인할 수 있습니다

## 🔧 API 스펙

### 배치 질의응답 API (권장)

**엔드포인트:** `POST /api/rag/batch`

**요청:**
```json
{
    "queries": ["질문1", "질문2", "질문3"],
    "top_k": 3
}
```

**응답:**
```json
{
    "results": [
        {
            "query": "질문1",
            "answer": "답변1",
            "retrieved_documents": [
                {
                    "doc_id": "document_id",
                    "text": "문서 내용",
                    "title": "문서 제목",
                    "distance": 0.85
                }
            ],
            "metadata": {
                "processing_time": 1.23,
                "num_retrieved": 3,
                "model": "gpt-3.5-turbo"
            }
        }
    ],
    "summary": {
        "total_queries": 3,
        "total_processing_time": 5.67,
        "average_processing_time": 1.89
    }
}
```

### 단일 질의응답 API

**엔드포인트:** `POST /api/rag/query`

**요청:**
```json
{
    "query": "질문 내용",
    "top_k": 3
}
```

**응답:**
```json
{
    "query": "질문",
    "answer": "답변",
    "retrieved_documents": [...],
    "metadata": {...}
}
```

## 🛠️ Baseline RAG 시스템 (로컬 테스트)

### Baseline RAG API 서버 사용

- Milvus 벡터 데이터베이스 사용
- OpenAI GPT-3.5-turbo 모델 사용
- 실제 학술 논문 데이터로 테스트
- 배치 처리 지원

### 테스트 방법

1. Academic RAG API 서버를 시작합니다
2. Streamlit 앱에서 "API 테스트" 페이지로 이동합니다
3. 연결 테스트를 수행합니다
4. 단일 질의 및 배치 질의를 테스트합니다

## 📁 파일 구조

```
RAG-eval-framework/
├── streamlit/                 # Streamlit 웹 인터페이스
│   ├── streamlit_page.py      # 메인 Streamlit 앱
│   ├── requirements.txt       # Python 의존성
│   └── README.md              # Streamlit README
├── datamorgana/               # QA 데이터 생성 모듈
│   ├── datamorgana_generator.py  # QA 데이터 생성기
│   ├── data/                  # 샘플 데이터
│   └── ...
├── RAGChecker/                # RAG 평가 모듈
│   ├── quick_start.py         # 평가 실행 스크립트
│   ├── results/               # 평가 결과 저장
│   ├── ragchecker/            # 평가 라이브러리
│   └── ...
├── academic_rag_api.py        # Baseline RAG API 서버
├── academic_rag.py            # 원본 RAG 시스템
├── results_for_eval.json      # RAG 실행 결과
└── README.md                  # 프로젝트 README
```

## ⚙️ 환경 변수

다음 환경 변수를 설정할 수 있습니다:

## 🚨 주의사항

1. **OpenAI API 키**: OpenAI API 키가 환경변수에 설정되어 있어야 합니다
2. **메모리 사용량**: Milvus 벡터 DB와 임베딩 생성으로 인한 메모리 사용량이 높을 수 있습니다
3. **처리 시간**: 배치 처리 시에도 각 질문마다 개별적으로 처리되므로 시간이 소요됩니다
4. **네트워크 연결**: OpenAI API 호출을 위한 인터넷 연결이 필요합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
