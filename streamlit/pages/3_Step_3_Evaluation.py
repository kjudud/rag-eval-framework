"""
Step 3: Evaluation 페이지
"""

import streamlit as st
import json
import os
import sys
import subprocess
import threading
import queue

from utils import display_logo, apply_sidebar_style, get_project_root

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Step 3: Evaluation",
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

st.subheader('Evaluation')
st.write('RAG 시스템의 성능을 평가합니다')

# Evaluation 섹션
st.subheader("📊 RAG 성능 평가")

# 평가 설정
col1, col2 = st.columns([1, 1])

with col1:
    metrics = st.selectbox(
        "평가할 메트릭:",
        ["all_metrics", "retriever_metrics", "generator_metrics"],
        help="all_metrics: 모든 메트릭, retriever_metrics: 검색기 메트릭, generator_metrics: 생성기 메트릭"
    )

with col2:
    model_name = st.selectbox(
        "사용할 모델:",
        ["openai/gpt-4o-mini", "openai/gpt-4o", "openai/gpt-3.5-turbo"],
        help="평가에 사용할 OpenAI 모델"
    )

# 입력 파일 경로 표시 (절대 경로)
current_file_dir = os.path.dirname(os.path.abspath(__file__))
streamlit_dir = os.path.dirname(current_file_dir)
input_file = os.path.join(streamlit_dir, "results_for_eval.json")
st.info(f"📁 입력 파일: `{input_file}` (Step 2에서 생성된 RAG 결과)")

# 파일 존재 확인
if not os.path.exists(input_file):
    st.error(f"❌ 입력 파일을 찾을 수 없습니다: `{input_file}`")
    st.write("먼저 Step 2에서 RAG를 실행해주세요.")
