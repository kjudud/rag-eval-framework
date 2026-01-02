"""
Step 1: Benchmark Generation (Multi-modal) 페이지
OCR 처리와 QA 생성을 순차적으로 수행
"""

import streamlit as st
import json
import os
import subprocess
import threading
import queue

from utils import display_logo, apply_sidebar_style, get_project_root, run_in_conda_env

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Step 1: Benchmark Generation (Multi-modal)",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 사이드바 스타일 적용
apply_sidebar_style()

# 로고 표시
display_logo()

# 로고 아래 구분선
st.markdown(
    """
    <div style="margin: 10px 0;">
        <hr style="margin: 0; border: 2px solid #e0e0e0; border-radius: 1px;">
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Benchmark Generation (Multi-modal)")
st.write("멀티모달 데이터(이미지 + 텍스트)를 사용하여 QA 데이터를 생성합니다.")

# 프로젝트 루트 경로
project_root = get_project_root()

# 단계별 진행 상황 표시
st.markdown("---")
st.markdown("### 📋 처리 단계")

# 단계 상태 초기화
if "ocr_completed" not in st.session_state:
    st.session_state["ocr_completed"] = False
if "qa_completed" not in st.session_state:
    st.session_state["qa_completed"] = False

# 단계 표시
col1, col2, col3 = st.columns(3)
with col1:
    ocr_status = "✅ 완료" if st.session_state["ocr_completed"] else "⏳ 대기"
    st.markdown(f"**Step 1: OCR 처리**\n\n{ocr_status}")
with col2:
    qa_status = (
        "✅ 완료"
        if st.session_state["qa_completed"]
        else ("⏳ 진행 가능" if st.session_state["ocr_completed"] else "⏳ 대기")
    )
    st.markdown(f"**Step 2: QA 생성**\n\n{qa_status}")
with col3:
    final_status = "✅ 완료" if st.session_state["qa_completed"] else "⏳ 대기"
    st.markdown(f"**Step 3: 결과 확인**\n\n{final_status}")

st.markdown("---")

# Step 1: OCR 처리
st.subheader("🔍 Step 1: OCR 처리")
st.write("1. PDF 이미지 파일이 있는 디렉토리를 확인하고 OCR 처리를 수행합니다.")

# 입력 디렉토리 확인
pdfs_to_img_dir = os.path.join(project_root, "mmodal_generation", "pdfs_to_img")
ocr_output_dir = os.path.join(project_root, "mmodal_generation", "ocr_output")

col1, col2 = st.columns(2)
with col1:
    st.write(f"**입력 디렉토리:** `{pdfs_to_img_dir}`")
    if os.path.exists(pdfs_to_img_dir):
        pdf_dirs = [
            d
            for d in os.listdir(pdfs_to_img_dir)
            if os.path.isdir(os.path.join(pdfs_to_img_dir, d))
        ]
        st.success(f"✅ 입력 디렉토리 발견: {len(pdf_dirs)}개 PDF 디렉토리")
        for pdf_dir in pdf_dirs[:5]:  # 최대 5개만 표시
            pdf_path = os.path.join(pdfs_to_img_dir, pdf_dir)
            image_files = [
                f
                for f in os.listdir(pdf_path)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
            ]
            st.write(f"  - `{pdf_dir}`: {len(image_files)}개 이미지")
        if len(pdf_dirs) > 5:
            st.info(f"  ... 외 {len(pdf_dirs) - 5}개 디렉토리")
    else:
        st.warning(f"⚠️ 입력 디렉토리가 존재하지 않습니다: `{pdfs_to_img_dir}`")

with col2:
    st.write(f"**출력 디렉토리:** `{ocr_output_dir}`")
    if os.path.exists(ocr_output_dir):
        output_dirs = [
            d
            for d in os.listdir(ocr_output_dir)
            if os.path.isdir(os.path.join(ocr_output_dir, d))
        ]
        st.info(f"ℹ️ 출력 디렉토리: {len(output_dirs)}개 처리된 디렉토리")
    else:
        st.info("ℹ️ 출력 디렉토리가 아직 생성되지 않았습니다.")

# OCR 처리 실행
if st.button(
    "🚀 OCR 처리 시작", type="primary", disabled=st.session_state["ocr_completed"]
):
    if not os.path.exists(pdfs_to_img_dir):
        st.error(f"❌ 입력 디렉토리가 존재하지 않습니다: `{pdfs_to_img_dir}`")
    else:
        # 진행상황 표시를 위한 컨테이너
        progress_container = st.container()
        status_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

        try:
            # 기존 프로세스가 실행 중이면 종료
            if "ocr_process" in st.session_state:
                old_process = st.session_state["ocr_process"]
                if old_process.poll() is None:  # 프로세스가 실행 중인 경우
                    status_text.text("기존 프로세스 종료 중...")
                    try:
                        old_process.terminate()
                        try:
                            old_process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            old_process.kill()
                            old_process.wait()
                        status_text.text("기존 프로세스가 종료되었습니다.")
                        del st.session_state["ocr_process"]
                    except Exception as e:
                        st.warning(f"기존 프로세스 종료 중 오류: {str(e)}")

            # OCR 스크립트 경로 (cwd 기준 상대 경로)
            ocr_script = "test_ocr_processor.py"
            cwd_path = os.path.join(project_root, "mmodal_generation")

            # conda 환경에서 OCR 스크립트 실행
            status_text.text("OCR 처리 시작 중...")
            process = run_in_conda_env(
                env_name="deepseek-ocr",
                script_path=ocr_script,
                cwd=cwd_path,
            )

            # 프로세스를 세션 상태에 저장
            st.session_state["ocr_process"] = process

            # 실시간 출력 처리
            def read_output(pipe, q):
                for line in iter(pipe.readline, ""):
                    q.put(line)
                pipe.close()

            # 출력을 읽는 스레드 시작
            output_queue = queue.Queue()
            output_thread = threading.Thread(
                target=read_output, args=(process.stdout, output_queue)
            )
            output_thread.daemon = True
            output_thread.start()

            # 에러 출력도 읽기
            error_queue = queue.Queue()
            error_thread = threading.Thread(
                target=read_output, args=(process.stderr, error_queue)
            )
            error_thread.daemon = True
            error_thread.start()

            # 출력 표시
            log_container = status_container.empty()
            log_lines = []

            while True:
                # 프로세스가 종료되었는지 확인
                if process.poll() is not None:
                    break

                # 표준 출력 읽기
                try:
                    output = output_queue.get(timeout=0.5)
                    if output:
                        log_lines.append(output.strip())
                        if len(log_lines) > 20:  # 최대 20줄만 유지
                            log_lines.pop(0)
                        log_container.text_area(
                            "실행 로그",
                            value="\n".join(log_lines),
                            height=200,
                            disabled=True,
                        )
                except queue.Empty:
                    pass

                # 에러 출력 읽기
                try:
                    error = error_queue.get(timeout=0.1)
                    if error:
                        log_lines.append(f"[ERROR] {error.strip()}")
                        if len(log_lines) > 20:
                            log_lines.pop(0)
                        log_container.text_area(
                            "실행 로그",
                            value="\n".join(log_lines),
                            height=200,
                            disabled=True,
                        )
                except queue.Empty:
                    pass

            # 프로세스 완료 대기
            return_code = process.wait()

            if return_code == 0:
                progress_bar.progress(1.0)
                status_text.text("✅ OCR 처리가 완료되었습니다!")
                st.success("✅ OCR 처리가 완료되었습니다!")
                st.session_state["ocr_completed"] = True
                if "ocr_process" in st.session_state:
                    del st.session_state["ocr_process"]
                st.rerun()
            else:
                stderr_output = (
                    process.stderr.read() if process.stderr else "에러 출력 없음"
                )
                st.error("❌ OCR 처리 중 오류가 발생했습니다:")
                st.code(stderr_output)

        except Exception as e:
            st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")
            import traceback

            st.code(traceback.format_exc())

# OCR 완료 후 Step 2 표시
if st.session_state["ocr_completed"]:
    st.markdown("---")
    st.subheader("📝 Step 2: QA 생성")
    st.write("2. OCR 처리된 결과를 사용하여 QA 데이터를 생성합니다.")

    # OCR 출력 확인
    if os.path.exists(ocr_output_dir):
        output_dirs = [
            d
            for d in os.listdir(ocr_output_dir)
            if os.path.isdir(os.path.join(ocr_output_dir, d))
        ]
        st.info(f"ℹ️ 처리된 OCR 결과: {len(output_dirs)}개 디렉토리")

        # QA 생성 설정
        col1, col2 = st.columns(2)
        with col1:
            num_questions = st.number_input(
                "문서당 질문 수",
                min_value=1,
                max_value=10,
                value=1,
                help="각 문서에서 생성할 QA 쌍의 개수",
            )
        with col2:
            max_tokens = st.number_input(
                "최대 생성 토큰 수",
                min_value=64,
                max_value=2048,
                value=256,
                step=64,
                help="모델이 생성할 최대 토큰 수",
            )

        # 출력 파일 경로
        output_file = os.path.join(
            project_root, "streamlit", "generated_qa_data_multi_modal.json"
        )
        st.write(f"**출력 파일:** `{output_file}`")

        # QA 생성 실행
        if st.button(
            "🚀 QA 생성 시작", type="primary", disabled=st.session_state["qa_completed"]
        ):
            # 진행상황 표시를 위한 컨테이너
            progress_container = st.container()
            status_container = st.container()

            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()

            try:
                # 기존 프로세스가 실행 중이면 종료
                if "qa_process" in st.session_state:
                    old_process = st.session_state["qa_process"]
                    if old_process.poll() is None:  # 프로세스가 실행 중인 경우
                        status_text.text("기존 프로세스 종료 중...")
                        try:
                            old_process.terminate()
                            try:
                                old_process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                old_process.kill()
                                old_process.wait()
                            status_text.text("기존 프로세스가 종료되었습니다.")
                            del st.session_state["qa_process"]
                        except Exception as e:
                            st.warning(f"기존 프로세스 종료 중 오류: {str(e)}")

                # QA 스크립트 경로 (cwd 기준 상대 경로)
                qa_script = "test_qa_generator.py"
                cwd_path = os.path.join(project_root, "mmodal_generation")

                # test_qa_generator.py는 직접 수정이 필요하므로,
                # 여기서는 환경 변수나 임시 파일로 설정 전달
                # 또는 qa_generator.py를 직접 호출하는 방식으로 변경 필요

                # 일단 test_qa_generator.py를 수정 가능한 버전으로 실행
                # 실제로는 qa_generator.py의 main 함수를 직접 호출하는 것이 좋음

                status_text.text("QA 생성 시작 중...")

                # conda 환경에서 QA 스크립트 실행
                # 주의: test_qa_generator.py는 하드코딩된 설정을 사용하므로
                # 실제로는 qa_generator.py를 직접 호출하거나
                # test_qa_generator.py를 수정해야 함

                # 임시로 test_qa_generator.py 실행 (설정은 스크립트 내부에서)
                process = run_in_conda_env(
                    env_name="Qwen3-VL",
                    script_path=qa_script,
                    cwd=cwd_path,
                )

                # 프로세스를 세션 상태에 저장
                st.session_state["qa_process"] = process

                # 실시간 출력 처리
                def read_output(pipe, q):
                    for line in iter(pipe.readline, ""):
                        q.put(line)
                    pipe.close()

                # 출력을 읽는 스레드 시작
                output_queue = queue.Queue()
                output_thread = threading.Thread(
                    target=read_output, args=(process.stdout, output_queue)
                )
                output_thread.daemon = True
                output_thread.start()

                # 에러 출력도 읽기
                error_queue = queue.Queue()
                error_thread = threading.Thread(
                    target=read_output, args=(process.stderr, error_queue)
                )
                error_thread.daemon = True
                error_thread.start()

                # 출력 표시
                log_container = status_container.empty()
                log_lines = []

                while True:
                    # 프로세스가 종료되었는지 확인
                    if process.poll() is not None:
                        break

                    # 표준 출력 읽기
                    try:
                        output = output_queue.get(timeout=0.5)
                        if output:
                            log_lines.append(output.strip())
                            if len(log_lines) > 20:
                                log_lines.pop(0)
                            log_container.text_area(
                                "실행 로그",
                                value="\n".join(log_lines),
                                height=200,
                                disabled=True,
                            )

                            # PROGRESS 메시지 파싱
                            if "PROGRESS:" in output:
                                try:
                                    parts = output.strip().split(":", 2)
                                    if len(parts) == 3:
                                        progress_value = int(parts[1]) / 100.0
                                        message = parts[2]
                                        progress_bar.progress(progress_value)
                                        status_text.text(
                                            f"진행률: {int(progress_value * 100)}% - {message}"
                                        )
                                except (ValueError, IndexError):
                                    pass
                    except queue.Empty:
                        pass

                    # 에러 출력 읽기
                    try:
                        error = error_queue.get(timeout=0.1)
                        if error:
                            log_lines.append(f"[ERROR] {error.strip()}")
                            if len(log_lines) > 20:
                                log_lines.pop(0)
                            log_container.text_area(
                                "실행 로그",
                                value="\n".join(log_lines),
                                height=200,
                                disabled=True,
                            )
                    except queue.Empty:
                        pass

                # 프로세스 완료 대기
                return_code = process.wait()

                if return_code == 0:
                    progress_bar.progress(1.0)
                    status_text.text("✅ QA 생성이 완료되었습니다!")
                    st.success("✅ QA 생성이 완료되었습니다!")
                    st.session_state["qa_completed"] = True
                    if "qa_process" in st.session_state:
                        del st.session_state["qa_process"]
                    st.rerun()
                else:
                    stderr_output = (
                        process.stderr.read() if process.stderr else "에러 출력 없음"
                    )
                    st.error("❌ QA 생성 중 오류가 발생했습니다:")
                    st.code(stderr_output)

            except Exception as e:
                st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")
                import traceback

                st.code(traceback.format_exc())
    else:
        st.warning(
            "⚠️ OCR 출력 디렉토리가 존재하지 않습니다. 먼저 OCR 처리를 완료하세요."
        )

# QA 완료 후 결과 표시
if st.session_state["qa_completed"]:
    st.markdown("---")
    st.subheader("📋 Step 3: 생성된 QA 데이터 확인")

    # 출력 파일 경로
    output_file = os.path.join(
        project_root, "streamlit", "generated_qa_data_multi_modal.json"
    )
    # test_qa_generator.py의 기본 출력 경로도 확인
    default_output_file = os.path.join(
        project_root, "mmodal_generation", "data", "test_qa_results.json"
    )

    # 파일 찾기
    qa_file_path = None
    if os.path.exists(output_file):
        qa_file_path = output_file
    elif os.path.exists(default_output_file):
        qa_file_path = default_output_file

    if qa_file_path and os.path.exists(qa_file_path):
        try:
            with open(qa_file_path, "r", encoding="utf-8") as f:
                qa_data = json.load(f)

            st.success(f"📁 QA 데이터 파일을 찾았습니다: `{qa_file_path}`")

            # 파일 정보
            col1, col2 = st.columns(2)
            with col1:
                if isinstance(qa_data, list):
                    total_qa_pairs = sum(
                        len(doc.get("generated_qa_pairs", [])) for doc in qa_data
                    )
                    st.metric("생성된 QA 쌍 수", total_qa_pairs)
                    st.metric("처리된 문서 수", len(qa_data))
                else:
                    st.metric("데이터 타입", type(qa_data).__name__)
            with col2:
                file_size = os.path.getsize(qa_file_path)
                st.metric("파일 크기", f"{file_size:,} bytes")

            # 첫 5개 QA 쌍 표시
            if isinstance(qa_data, list) and len(qa_data) > 0:
                st.write("**첫 5개 QA 쌍:**")
                displayed = 0
                for i, qa_item in enumerate(qa_data):
                    if displayed >= 5:
                        break
                    qa_pairs = qa_item.get("generated_qa_pairs", [])
                    if qa_pairs:
                        for j, qa_pair in enumerate(qa_pairs):
                            if displayed >= 5:
                                break
                            with st.expander(
                                f"QA 쌍 {displayed + 1} - 문서 ID: {qa_item.get('id', 'unknown')}"
                            ):
                                st.write(f"**질문:** {qa_pair.get('question', 'N/A')}")
                                st.write(f"**답변:** {qa_pair.get('answer', 'N/A')}")
                                st.write(
                                    f"**문서 ID:** {qa_pair.get('document_id', 'N/A')}"
                                )
                                if "user_categories" in qa_pair:
                                    st.write(
                                        f"**사용자 카테고리:** {qa_pair.get('user_categories', 'N/A')}"
                                    )
                                if "question_categories" in qa_pair:
                                    st.write(
                                        f"**질문 카테고리:** {qa_pair.get('question_categories', 'N/A')}"
                                    )
                                st.write("---")
                            displayed += 1
                            if displayed >= 5:
                                break

            # 전체 데이터 다운로드 버튼
            with open(qa_file_path, "r", encoding="utf-8") as f:
                qa_file_content = f.read()

            st.download_button(
                label="📥 생성된 QA 데이터 다운로드",
                data=qa_file_content,
                file_name="generated_qa_data_multi_modal.json",
                mime="application/json",
            )

        except Exception as e:
            st.error(f"❌ QA 데이터 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
            import traceback

            st.code(traceback.format_exc())
    else:
        st.warning("⚠️ 생성된 QA 데이터 파일을 찾을 수 없습니다.")
        st.info("다음 경로들을 확인했습니다:")
        st.write(f"- `{output_file}`")
        st.write(f"- `{default_output_file}`")

# 리셋 버튼
st.markdown("---")
if st.button("🔄 전체 프로세스 리셋"):
    st.session_state["ocr_completed"] = False
    st.session_state["qa_completed"] = False
    if "ocr_process" in st.session_state:
        try:
            st.session_state["ocr_process"].terminate()
        except (AttributeError, ProcessLookupError):
            pass
        del st.session_state["ocr_process"]
    if "qa_process" in st.session_state:
        try:
            st.session_state["qa_process"].terminate()
        except (AttributeError, ProcessLookupError):
            pass
        del st.session_state["qa_process"]
    st.rerun()
