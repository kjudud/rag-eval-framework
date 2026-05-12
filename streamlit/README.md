# RAG 평가 프레임워크 - Academic RAG API 버전

이 프로젝트는 `academic_rag.py`를 API 서버로 래핑하여 배치 질의 방식으로 RAG 시스템을 평가하는 프레임워크입니다.

## 🚀 빠른 시작

### 1. 의존성 설치(root에서)

```bash
conda create -n rag-eval-framework python=3.11
conda activate rag-eval-framework
pip install -r requirements.txt
```

### 2. WSL 환경 설정 (WSL 사용시 port 에러 발생시)

```bash
# 포트 포워딩 설정 (Windows 관리자 권한 필요)
./setup_wsl_ports.sh

# 연결 테스트
python test_connection.py
```

### 3. Academic RAG API 서버 시작

```bash
python academic_rag_api.py
```

서버가 `http://localhost:5000`에서 실행됩니다.

### 4. Streamlit 앱 시작

```bash
streamlit run streamlit_page.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

## 📋 사용법

### Step 1: Benchmark Generation
1. JSON 형식의 corpus 파일을 업로드합니다
2. DataMorgana를 사용하여 QA 데이터를 생성합니다

### Step 2: RAG 실행 (배치 API 호출)
1. Academic RAG API 서버 URL을 입력합니다 (기본값: http://localhost:5000) (wsl에서 실행시 0.0.0.0)
2. API 연결을 테스트합니다
3. QA 데이터를 사용하여 배치 방식으로 RAG API를 호출합니다
4. 결과를 `results_for_eval.json`에 저장합니다

### Step 3: Evaluation
1. RAG 실행 결과를 평가합니다
2. RAGChecker를 사용하여 성능 메트릭을 계산합니다

### API 테스트
1. Academic RAG API를 직접 테스트할 수 있습니다
2. 단일 질의 및 배치 질의 테스트가 가능합니다

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
```

## 🛠️ 로컬 테스트

### Academic RAG API 서버 사용

Academic RAG API 서버는 실제 `academic_rag.py`를 기반으로 구현되었습니다:

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
streamlit/
├── streamlit_page.py          # 메인 Streamlit 앱
├── academic_rag_api.py        # Academic RAG API 서버
├── requirements.txt           # Python 의존성
└── README.md                 # 이 파일
```

## 🔍 주요 기능

- **배치 처리**: 여러 질문을 한 번에 처리하여 효율성 향상
- **실제 RAG 시스템**: academic_rag.py를 기반으로 한 실제 RAG 구현
- **Milvus 벡터 DB**: 고성능 벡터 검색
- **OpenAI 통합**: GPT-3.5-turbo를 사용한 답변 생성
- **실시간 진행률**: API 호출 진행 상황을 실시간으로 표시
- **결과 저장**: JSON 형식으로 결과 저장
- **에러 처리**: API 호출 실패 시 적절한 에러 메시지 표시

## ⚙️ 환경 변수

다음 환경 변수를 설정할 수 있습니다:

```bash
export CHUNKS_FILE="datamorgana/data/academic_chunks_sample.json"  # 청크 파일 경로
export MILVUS_DB_PATH="./academic_milvus.db"                      # Milvus DB 경로
```

## 🚨 주의사항

1. **OpenAI API 키**: OpenAI API 키가 환경변수에 설정되어 있어야 합니다
2. **메모리 사용량**: Milvus 벡터 DB와 임베딩 생성으로 인한 메모리 사용량이 높을 수 있습니다
3. **처리 시간**: 배치 처리 시에도 각 질문마다 개별적으로 처리되므로 시간이 소요됩니다
4. **네트워크 연결**: OpenAI API 호출을 위한 인터넷 연결이 필요합니다

## 📊 성능 최적화

- **배치 처리**: 여러 질문을 한 번에 처리하여 네트워크 오버헤드 감소
- **Milvus 캐싱**: 벡터 DB를 사용하여 검색 성능 향상
- **병렬 처리**: API 서버에서 여러 질문을 병렬로 처리 가능

## 📞 지원

문제가 발생하면 다음을 확인해주세요:

1. OpenAI API 키 설정
2. Milvus DB 파일 권한
3. 청크 파일 경로
4. 네트워크 연결 상태
5. 로그 메시지 확인
