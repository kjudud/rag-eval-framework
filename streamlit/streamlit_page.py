import streamlit as st
import json
from io import StringIO
import subprocess
import os
import sys

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="RAG-eval-framework",
    page_icon="🔬",
    layout="wide",  # 와이드 레이아웃으로 설정
    initial_sidebar_state="expanded"
)

# 페이지 상단에 로고 표시
def display_logo():
    # 로고 이미지 표시
    logo_path = "../assets/KETI_logo.svg"
    
    # 제목과 로고를 같은 높이에 배치
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(
            '''
            <div style="margin: 0; padding: 0; display: flex; flex-direction: column; justify-content: center; height: 100%;">
                <h1 style="margin: 0; padding: 0; color: #1f77b4;">RAG-eval-framework</h1>
                <p style="margin: 5px 0 0 0; padding: 0; font-size: 12px; color: #666666; line-height: 1.3;">
                    해당 연구는 2024년도 정부(과학기술정보통신부)의 재원으로 정보통신기획평가원의 지원을 받아 수행된 연구임<br>
                    (No.2710017875, 멀티모달 데이터 입력 기반 검색 증강 생성 기술 개발)
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    with col2:
        if os.path.exists(logo_path):
            try:
                # 오른쪽 정렬된 로고
                st.markdown(
                    '''
                    <div style="text-align: right; margin: 0; padding: 0; display: flex; justify-content: flex-end; align-items: center; height: 100%;">
                    ''',
                    unsafe_allow_html=True
                )
                st.image(logo_path, width=250)
                st.markdown(
                    '''
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"이미지 로드 실패: {str(e)}")
                
        else:
            # 로고 파일이 없을 때
            st.markdown(
                '''
                <div style="text-align: right; margin: 0; padding: 0; display: flex; justify-content: flex-end;">
                    <a href="https://www.keti.re.kr" target="_blank" 
                       style="text-decoration: none; color: #1f77b4; font-size: 18px; font-weight: bold;">
                        KETI
                    </a>
                </div>
                ''',
                unsafe_allow_html=True
            )

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

# 사이드바에서 페이지 선택
st.sidebar.subheader('🔬 RAG 평가 pipeline')
page = st.sidebar.radio(
    "페이지를 선택하세요",
    ["1️⃣ Step: Benchmark Generation", "2️⃣ Step: RAG 실행", "3️⃣ Step: Evaluation"],
    index=0
)