else:
    # 파일 정보 표시
    file_size = os.path.getsize(input_file)
    st.metric("파일 크기", f"{file_size:,} bytes")
    
    # 파일 내용 미리보기
    with st.expander("📄 RAG 결과 파일 미리보기"):
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            st.text(content[:1000] + "..." if len(content) > 1000 else content)
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {str(e)}")
    
    # RAGChecker 실행
    st.subheader("🔍 RAGChecker 실행")
    
    # 실행 중인 프로세스 상태 표시
    if 'ragchecker_process' in st.session_state:
        process = st.session_state['ragchecker_process']
        if process.poll() is None:  # 프로세스가 실행 중인 경우
            st.warning("⚠️ RAGChecker 프로세스가 실행 중입니다. 새로 시작하면 기존 프로세스가 종료됩니다.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 Evaluation 시작", type="primary"):
            # 진행상황 표시를 위한 컨테이너
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            try:
                # 기존 프로세스가 실행 중이면 종료
                if 'ragchecker_process' in st.session_state:
                    old_process = st.session_state['ragchecker_process']
                    if old_process.poll() is None:  # 프로세스가 실행 중인 경우
                        status_text.text("기존 프로세스 종료 중...")
                        try:
                            old_process.terminate()  # 정상 종료 시도
                            # 5초 대기 후 강제 종료
                            try:
                                old_process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                old_process.kill()  # 강제 종료
                                old_process.wait()
                            status_text.text("기존 프로세스가 종료되었습니다.")
                            # 세션 상태에서 제거
                            del st.session_state['ragchecker_process']
                        except Exception as e:
                            st.warning(f"기존 프로세스 종료 중 오류: {str(e)}")
                
                # RAGChecker 실행
                # 프로젝트 루트 경로 가져오기
                project_root = get_project_root()
                
                ragchecker_script = os.path.join(project_root, "RAGChecker", "quick_start.py")
                input_file_abs = os.path.join(project_root, "streamlit", input_file)
                output_file_abs = os.path.join(project_root, "RAGChecker", "results", "result_rag-framework.json")
                
                cmd = [
                    sys.executable, 
                    ragchecker_script,
                    "--input_file", input_file_abs,
                    "--output_file", output_file_abs,
                    "--metrics", metrics,
                    "--extractor_name", model_name,
                    "--checker_name", model_name
                ]
                
                # 새 프로세스 시작 (프로젝트 루트에서 실행)
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True, 
                    cwd=project_root,
                    bufsize=0,  # unbuffered
                    universal_newlines=True
                )
                
                # 프로세스를 세션 상태에 저장 (필요한 경우)
                st.session_state['ragchecker_process'] = process
                
                # 실시간 출력 처리
                def read_output(pipe, q):
                    for line in iter(pipe.readline, ''):
                        q.put(line)
                    pipe.close()
                
                # 출력을 읽는 스레드 시작
                output_queue = queue.Queue()
                output_thread = threading.Thread(target=read_output, args=(process.stdout, output_queue))
                output_thread.daemon = True
                output_thread.start()
                
                while True:
                    # 프로세스가 종료되었는지 확인
                    if process.poll() is not None:
                        break
                        
                    try:
                        # 큐에서 출력 읽기 (타임아웃 0.5초)
                        output = output_queue.get(timeout=0.5)
                        if output:
                            # PROGRESS:숫자:메시지 형식 파싱
                            if output.startswith("PROGRESS:"):
                                try:
                                    parts = output.strip().split(":", 2)
                                    if len(parts) == 3:
                                        progress_value = int(parts[1]) / 100.0
                                        message = parts[2]
                                        progress_bar.progress(progress_value)
                                        status_text.text(f"진행률: {int(progress_value * 100)}% - {message}")
                                except Exception as e:
                                    pass
                            else:
                                # 일반 로그 출력
                                status_text.text(f"실행 중... {output.strip()}")
                    except queue.Empty:
                        # 큐가 비어있으면 계속 대기
                        continue
                
                # 프로세스 완료 대기
                return_code = process.wait()
                
                if return_code == 0:
                    progress_bar.progress(1.0)
                    status_text.text("✅ Evaluation이 완료되었습니다!")
                    st.success("✅ Evaluation이 완료되었습니다!")
                    st.session_state['evaluation_completed'] = True
                    # 프로세스 완료 후 세션 상태에서 제거
                    if 'ragchecker_process' in st.session_state:
                        del st.session_state['ragchecker_process']
                else:
                    stderr_output = process.stderr.read()
                    st.error(f"❌ Evaluation 실행 중 오류가 발생했습니다:")
                    st.code(stderr_output)
                    
            except Exception as e:
                st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")
    
    with col2:
        if st.button("🗑️ 결과 초기화"):
            if 'evaluation_completed' in st.session_state:
                del st.session_state['evaluation_completed']
            st.rerun()
    
    # Evaluation 결과 표시
    if 'evaluation_completed' in st.session_state and st.session_state['evaluation_completed']:
        st.subheader("📋 Evaluation 결과")
        
        # RAGChecker 결과 파일 확인
        project_root = get_project_root()
        ragchecker_results = os.path.join(project_root, "RAGChecker", "results", "result_rag-framework.json")
        if os.path.exists(ragchecker_results):
            try:
                with open(ragchecker_results, 'r', encoding='utf-8') as f:
                    eval_results = json.load(f)
                
                st.success(f"📁 Evaluation 결과 파일을 찾았습니다: `{ragchecker_results}`")
                
                # 결과 요약
                if 'results' in eval_results:
                    results_data = eval_results['results']
                    st.write(f"**총 평가된 질문 수:** {len(results_data)}")
                    
                    # 메트릭 요약
                    st.subheader("📊 성능 메트릭")
                    
                    # 전체 메트릭 표시
                    if 'metrics' in eval_results:
                        metrics_data = eval_results['metrics']
                        
                        # 메트릭 그룹별로 표시
                        for group_name, group_metrics in metrics_data.items():
                            if group_metrics:  # 메트릭이 있는 경우만 표시
                                st.write(f"**{group_name.replace('_', ' ').title()}:**")
                                
                                # 메트릭을 컬럼으로 표시
                                cols = st.columns(len(group_metrics))
                                for i, (metric_name, metric_value) in enumerate(group_metrics.items()):
                                    with cols[i]:
                                        st.metric(
                                            metric_name.replace('_', ' ').title(),
                                            f"{metric_value}%",
                                            help=f"{group_name} 그룹의 {metric_name} 메트릭"
                                        )
                                st.write("---")
                    
                    # 기본 정보
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("평가 완료", f"{len(results_data)}개")
                    with col2:
                        st.metric("결과 파일", "생성됨")
                    with col3:
                        file_size = os.path.getsize(ragchecker_results)
                        st.metric("결과 크기", f"{file_size:,} bytes")
                    
                    # 첫 번째 결과 미리보기
                    if results_data:
                        first_result = results_data[0]
                        st.subheader("🔍 첫 번째 결과 미리보기")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**질문:** {first_result.get('query', 'N/A')}")
                            st.write(f"**예상 답변:** {first_result.get('gt_answer', 'N/A')}")
                        with col2:
                            st.write(f"**생성된 답변:** {first_result.get('response', 'N/A')}")
                        
                        # 개별 메트릭 표시
                        if 'metrics' in first_result:
                            st.write("**예시) 첫번째 qa쌍에 대한 결과:**")
                            metric_cols = st.columns(len(first_result['metrics']))
                            for i, (metric_name, metric_value) in enumerate(first_result['metrics'].items()):
                                with metric_cols[i]:
                                    st.metric(
                                        metric_name.replace('_', ' ').title(),
                                        f"{metric_value:.2f}",
                                        help=f"첫 번째 qa쌍에 대한 {metric_name} 점수"
                                    )
                    
                    # 상세 결과 표시
                    with st.expander("📄 전체 Evaluation 결과 (JSON)"):
                        st.json(eval_results)
                    
                    # 결과 다운로드
                    with open(ragchecker_results, 'r', encoding='utf-8') as f:
                        eval_content = f.read()
                    
                    st.download_button(
                        label="📥 Evaluation 결과 다운로드",
                        data=eval_content,
                        file_name="evaluation_results.json",
                        mime="application/json"
                    )
                
            except Exception as e:
                st.error(f"❌ Evaluation 결과 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
        else:
            st.warning("⚠️ Evaluation 결과 파일을 찾을 수 없습니다.")

