"""
Step 1: Benchmark Generation (Multi-modal) 페이지
OCR 처리와 QA 생성을 순차적으로 수행
"""

import streamlit as st
import json
import os
import threading
import queue
import zipfile
import time
import traceback

from utils import (
    display_logo,
    apply_sidebar_style,
    get_project_root,
    run_in_conda_env,
    terminate_old_process,
    show_loading_spinner,
)

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Step 1: Benchmark Generation (Multi-modal)",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 사이드바 스타일 적용
apply_sidebar_style()
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

project_root = get_project_root()


# ==================== 헬퍼 함수 ====================
def get_zip_name():
    """세션 상태에서 ZIP 파일명 가져오기"""
    return st.session_state.get("zip_name", "default")


def read_output(pipe, q):
    """파이프에서 출력을 읽어 큐에 저장하는 함수"""
    for line in iter(pipe.readline, ""):
        q.put(line)
    pipe.close()


def collect_process_output(process, log_key: str, max_lines: int = 100):
    """프로세스 출력을 수집하여 세션 상태에 저장"""
    output_queue = queue.Queue()
    error_queue = queue.Queue()

    # 출력 읽기 스레드 시작
    output_thread = threading.Thread(
        target=read_output, args=(process.stdout, output_queue)
    )
    output_thread.daemon = True
    output_thread.start()

    error_thread = threading.Thread(
        target=read_output, args=(process.stderr, error_queue)
    )
    error_thread.daemon = True
    error_thread.start()

    log_lines = []

    # 프로세스 완료까지 출력 수집
    while True:
        if process.poll() is not None:
            break

        # 표준 출력 읽기
        try:
            output = output_queue.get(timeout=0.3)
            if output:
                log_lines.append(output.strip())
                if len(log_lines) > max_lines:
                    log_lines.pop(0)
        except queue.Empty:
            pass

        # 에러 출력 읽기
        try:
            error = error_queue.get(timeout=0.3)
            if error:
                log_lines.append(f"[ERROR] {error.strip()}")
                if len(log_lines) > max_lines:
                    log_lines.pop(0)
        except queue.Empty:
            pass

        time.sleep(0.05)

    # 프로세스 완료 대기
    process.wait()

    # 스레드 완료 대기 및 남은 출력 읽기
    output_thread.join(timeout=2)
    error_thread.join(timeout=2)

    for queue_obj in [output_queue, error_queue]:
        while True:
            try:
                line = queue_obj.get_nowait()
                if line:
                    prefix = "[ERROR] " if queue_obj == error_queue else ""
                    log_lines.append(f"{prefix}{line.strip()}")
                    if len(log_lines) > max_lines:
                        log_lines.pop(0)
            except queue.Empty:
                break

    # 세션 상태에 저장
    if log_lines:
        st.session_state[log_key] = log_lines

    return log_lines


def display_logs(log_key: str, title: str = "실행 로그"):
    """세션 상태에 저장된 로그를 표시"""
    if log_key in st.session_state and st.session_state[log_key]:
        with st.expander(f"📋 {title}", expanded=False):
            st.text_area(
                title,
                value="\n".join(st.session_state[log_key]),
                height=300,
                disabled=True,
            )


# ==================== UI 초기화 ====================

st.markdown("---")
st.markdown("### 📋 처리 단계")

# 단계 상태 초기화
if "ocr_completed" not in st.session_state:
    st.session_state["ocr_completed"] = False
if "qa_completed" not in st.session_state:
    st.session_state["qa_completed"] = False
if "datamorgana_config_path" not in st.session_state:
    st.session_state["datamorgana_config_path"] = None
if "pdf_stats" not in st.session_state:
    st.session_state["pdf_stats"] = None

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

# ==================== Step 1: OCR 처리 ====================

st.subheader("🔍 Step 1: OCR 처리")
st.write("1. ZIP 파일을 업로드하고 OCR 처리를 수행합니다.")

upload_base_dir = os.path.join(
    project_root, "uploaded_files", "benchmark_generation_img_txt"
)
os.makedirs(upload_base_dir, exist_ok=True)

st.markdown("### 📤 ZIP 파일 업로드")
uploaded_zip = st.file_uploader(
    "OCR 처리를 위한 ZIP 파일을 선택하세요",
    type=["zip"],
    help="이미지 파일들이 포함된 ZIP 파일을 업로드할 수 있습니다.",
)