if page == "1️⃣ Step: Benchmark Generation":
    st.subheader('Benchmark Generation')
    st.write('1.Corpus로 사용할 json 파일을 업로드합니다')

    # JSON 파일 업로드
    uploaded_file = st.file_uploader(
        "JSON 파일을 선택하세요",
        type=['json'],
        help="JSON 형식의 파일만 업로드 가능합니다"
    )
    
    # Config 파일 업로드 (옵션)
    st.write("**Config 파일 (옵션):**")
    uploaded_config = st.file_uploader(
        "Config 파일을 선택하세요",
        type=['json'],
        help="DataMorgana 설정 파일. 업로드하지 않으면 기본 설정을 사용합니다.",
        key="config_uploader"
    )

    if uploaded_file is not None:
        try:
            # JSON 파일 읽기
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            json_data = json.load(stringio)
            
            st.success("✅ JSON 파일이 성공적으로 업로드되었습니다!")
            
            # 파일 정보 표시
            st.subheader("📁 파일 정보")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("파일명", uploaded_file.name)
                st.metric("파일 크기", f"{uploaded_file.size:,} bytes")
            with col2:
                if isinstance(json_data, list):
                    st.metric("데이터 개수", len(json_data))
                elif isinstance(json_data, dict):
                    st.metric("키 개수", len(json_data.keys()))
            
            # JSON 데이터 미리보기
            st.subheader("👀 데이터 미리보기")
            
            if isinstance(json_data, list):
                # 리스트인 경우 첫 5개 항목만 표시
                preview_data = json_data[:5]
                st.json(preview_data)
                if len(json_data) > 5:
                    st.info(f"총 {len(json_data)}개 항목 중 처음 5개만 표시됩니다.")
            else:
                # 딕셔너리인 경우 전체 표시
                st.json(json_data)
            
            # 데이터 분석
            st.subheader("📊 데이터 분석")
            
            if isinstance(json_data, list) and len(json_data) > 0:
                # 첫 번째 항목의 구조 분석
                first_item = json_data[0]
                if isinstance(first_item, dict):
                    st.write("**첫 번째 항목의 키 구조:**")
                    for key, value in first_item.items():
                        value_type = type(value).__name__
                        if isinstance(value, str):
                            value_preview = value[:50] + "..." if len(value) > 50 else value
                            st.write(f"- `{key}`: {value_type} - `{value_preview}`")
                        else:
                            st.write(f"- `{key}`: {value_type}")
            
            # 데이터를 세션 상태에 저장
            st.session_state['uploaded_json'] = json_data
            st.session_state['uploaded_filename'] = uploaded_file.name
            
            # Config 파일도 세션 상태에 저장
            if uploaded_config is not None:
                config_stringio = StringIO(uploaded_config.getvalue().decode("utf-8"))
                config_data = json.load(config_stringio)
                st.session_state['uploaded_config'] = config_data
                st.session_state['uploaded_config_filename'] = uploaded_config.name
                st.success(f"✅ Config 파일이 업로드되었습니다: `{uploaded_config.name}`")
            else:
                # 기본 config 사용
                st.session_state['uploaded_config'] = None
                st.session_state['uploaded_config_filename'] = None
                st.info("ℹ️ Config 파일이 업로드되지 않았습니다. 기본 설정을 사용합니다.")
            
            # 파일을 디스크에 저장
            upload_dir = "uploaded_files"
            os.makedirs(upload_dir, exist_ok=True)
            
            # JSON 파일 저장
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            # Config 파일 저장 (있는 경우)
            config_path = None
            if uploaded_config is not None:
                config_path = os.path.join(upload_dir, uploaded_config.name)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                st.success(f"📁 파일들이 디스크에 저장되었습니다:")
                st.write(f"- JSON: `{file_path}`")
                st.write(f"- Config: `{config_path}`")
            else:
                st.success(f"📁 파일이 디스크에 저장되었습니다: `{file_path}`")
            
            # 저장된 디렉토리의 파일 리스트 표시
            st.subheader("📂 저장된 파일 목록")
            if os.path.exists(upload_dir):
                files = os.listdir(upload_dir)
                if files:
                    for file in sorted(files):
                        file_full_path = os.path.join(upload_dir, file)
                        file_size = os.path.getsize(file_full_path)
                        st.write(f"• `{file}` ({file_size:,} bytes)")
                else:
                    st.write("저장된 파일이 없습니다.")
            else:
                st.write("저장 디렉토리가 존재하지 않습니다.")
            
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON 파일 형식이 올바르지 않습니다: {str(e)}")
        except Exception as e:
            st.error(f"❌ 파일 처리 중 오류가 발생했습니다: {str(e)}")

    # 세션 상태에서 데이터 확인
    if 'uploaded_json' in st.session_state:
        st.subheader("🔄 현재 로드된 데이터")
        st.info(f"현재 로드된 파일: `{st.session_state['uploaded_filename']}`")
        
        # 경로 정보 표시
        st.subheader("📋 실행 경로 정보")
        input_path = f"uploaded_files/{st.session_state['uploaded_filename']}"
        output_path = "generated_qa_data.json"
        config_path = None
        if 'uploaded_config_filename' in st.session_state and st.session_state['uploaded_config_filename']:
            config_path = f"uploaded_files/{st.session_state['uploaded_config_filename']}"
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**입력 파일:** `{input_path}`")
            if config_path:
                st.write(f"**Config 파일:** `{config_path}`")
            else:
                st.write(f"**Config 파일:** 기본 설정 사용")
        with col2:
            st.write(f"**출력 파일:** `{output_path}`")
        
        # datamorgana generator 실행 섹션
        st.subheader("🤖 DataMorgana Generator 실행")
        st.write("2. 업로드된 JSON 파일로 QA 데이터를 생성합니다")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🚀 QA 데이터 생성 시작", type="primary"):
                # 진행상황 표시를 위한 컨테이너
                progress_container = st.container()
                status_container = st.container()
                
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                try:
                    # datamorgana generator 실행 (실시간 출력)
                    cmd = [
                        sys.executable, 
                        "../datamorgana/datamorgana_generator.py",
                        "--input_file", input_path,
                        "--output_file", output_path
                    ]
                    
                    # config 파일이 있으면 추가
                    if config_path:
                        cmd.extend(["--config_file", config_path])
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True, 
                        cwd=".",
                        bufsize=0,  # unbuffered
                        universal_newlines=True
                    )
                    
                    # 실시간 출력 처리
                    import threading
                    import queue
                    
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
                            # 큐에서 출력 읽기 (타임아웃 0.1초)
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
                        status_text.text("✅ QA 데이터 생성이 완료되었습니다!")
                        st.success("✅ QA 데이터 생성이 완료되었습니다!")
                        st.session_state['qa_generated'] = True
                    else:
                        stderr_output = process.stderr.read()
                        st.error(f"❌ Generator 실행 중 오류가 발생했습니다:")
                        st.code(stderr_output)
                        
                except Exception as e:
                    st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")
        
        with col2:
            if st.button("🗑️ 데이터 제거"):
                del st.session_state['uploaded_json']
                del st.session_state['uploaded_filename']
                if 'uploaded_config' in st.session_state:
                    del st.session_state['uploaded_config']
                if 'uploaded_config_filename' in st.session_state:
                    del st.session_state['uploaded_config_filename']
                if 'qa_generated' in st.session_state:
                    del st.session_state['qa_generated']
                st.rerun()
        
        # 생성된 QA 데이터 표시
        if 'qa_generated' in st.session_state and st.session_state['qa_generated']:
            st.subheader("📋 생성된 QA 데이터 미리보기")
            
            qa_file_path = "generated_qa_data.json"
            if os.path.exists(qa_file_path):
                try:
                    with open(qa_file_path, 'r', encoding='utf-8') as f:
                        qa_data = json.load(f)
                    
                    st.success(f"📁 QA 데이터 파일을 찾았습니다: `{qa_file_path}`")
                    
                    # 파일 정보
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("생성된 QA 쌍 수", len(qa_data))
                    with col2:
                        file_size = os.path.getsize(qa_file_path)
                        st.metric("파일 크기", f"{file_size:,} bytes")
                    
                    # 첫 5개 QA 쌍 표시
                    st.write("**첫 5개 QA 쌍:**")
                    for i, qa_item in enumerate(qa_data[:5]):
                        with st.expander(f"QA 쌍 {i+1}"):
                            if 'generated_qa_pairs' in qa_item:
                                for j, qa_pair in enumerate(qa_item['generated_qa_pairs']):
                                    st.write(f"**질문 {j+1}:** {qa_pair.get('question', 'N/A')}")
                                    st.write(f"**답변 {j+1}:** {qa_pair.get('answer', 'N/A')}")
                                    st.write(f"**문서 ID:** {qa_pair.get('document_id', 'N/A')}")
                                    st.write("---")
                            else:
                                st.write("QA 쌍 데이터가 없습니다.")
                    
                    # 전체 데이터 다운로드 버튼
                    with open(qa_file_path, 'r', encoding='utf-8') as f:
                        qa_file_content = f.read()
                    
                    st.download_button(
                        label="📥 생성된 QA 데이터 다운로드",
                        data=qa_file_content,
                        file_name="academic_chunks_sample_qa.json",
                        mime="application/json"
                    )
                    
                except Exception as e:
                    st.error(f"❌ QA 데이터 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
            else:
                st.warning("⚠️ 생성된 QA 데이터 파일을 찾을 수 없습니다.")

elif page == "2️⃣ Step: RAG 실행":
    st.subheader('RAG 실행')
    st.write('RAG 시스템을 실행하여 질문에 대한 답변을 생성합니다')
    
    # RAG 실행 섹션
    st.subheader("🤖 RAG 시스템 실행")
    
    # 설정 옵션
    col1, col2 = st.columns([1, 1])
    
    with col1:
        num_questions = st.number_input("테스트할 질문 개수:", min_value=1, max_value=50, value=10)
    
    with col2:
        chunks_file = st.selectbox(
            "사용할 청크 파일:",
            ["uploaded_files/academic_chunks_sample_mini.json", "datamorgana/data/academic_chunks_sample.json"],
            help="업로드된 파일 또는 기본 파일을 선택하세요"
        )
    
    # QA 파일 경로 표시
    qa_file = "generated_qa_data.json"
    st.info(f"📁 QA 파일: `{qa_file}` (Step 1에서 생성된 파일 사용)")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔍 RAG 실행", type="primary"):
            # 진행상황 표시를 위한 컨테이너
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            try:
                # RAG 시스템 실행 (academic_rag.py 사용)
                cmd = [
                    sys.executable, 
                    "../academic_rag.py",
                    "--chunks_file", chunks_file,
                    "--qa_file", qa_file,
                    "--output_file", "results_for_eval.json",
                    "--num_questions", str(num_questions)
                ]
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True, 
                    cwd=".",
                    bufsize=0,  # unbuffered
                    universal_newlines=True
                )
                
                # 실시간 출력 처리
                import threading
                import queue
                
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
                    status_text.text("✅ RAG 실행이 완료되었습니다!")
                    st.success("✅ RAG 실행이 완료되었습니다!")
                    st.session_state['rag_completed'] = True
                else:
                    stderr_output = process.stderr.read()
                    st.error(f"❌ RAG 실행 중 오류가 발생했습니다:")
                    st.code(stderr_output)
                    
            except Exception as e:
                st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")
    
    with col2:
        if st.button("🗑️ 결과 초기화"):
            if 'rag_completed' in st.session_state:
                del st.session_state['rag_completed']
            st.rerun()
    
    # RAG 실행 결과 표시
    if 'rag_completed' in st.session_state and st.session_state['rag_completed']:
        st.subheader("📋 RAG 실행 결과")
        
        results_file = "results_for_eval.json"
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

