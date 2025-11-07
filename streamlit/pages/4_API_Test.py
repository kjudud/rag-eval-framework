"""
API 테스트 페이지
"""

import streamlit as st
import json

from utils import display_logo, RAGAPIClient, apply_sidebar_style

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="API 테스트",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 스타일 적용
apply_sidebar_style()

# 로고 표시
display_logo()

# 로고 아래 구분선
st.markdown(
    '''
    <div style="margin: 10px 0;">
        <hr style="margin: 0; border: 2px solid #e0e0e0; border-radius: 1px;">
    </div>
    ''',
    unsafe_allow_html=True
)

st.subheader('API 테스트')
st.write('참가자의 RAG API를 직접 테스트할 수 있습니다')

# API 테스트 섹션
st.subheader("🔗 API 연결 테스트")

col1, col2 = st.columns([2, 1])

with col1:
    api_url = st.text_input(
        "API 서버 URL:",
        value="http://localhost:5000",
        help="테스트할 RAG API 서버 주소"
    )

with col2:
    if st.button("🔍 연결 테스트", type="primary"):
        try:
            client = RAGAPIClient(api_url)
            
            # 헬스 체크
            with st.spinner("API 연결 확인 중..."):
                health = client.health_check()
            
            st.success("✅ API 연결 성공!")
            
            # API 정보 표시
            col1, col2 = st.columns(2)
            with col1:
                st.metric("상태", health.get('status', 'unknown'))
                st.metric("메시지", health.get('message', 'N/A'))
            
            with col2:
                config = client.get_config()
                st.metric("API 버전", config.get('api_version', 'unknown'))
                st.metric("지원 언어", ", ".join(config.get('supported_languages', [])))
            
            # 지원 엔드포인트 표시
            st.subheader("📋 지원 엔드포인트")
            endpoints = config.get('supported_endpoints', [])
            for endpoint in endpoints:
                st.write(f"• `{endpoint}`")
            
        except Exception as e:
            st.error(f"❌ API 연결 실패: {str(e)}")
            st.code(str(e))

# 단일 질의 테스트
st.subheader("💬 단일 질의 테스트")

col1, col2 = st.columns([2, 1])

with col1:
    test_question = st.text_input(
        "테스트 질문:",
        value="인공지능이란 무엇인가요?",
        help="API에 전송할 테스트 질문"
    )

with col2:
    test_top_k = st.number_input("검색 문서 수:", min_value=1, max_value=10, value=3)

if st.button("🚀 질의 테스트", type="primary"):
    if not test_question.strip():
        st.warning("질문을 입력해주세요.")
    else:
        try:
            client = RAGAPIClient(api_url)
            
            with st.spinner("질의 처리 중..."):
                # 단일 질의는 배치 API를 사용하되 질문 1개만 전송
                response = client.batch_query([test_question], test_top_k)
                single_result = response.get('results', [{}])[0]
            
            st.success("✅ 질의 처리 완료!")
            
            # 결과 표시
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📝 질문")
                st.write(test_question)
                
                st.subheader("🤖 생성된 답변")
                st.write(single_result.get('answer', 'N/A'))
            
            with col2:
                st.subheader("📊 메타데이터")
                metadata = single_result.get('metadata', {})
                st.metric("처리 시간", f"{metadata.get('processing_time', 0):.2f}초")
                st.metric("검색 문서 수", metadata.get('num_retrieved', 0))
                st.metric("모델", metadata.get('model', 'N/A'))
            
            # 검색된 문서 표시
            st.subheader("📚 검색된 문서")
            retrieved_docs = single_result.get('retrieved_documents', [])
            
            if retrieved_docs:
                for i, doc in enumerate(retrieved_docs):
                    with st.expander(f"문서 {i+1} (ID: {doc.get('doc_id', 'N/A')})"):
                        st.write(f"**제목:** {doc.get('title', 'N/A')}")
                        st.write(f"**내용:** {doc.get('text', 'N/A')}")
                        if 'distance' in doc:
                            st.write(f"**유사도:** {doc['distance']:.4f}")
            else:
                st.info("검색된 문서가 없습니다.")
            
            # 전체 응답 JSON 표시
            with st.expander("📄 전체 응답 (JSON)"):
                st.json(single_result)
            
        except Exception as e:
            st.error(f"❌ 질의 처리 실패: {str(e)}")
            st.code(str(e))

# 배치 테스트
st.subheader("📦 배치 질의 테스트")

# 샘플 질문들
sample_questions = [
    "인공지능이란 무엇인가요?",
    "머신러닝과 딥러닝의 차이점은 무엇인가요?",
    "자연어처리 기술에 대해 설명해주세요.",
    "RAG 기술의 장점은 무엇인가요?",
    "AI 모델의 학습 과정은 어떻게 이루어지나요?"
]

