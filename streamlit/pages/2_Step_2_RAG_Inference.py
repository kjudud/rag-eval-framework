"""
Step 2: RAG 실행 페이지
"""

import streamlit as st
import json
import os
import time
import traceback

from utils import display_logo, RAGAPIClient, apply_sidebar_style, get_project_root

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Step 2: RAG 실행",
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

st.subheader('RAG 실행')
st.write('⚡ 참가자의 RAG API를 호출하여 질문에 대한 답변을 생성합니다')
st.write('🧠 Hybrid search 기반 RAG baseline 모델을 제공합니다.')
st.write('🔍 시맨틱 검색 + 🔑 키워드 검색 --> ⚡ hybrid search')
# RAG 실행 섹션
st.subheader("🤖 RAG API 호출")

# API 설정 옵션
st.subheader("⚙️ API 설정")
col1, col2 = st.columns([1, 1])

with col1:
    api_url = st.text_input(
        "API 서버 URL:",
        value="http://localhost:5000",
        help="참가자의 RAG API 서버 주소"
    )
    
    # 프로젝트 루트 경로 가져오기
    project_root = get_project_root()
    uploaded_files_dir = os.path.join(project_root, "uploaded_files")
    # uploaded_files 디렉토리에서 JSON 파일 목록 가져오기
    chunks_file_options = []
    if os.path.exists(uploaded_files_dir):
        for file in os.listdir(uploaded_files_dir):
            chunks_file_options.append(file)
    
    if chunks_file_options:
        selected_file = st.selectbox(
            "청크 파일 선택:",
            options=chunks_file_options,
            help="RAG 시스템에서 사용할 청크 파일을 선택하세요"
        )
        chunks_file_path = os.path.join(uploaded_files_dir, selected_file)
        st.info(f"📁 선택된 파일: `{chunks_file_path}`")
    else:
        st.warning("⚠️ uploaded_files 디렉토리에 파일이 없습니다.")
        selected_file = None
        chunks_file_path = None
    
    # API 연결 테스트
    if st.button("🔗 API 연결 테스트", type="secondary"):
        try:
            client = RAGAPIClient(api_url)
            health = client.health_check(chunks_file=chunks_file_path)
            st.success(f"✅ API 연결 성공!\n상태: {health.get('status', 'unknown')}")
            
            # API 설정 정보 표시
            config = client.get_config()
            st.info(f"📋 API 버전: {config.get('api_version', 'unknown')}")
            
        except Exception as e:
            st.error(f"❌ API 연결 실패: {str(e)}")
            
            # WSL 환경에서의 문제 해결 가이드 표시
            st.warning("🔧 WSL 환경에서의 문제 해결 방법:")
            st.markdown("""
            1. **API 서버가 실행 중인지 확인:**
               ```bash
               python academic_rag_api.py
               ```
            
            2. **포트가 사용 중인지 확인:**
               ```bash
               netstat -tlnp | grep :5000
               ```
            
            3. **WSL IP 주소 확인:**
               ```bash
               hostname -I
               ```
            
            4. **방화벽 설정 확인:**
               - Windows 방화벽에서 포트 5000 허용
               - WSL에서 포트 포워딩 설정
            """)

with col2:
    num_questions = st.number_input("테스트할 질문 개수:", min_value=1, max_value=1000, value=10)
    top_k = st.number_input("검색할 문서 개수:", min_value=1, max_value=10, value=3)

# API 정의 표시
st.markdown("---")
st.markdown("### 🔌 API 형식 가이드")

# 좌우 컬럼으로 구분
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📤 배치 쿼리 요청 형식")
    st.code('''
POST /batch_query
Content-Type: application/json

{
  "questions": [
    "질문 1",
    "질문 2", 
    "질문 3"
  ],
  "top_k": 3
}
    ''', language='json')
    
with col2:
    st.markdown("#### 📥 배치 쿼리 응답 형식")
    st.code('''
{
  "results": [
    {
      "query_id": "0",
      "query": "질문 내용",
      "gt_answer": "정답",
      "response": "시스템 응답",
      "retrieved_context": [
        {
          "distance": 0.7262771129608154,
          "doc_id": "문서 ID",
          "text": "검색된 문서 내용...",
          "title": "문서 제목"
        }
      ],
      "metadata": {
        "model": "gpt-3.5-turbo",
        "num_retrieved": 3,
        "processing_time": 2.14,
        "query_index": 0,
        "timestamp": 1758269337.2524438
      }
    }
  ],
  "metadata": {
    "total_questions": 3,
    "processed_questions": 3,
    "api_url": "http://localhost:5000",
    "top_k": 3,
    "batch_processing": true,
    "timestamp": 1758269340.597136
  }
}
    ''', language='json')

st.info("💡 **사용법**: 위 형식을 참고하여 API 요청/응답을 확인하세요.")
st.markdown("---")

# QA 파일 경로 표시 (절대 경로)
current_file_dir = os.path.dirname(os.path.abspath(__file__))
streamlit_dir = os.path.dirname(current_file_dir)
qa_file = os.path.join(streamlit_dir, "generated_qa_data.json")
st.info(f"📁 QA 파일: `{qa_file}` (Step 1에서 생성된 파일 사용)")

# 파일 존재 확인
if not os.path.exists(qa_file):
    st.error(f"❌ QA 파일을 찾을 수 없습니다: `{qa_file}`")
    st.write("먼저 Step 1에서 QA 데이터를 생성해주세요.")
else:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔍 RAG API 호출 (배치)", type="primary"):
            # 진행상황 표시를 위한 컨테이너
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            try:
                # RAG API 클라이언트 초기화
                status_text.text("API 클라이언트 초기화 중...")
                progress_bar.progress(0.05)
                client = RAGAPIClient(api_url)
                
                # QA 데이터 로드
                status_text.text("QA 데이터 로드 중...")
                progress_bar.progress(0.1)
                
                with open(qa_file, 'r', encoding='utf-8') as f:
                    qa_data = json.load(f)
                
                # 질문 추출
                questions = []
                gt_answers = []
                document_ids = []
                
                for item in qa_data:
                    if 'generated_qa_pairs' in item:
                        for qa_pair in item['generated_qa_pairs']:
                            if 'question' in qa_pair:
                                questions.append(qa_pair['question'])
                                gt_answers.append(qa_pair.get('answer', ''))
                                document_ids.append(qa_pair.get('document_id', ''))
                    elif 'question' in item:
                        questions.append(item['question'])
                        gt_answers.append(item.get('answer', ''))
                        document_ids.append(item.get('document_id', ''))
                
                # 질문 수 제한
                if num_questions < len(questions):
                    questions = questions[:num_questions]
                    gt_answers = gt_answers[:num_questions]
                    document_ids = document_ids[:num_questions]
                
                status_text.text(f"총 {len(questions)}개 질문을 배치로 처리 중...")
                progress_bar.progress(0.2)
                
                # 배치 API 호출 (chunks_file 전달)
                batch_response = client.batch_query(questions, top_k, chunks_file=chunks_file_path)
                batch_results = batch_response.get('results', [])
                
                progress_bar.progress(0.9)
                status_text.text("결과 변환 중...")
                
                # 결과를 기존 형식에 맞게 변환
                results = []
                for i, (question, gt_answer, doc_id) in enumerate(zip(questions, gt_answers, document_ids)):
                    if i < len(batch_results):
                        batch_result = batch_results[i]
                        result = {
                            'query_id': str(i),
                            'query': question,
                            'gt_answer': gt_answer,
                            'response': batch_result.get('answer', ''),
                            'retrieved_context': batch_result.get('retrieved_documents', []),
                            'metadata': batch_result.get('metadata', {})
                        }
                    else:
                        # 배치 결과가 부족한 경우
                        result = {
                            'query_id': str(i),
                            'query': question,
                            'gt_answer': gt_answer,
                            'response': '처리 실패',
                            'retrieved_context': [],
                            'metadata': {'error': '배치 처리 결과 없음'}
                        }
                    results.append(result)
                
                # 결과를 파일로 저장
                status_text.text("결과 저장 중...")
                output_data = {
                    'results': results,
                    'metadata': {
                        'total_questions': len(questions),
                        'processed_questions': len(results),
                        'api_url': api_url,
                        'top_k': top_k,
                        'batch_processing': True,
                        'timestamp': time.time()
                    }
                }
                
                # 절대 경로로 저장
                results_file = os.path.join(streamlit_dir, "results_for_eval.json")
                with open(results_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                
                progress_bar.progress(1.0)
                status_text.text("✅ RAG API 배치 호출이 완료되었습니다!")
                st.success(f"✅ RAG API 배치 호출이 완료되었습니다! ({len(results)}개 질문 처리)")
                st.session_state['rag_completed'] = True
                
            except Exception as e:
                st.error(f"❌ RAG API 호출 중 오류가 발생했습니다: {str(e)}")
                st.code(traceback.format_exc())
    
    with col2:
        if st.button("🗑️ 결과 초기화"):
            if 'rag_completed' in st.session_state:
                del st.session_state['rag_completed']
            st.rerun()

# RAG 실행 결과 표시
if 'rag_completed' in st.session_state and st.session_state['rag_completed']:
    st.subheader("📋 RAG 실행 결과")
    
    results_file = os.path.join(streamlit_dir, "results_for_eval.json")
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results_data = json.load(f)
            
            st.success(f"📁 RAG 결과 파일을 찾았습니다: `{results_file}`")
            
            # 결과 요약
            results = results_data.get('results', [])
            st.write(f"**총 {len(results)}개의 질문-답변 쌍이 처리되었습니다.**")
            
            # 첫 번째 결과 미리보기
            if results:
                first_result = results[0]
                st.subheader("🔍 첫 번째 결과 미리보기")
                st.write(f"**질문:** {first_result.get('query', 'N/A')}")
                st.write(f"**예상 답변:** {first_result.get('gt_answer', 'N/A')}")
                st.write(f"**생성된 답변:** {first_result.get('response', 'N/A')}")
                
                # 검색된 컨텍스트 표시
                if 'retrieved_context' in first_result:
                    st.subheader("🔍 검색된 컨텍스트")
                    for i, ctx in enumerate(first_result['retrieved_context']):
                        with st.expander(f"컨텍스트 {i+1} (문서 ID: {ctx.get('doc_id', 'N/A')})"):
                            st.text(ctx.get('text', 'N/A'))
            
            # 전체 결과 다운로드
            with open(results_file, 'r', encoding='utf-8') as f:
                result_content = f.read()
            
            st.download_button(
                label="📥 RAG 결과 다운로드",
                data=result_content,
                file_name="results_for_eval.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"❌ RAG 결과 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
    else:
        st.warning("⚠️ RAG 결과 파일을 찾을 수 없습니다.")