elif page == "3️⃣ Step: Evaluation":
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
    
    # 입력 파일 경로 표시
    input_file = "results_for_eval.json"
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
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🚀 Evaluation 시작", type="primary"):
                # 진행상황 표시를 위한 컨테이너
                progress_container = st.container()
                
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                try:
                    # RAGChecker 실행
                    cmd = [
                        sys.executable, 
                        "../RAGChecker/quick_start.py",
                        "--input_file", f"../{input_file}",
                        "--output_file", "result_rag-framework.json",
                        "--metrics", metrics,
                        "--extractor_name", model_name,
                        "--checker_name", model_name
                    ]
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True, 
                        cwd=".",
                        bufsize=0,  # unbuffered
                        universal_newlines=True
                    )
                    
                    # 실시간 출력 처리
                    import threading
                    import queue
                    
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
            ragchecker_results = "../RAGChecker/results/result_rag-framework.json"
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
                                st.write("**개별 메트릭:**")
                                metric_cols = st.columns(len(first_result['metrics']))
                                for i, (metric_name, metric_value) in enumerate(first_result['metrics'].items()):
                                    with metric_cols[i]:
                                        st.metric(
                                            metric_name.replace('_', ' ').title(),
                                            f"{metric_value:.2f}",
                                            help=f"첫 번째 질문의 {metric_name} 점수"
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
    
        else:
            st.warning("⚠️ 평가할 결과 파일이 없습니다. 먼저 RAG 실행을 완료해주세요.")
        
            # 결과 파일 생성 가이드
            st.subheader("📝 결과 파일 생성 가이드")
            st.write("평가를 위해서는 다음 중 하나의 파일이 필요합니다:")
            st.write("1. `results_for_eval.json` - RAG 실행 결과")
            st.write("2. `RAGChecker/results/result_rag-framework.json` - 이전 평가 결과")
            
            if st.button("🔄 파일 목록 새로고침"):
                st.rerun()