col1, col2 = st.columns([2, 1])

with col1:
    batch_questions = st.text_area(
        "배치 질문 (한 줄에 하나씩):",
        value="\n".join(sample_questions),
        height=150,
        help="여러 질문을 한 번에 테스트할 수 있습니다"
    )

with col2:
    batch_top_k = st.number_input("검색 문서 수:", min_value=1, max_value=10, value=3, key="batch_top_k")

if st.button("🚀 배치 테스트", type="primary"):
    questions_list = [q.strip() for q in batch_questions.split('\n') if q.strip()]
    
    if not questions_list:
        st.warning("질문을 입력해주세요.")
    else:
        try:
            client = RAGAPIClient(api_url)
            
            with st.spinner(f"{len(questions_list)}개 질문 처리 중..."):
                response = client.batch_query(questions_list, batch_top_k)
            
            st.success(f"✅ 배치 처리 완료! ({len(questions_list)}개 질문)")
            
            # 배치 결과 요약
            summary = response.get('summary', {})
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("총 질문 수", summary.get('total_queries', 0))
            with col2:
                st.metric("총 처리 시간", f"{summary.get('total_processing_time', 0):.2f}초")
            with col3:
                st.metric("평균 처리 시간", f"{summary.get('average_processing_time', 0):.2f}초")
            
            # 개별 결과 표시
            st.subheader("📋 개별 결과")
            results = response.get('results', [])
            
            for i, result in enumerate(results):
                with st.expander(f"질문 {i+1}: {result.get('query', 'N/A')[:50]}..."):
                    st.write(f"**질문:** {result.get('query', 'N/A')}")
                    st.write(f"**답변:** {result.get('answer', 'N/A')}")
                    
                    # 검색된 문서 표시
                    retrieved_docs = result.get('retrieved_documents', [])
                    if retrieved_docs:
                        st.write("**검색된 문서:**")
                        for j, doc in enumerate(retrieved_docs[:2]):  # 최대 2개만 표시
                            st.write(f"- {doc.get('title', 'N/A')} (유사도: {doc.get('distance', 0):.4f})")
                    
                    # 메타데이터
                    metadata = result.get('metadata', {})
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("처리 시간", f"{metadata.get('processing_time', 0):.2f}초")
                    with col2:
                        st.metric("검색 문서 수", metadata.get('num_retrieved', 0))
            
            # 전체 응답 다운로드
            st.download_button(
                label="📥 배치 결과 다운로드",
                data=json.dumps(response, ensure_ascii=False, indent=2),
                file_name="batch_test_results.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"❌ 배치 처리 실패: {str(e)}")
            st.code(str(e))

# Academic RAG API 서버 시작 가이드
st.subheader("🛠️ 로컬 테스트 가이드")

with st.expander("📖 Academic RAG API 서버 사용법"):
    st.markdown("""
    **1. Academic RAG API 서버 시작:**
    ```bash
    cd streamlit
    python academic_rag_api.py
    ```
    
    **2. 서버 확인:**
    - 브라우저에서 http://localhost:5000/health 접속
    - 또는 위의 "연결 테스트" 버튼 클릭
    
    **3. API 엔드포인트:**
    - `GET /health` - 헬스 체크
    - `POST /api/rag/query` - 단일 질의응답
    - `POST /api/rag/batch` - 배치 질의응답 (권장)
    - `GET /api/rag/config` - API 설정 정보
    
    **4. 환경 변수 설정 (선택사항):**
    ```bash
    export CHUNKS_FILE="datamorgana/data/academic_chunks_sample.json"
    export MILVUS_DB_PATH="./academic_milvus.db"
    ```
    
    **5. 실제 API 연동:**
    - 참가자의 실제 API URL을 입력하여 테스트
    - API 스펙이 위의 Academic RAG API와 호환되어야 함
    """)

# API 스펙 정보
with st.expander("📋 API 스펙 정보"):
    st.markdown("""
    **단일 질의응답 API:**
    ```json
    POST /api/rag/query
    {
        "query": "질문 내용",
        "top_k": 3
    }
    ```
    
    **배치 질의응답 API:**
    ```json
    POST /api/rag/batch
    {
        "queries": ["질문1", "질문2", "질문3"],
        "top_k": 3
    }
    ```
    
    **응답 형식:**
    ```json
    {
        "query": "질문",
        "answer": "답변",
        "retrieved_documents": [
            {
                "id": "doc_id",
                "text": "문서 내용",
                "metadata": {"source": "출처"}
            }
        ],
        "metadata": {
            "processing_time": 1.23,
            "num_retrieved": 3,
            "model": "model_name"
        }
    }
    ```
    """)