# ZIP 파일 업로드 및 압축 해제
extract_dir = None
if uploaded_zip is not None:
    try:
        zip_path = os.path.join(upload_base_dir, uploaded_zip.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.getbuffer())

        st.success(f"✅ ZIP 파일이 업로드되었습니다: `{uploaded_zip.name}`")

        zip_name = os.path.splitext(uploaded_zip.name)[0]
        extract_dir = os.path.join(upload_base_dir, zip_name)
        os.makedirs(extract_dir, exist_ok=True)
        st.session_state["zip_name"] = zip_name

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

    except Exception as e:
        st.error(f"❌ ZIP 파일 처리 중 오류가 발생했습니다: {str(e)}")
        st.code(traceback.format_exc())

# OCR 완료 메시지 표시
if st.session_state.get("ocr_completed", False):
    st.success("✅ OCR 처리가 완료되었습니다!")
    if "ocr_elapsed_sec" in st.session_state:
        elapsed = st.session_state["ocr_elapsed_sec"]
        st.info(f"⏱️ OCR 처리 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")

    stats = st.session_state.get("pdf_stats")
    if stats:
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("총 PDF 수", f"{stats['total_pdfs']}개")
        col_b.metric("총 페이지 수", f"{stats['total_pages']}페이지")
        col_c.metric("총 파일 크기", f"{stats['total_mb']} MB")
        col_d.metric("평균 파일 크기", f"{stats['avg_mb']} MB")

        if stats.get("size_dist"):
            with st.expander("📊 파일 크기 분포", expanded=False):
                st.dataframe(
                    {
                        "크기 구간": list(stats["size_dist"].keys()),
                        "파일 수": list(stats["size_dist"].values()),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

    display_logs("ocr_log_lines", "OCR 처리 실행 로그")

# OCR 처리 실행
if st.button(
    "🚀 OCR 처리 시작", type="primary", disabled=st.session_state["ocr_completed"]
):
    if extract_dir is None or not os.path.exists(extract_dir):
        st.error("❌ 업로드된 파일이 존재하지 않습니다")
    else:
        progress_container = st.container()
        status_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

        try:
            terminate_old_process("ocr_process", status_text)

            zip_name = get_zip_name()
            pdfs_to_img_dir_path = os.path.join(
                project_root, "mmodal_generation", "pdfs_to_img", zip_name
            )
            output_dir_path = os.path.join(
                project_root, "mmodal_generation", "ocr_output", zip_name
            )

            os.makedirs(pdfs_to_img_dir_path, exist_ok=True)
            os.makedirs(output_dir_path, exist_ok=True)

            ocr_script = [
                os.path.join(
                    project_root, "mmodal_generation", "test_ocr_processor.py"
                ),
                "--pdf-dir",
                extract_dir,
                "--pdfs-to-img-dir",
                pdfs_to_img_dir_path,
                "--output-dir",
                output_dir_path,
            ]

            process = run_in_conda_env(
                env_name="deepseek-ocr",
                script_path=ocr_script[0],
                args=ocr_script[1:],
            )

            st.session_state["ocr_process"] = process
            st.session_state["ocr_log_lines"] = ["OCR 처리 시작 중..."]

            # 로딩 스피너 표시
            show_loading_spinner(status_text, "OCR 처리 실행 중...")

            log_container = status_container.empty()
            log_container.text_area(
                "실행 로그",
                value="프로세스 출력을 수집하고 있습니다...",
                height=200,
                disabled=True,
            )

            # 출력 수집
            log_lines = collect_process_output(process, "ocr_log_lines", max_lines=100)

            # 최종 로그 표시
            if log_lines:
                log_container.text_area(
                    "실행 로그",
                    value="\n".join(log_lines),
                    height=200,
                    disabled=True,
                )

            return_code = process.returncode

            if return_code == 0:
                progress_bar.progress(1.0)
                status_text.text("✅ OCR 처리가 완료되었습니다!")
                st.session_state["ocr_completed"] = True

                # TIMING / PDF_STATS 메시지 파싱
                for line in log_lines:
                    if "TIMING:total:" in line:
                        try:
                            elapsed = float(line.split("TIMING:total:")[1].strip())
                            st.session_state["ocr_elapsed_sec"] = elapsed
                        except (ValueError, IndexError):
                            pass
                    if "PDF_STATS:" in line:
                        try:
                            json_str = line.split("PDF_STATS:")[1].strip()
                            st.session_state["pdf_stats"] = json.loads(json_str)
                        except Exception:
                            pass

                if "ocr_process" in st.session_state:
                    del st.session_state["ocr_process"]
                st.success("✅ OCR 처리가 완료되었습니다!")
                st.rerun()
            else:
                st.error("❌ OCR 처리 중 오류가 발생했습니다.")
                if log_lines:
                    st.code("\n".join(log_lines))

        except Exception as e:
            st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")
            st.code(traceback.format_exc())

# ==================== Step 2: QA 생성 ====================

if st.session_state["ocr_completed"]:
    st.markdown("---")
    st.subheader("📝 Step 2: QA 생성")
    st.write("2. OCR 처리된 결과를 사용하여 QA 데이터를 생성합니다.")

    # OCR 출력 디렉토리 경로 계산 (zip_name 사용)
    zip_name = get_zip_name()
    ocr_output_dir_path = os.path.join(
        project_root, "mmodal_generation", "ocr_output", zip_name
    )

    if os.path.exists(ocr_output_dir_path):
        output_dirs = [
            d
            for d in os.listdir(ocr_output_dir_path)
            if os.path.isdir(os.path.join(ocr_output_dir_path, d))
        ]
        st.info(f"ℹ️ 처리된 OCR 결과: {len(output_dirs)}개 디렉토리")

        # DataMorgana 설정 파일 업로드
        st.markdown("#### ⚙️ DataMorgana 설정 파일 (선택)")
        uploaded_config = st.file_uploader(
            "datamorgana_config_template.json 파일을 업로드하세요 (업로드하지 않으면 기본 설정 사용)",
            type=["json"],
            key="datamorgana_config_uploader",
            help="QA 생성에 사용할 카테고리 설정 파일입니다.",
        )
        if uploaded_config is not None:
            try:
                config_json = json.loads(uploaded_config.read().decode("utf-8"))
                config_save_path = os.path.join(
                    upload_base_dir, f"datamorgana_config_{zip_name}.json"
                )
                with open(config_save_path, "w", encoding="utf-8") as f:
                    json.dump(config_json, f, ensure_ascii=False, indent=2)
                st.session_state["datamorgana_config_path"] = config_save_path
                st.success(f"✅ 설정 파일이 업로드되었습니다: `{uploaded_config.name}`")
            except Exception as e:
                st.error(f"❌ 설정 파일 처리 중 오류가 발생했습니다: {str(e)}")
                st.session_state["datamorgana_config_path"] = None
        elif st.session_state.get("datamorgana_config_path"):
            st.info(
                f"ℹ️ 이전에 업로드된 설정 파일을 사용합니다: `{os.path.basename(st.session_state['datamorgana_config_path'])}`"
            )
        else:
            st.info(
                "ℹ️ 설정 파일이 없으면 기본 `datamorgana_config_template.json`을 사용합니다."
            )

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
                value=1024,
                step=64,
                help="모델이 생성할 최대 토큰 수",
            )

        zip_name = get_zip_name()
        output_file = os.path.join(
            project_root, "streamlit", f"generated_qa_data_{zip_name}.json"
        )
        st.write(f"**출력 파일:** `{output_file}`")

        if st.button(
            "🚀 QA 생성 시작", type="primary", disabled=st.session_state["qa_completed"]
        ):
            progress_container = st.container()
            status_container = st.container()

            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()

            try:
                terminate_old_process("qa_process", status_text)

                qa_script = "test_qa_generator.py"
                cwd_path = os.path.join(project_root, "mmodal_generation")
                output_file_path = os.path.join(
                    project_root, "streamlit", f"generated_qa_data_{zip_name}.json"
                )

                # 로딩 스피너 표시
                show_loading_spinner(status_text, "QA 생성 시작 중...")

                process = run_in_conda_env(
                    env_name="Qwen3-VL",
                    script_path=qa_script,
                    args=[
                        "--ocr-output-dir",
                        ocr_output_dir_path,
                        "--output-file",
                        output_file_path,
                        "--num-questions",
                        str(num_questions),
                        "--max-new-tokens",
                        str(max_tokens),
                    ]
                    + (
                        ["--config-file", st.session_state["datamorgana_config_path"]]
                        if st.session_state.get("datamorgana_config_path")
                        else []
                    ),
                    cwd=cwd_path,
                )

                st.session_state["qa_process"] = process
                log_container = status_container.empty()
                log_lines = []

                # 출력 수집 (PROGRESS 메시지 파싱 포함)
                output_queue = queue.Queue()
                error_queue = queue.Queue()

                output_thread = threading.Thread(
                    target=read_output, args=(process.stdout, output_queue)
                )
                output_thread.daemon = True
                output_thread.start()

                error_thread = threading.Thread(
                    target=read_output, args=(process.stderr, error_queue)
                )
                error_thread.daemon = True
                error_thread.start()

                while True:
                    if process.poll() is not None:
                        break

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

                return_code = process.wait()
                output_thread.join(timeout=2)
                error_thread.join(timeout=2)

                if return_code == 0:
                    progress_bar.progress(1.0)
                    status_text.text("✅ QA 생성이 완료되었습니다!")
                    st.success("✅ QA 생성이 완료되었습니다!")
                    st.session_state["qa_completed"] = True

                    # TIMING 메시지 파싱
                    for line in log_lines:
                        if line.startswith("TIMING:total:"):
                            try:
                                elapsed = float(line.split(":")[2])
                                st.session_state["qa_elapsed_sec"] = elapsed
                            except (ValueError, IndexError):
                                pass

                    if "qa_process" in st.session_state:
                        del st.session_state["qa_process"]
                    st.rerun()
                else:
                    st.error("❌ QA 생성 중 오류가 발생했습니다.")
                    if log_lines:
                        st.code("\n".join(log_lines))

            except Exception as e:
                st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")
                st.code(traceback.format_exc())
    else:
        st.warning(
            "⚠️ OCR 출력 디렉토리가 존재하지 않습니다. 먼저 OCR 처리를 완료하세요."
        )

# ==================== Step 3: 결과 확인 ====================

if st.session_state["qa_completed"]:
    st.markdown("---")
    st.subheader("📋 Step 3: 생성된 QA 데이터 확인")
    if "qa_elapsed_sec" in st.session_state:
        elapsed = st.session_state["qa_elapsed_sec"]
        st.info(f"⏱️ QA 생성 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")

    zip_name = get_zip_name()
    output_file = os.path.join(
        project_root, "streamlit", f"generated_qa_data_{zip_name}.json"
    )

    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                qa_data = json.load(f)

            st.success(f"📁 QA 데이터 파일을 찾았습니다: `{output_file}`")

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
                file_size = os.path.getsize(output_file)
                st.metric("파일 크기", f"{file_size:,} bytes")

            # 첫 5개 QA 쌍 표시
            if isinstance(qa_data, list) and len(qa_data) > 0:
                st.write("**첫 5개 QA 쌍:**")
                displayed = 0
                for qa_item in qa_data:
                    if displayed >= 5:
                        break
                    qa_pairs = qa_item.get("generated_qa_pairs", [])
                    if qa_pairs:
                        for qa_pair in qa_pairs:
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

            # 다운로드 버튼
            with open(output_file, "r", encoding="utf-8") as f:
                qa_file_content = f.read()

            download_filename = f"generated_qa_data_{zip_name}.json"
            st.download_button(
                label="📥 생성된 QA 데이터 다운로드",
                data=qa_file_content,
                file_name=download_filename,
                mime="application/json",
            )

        except Exception as e:
            st.error(f"❌ QA 데이터 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
            st.code(traceback.format_exc())
    else:
        st.warning("⚠️ 생성된 QA 데이터 파일을 찾을 수 없습니다.")
        st.write(f"확인 경로: `{output_file}`")

# ==================== 리셋 버튼 ====================

st.markdown("---")
if st.button("🔄 전체 프로세스 리셋"):
    st.session_state["ocr_completed"] = False
    st.session_state["qa_completed"] = False
    for process_key in ["ocr_process", "qa_process"]:
        if process_key in st.session_state:
            try:
                st.session_state[process_key].terminate()
            except (AttributeError, ProcessLookupError):
                pass
            del st.session_state[process_key]
    st.rerun()
