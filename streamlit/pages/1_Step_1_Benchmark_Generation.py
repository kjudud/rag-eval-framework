"""
Step 1: Benchmark Generation 페이지
"""

import streamlit as st
import json
from io import StringIO
import subprocess
import os
import sys
import threading
import queue

from utils import display_logo, apply_sidebar_style, get_project_root

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Step 1: Benchmark Generation",
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

st.subheader("Benchmark Generation")
st.write("1.Corpus로 사용할 json 파일을 업로드합니다")

# JSON 파일 업로드
uploaded_file = st.file_uploader(
    "JSON 파일을 선택하세요", type=["json"], help="JSON 형식의 파일만 업로드 가능합니다"
)

# Config 파일 업로드 (옵션)
st.write("**Config 파일 (옵션):**")
uploaded_config = st.file_uploader(
    "Config 파일을 선택하세요",
    type=["json"],
    help="DataMorgana 설정 파일. 업로드하지 않으면 기본 설정을 사용합니다.",
    key="config_uploader",
)

# corpus ,config 파일 json 형식 샘플
st.markdown("---")
st.markdown("### 📋 JSON 파일 형식 가이드")

# 좌우 컬럼으로 구분
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📄 Corpus 파일 형식")
    st.markdown("**ex)academic_chunks_sample_mini.json**")
    st.code(
        """
[
  {
    "id": "unique-identifier",
    "content": "문서의 실제 내용...",
    "title": "문서 제목"
  },
  {
    "id": "another-identifier", 
    "content": "다른 문서 내용...",
    "title": "다른 문서 제목"
  }
]
    """,
        language="json",
    )

with col2:
    st.markdown("#### ⚙️ Config 파일 형식")
    st.markdown("**ex)datamorgana_config_template.json**")
    st.code(
        """
{
  "user_categorizations": [
    {
      "name": "expertise",
      "categories": [
        {
          "name": "expert",
          "probability": 0.7,
          "description": "전문가 사용자"
        },
        {
          "name": "novice", 
          "probability": 0.3,
          "description": "초보 사용자"
        }
      ]
    }
  ],
  "question_categorizations": [
    {
      "name": "factuality",
      "categories": [
        {
          "name": "factoid",
          "probability": 0.6,
          "description": "구체적인 사실을 묻는 질문"
        },
        {
          "name": "open-ended",
          "probability": 0.4,
          "description": "자유로운 답변을 요구하는 질문"
        }
      ]
    }
  ]
}
    """,
        language="json",
    )

st.info("💡 **사용법**: 위 형식을 참고하여 JSON 파일을 준비한 후 업로드하세요.")
st.markdown("---")


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
        st.session_state["uploaded_json"] = json_data
        st.session_state["uploaded_filename"] = uploaded_file.name

        # Config 파일도 세션 상태에 저장
        if uploaded_config is not None:
            config_stringio = StringIO(uploaded_config.getvalue().decode("utf-8"))
            config_data = json.load(config_stringio)
            st.session_state["uploaded_config"] = config_data
            st.session_state["uploaded_config_filename"] = uploaded_config.name
            st.success(f"✅ Config 파일이 업로드되었습니다: `{uploaded_config.name}`")
        else:
            # 기본 config 사용
            st.session_state["uploaded_config"] = None
            st.session_state["uploaded_config_filename"] = None
            st.info("ℹ️ Config 파일이 업로드되지 않았습니다. 기본 설정을 사용합니다.")

        # 파일을 디스크에 저장
        upload_dir = "uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)

        # JSON 파일 저장
        file_path = os.path.join(upload_dir, uploaded_file.name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # Config 파일 저장 (있는 경우)
        config_path = None
        if uploaded_config is not None:
            config_path = os.path.join(upload_dir, uploaded_config.name)
            with open(config_path, "w", encoding="utf-8") as f:
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
if "uploaded_json" in st.session_state:
    st.subheader("🔄 현재 로드된 데이터")
    st.info(f"현재 로드된 파일: `{st.session_state['uploaded_filename']}`")

    # 경로 정보 표시
    st.subheader("📋 실행 경로 정보")
    # 절대 경로 계산
    project_root = get_project_root()
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    streamlit_dir = os.path.dirname(current_file_dir)
    input_path = os.path.join(
        project_root, "uploaded_files", st.session_state["uploaded_filename"]
    )
    output_path = os.path.join(streamlit_dir, "generated_qa_data.json")
    config_path = None
    if (
        "uploaded_config_filename" in st.session_state
        and st.session_state["uploaded_config_filename"]
    ):
        config_path = os.path.join(
            project_root,
            "uploaded_files",
            st.session_state["uploaded_config_filename"],
        )

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

    # 실행 중인 프로세스 상태 표시
    if "datamorgana_process" in st.session_state:
        process = st.session_state["datamorgana_process"]
        if process.poll() is None:  # 프로세스가 실행 중인 경우
            st.warning(
                "⚠️ DataMorgana 프로세스가 실행 중입니다. 새로 시작하면 기존 프로세스가 종료됩니다."
            )

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
                # 기존 프로세스가 실행 중이면 종료
                if "datamorgana_process" in st.session_state:
                    old_process = st.session_state["datamorgana_process"]
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
                            del st.session_state["datamorgana_process"]
                        except Exception as e:
                            st.warning(f"기존 프로세스 종료 중 오류: {str(e)}")

                # datamorgana generator 실행 (실시간 출력)
                # 프로젝트 루트 경로 가져오기
                project_root = get_project_root()

                datamorgana_script = os.path.join(
                    project_root, "datamorgana", "datamorgana_generator.py"
                )
                input_file_abs = os.path.join(project_root, "streamlit", input_path)
                output_file_abs = os.path.join(project_root, "streamlit", output_path)

                # 로그 파일 경로 설정
                log_file_abs = os.path.join(
                    project_root, "streamlit", "datamorgana_generator.log"
                )

                cmd = [
                    sys.executable,
                    datamorgana_script,
                    "--input_file",
                    input_file_abs,
                    "--output_file",
                    output_file_abs,
                    "--log_file",
                    log_file_abs,
                ]

                # config 파일이 있으면 추가
                if config_path:
                    config_file_abs = os.path.join(
                        project_root, "streamlit", config_path
                    )
                    cmd.extend(["--config_file", config_file_abs])

                # 새 프로세스 시작 (프로젝트 루트에서 실행)
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=project_root,
                    bufsize=0,  # unbuffered
                    universal_newlines=True,
                )

                # 프로세스를 세션 상태에 저장 (필요한 경우)
                st.session_state["datamorgana_process"] = process

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
                                        status_text.text(
                                            f"진행률: {int(progress_value * 100)}% - {message}"
                                        )
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
                    st.session_state["qa_generated"] = True
                    # 프로세스 완료 후 세션 상태에서 제거
                    if "datamorgana_process" in st.session_state:
                        del st.session_state["datamorgana_process"]
                else:
                    stderr_output = process.stderr.read()
                    st.error(f"❌ Generator 실행 중 오류가 발생했습니다:")
                    st.code(stderr_output)

            except Exception as e:
                st.error(f"❌ 실행 중 오류가 발생했습니다: {str(e)}")

    with col2:
        if st.button("🗑️ 데이터 제거"):
            del st.session_state["uploaded_json"]
            del st.session_state["uploaded_filename"]
            if "uploaded_config" in st.session_state:
                del st.session_state["uploaded_config"]
            if "uploaded_config_filename" in st.session_state:
                del st.session_state["uploaded_config_filename"]
            if "qa_generated" in st.session_state:
                del st.session_state["qa_generated"]
            st.rerun()

    # 생성된 QA 데이터 표시
    if "qa_generated" in st.session_state and st.session_state["qa_generated"]:
        st.subheader("📋 생성된 QA 데이터 미리보기")

        # 절대 경로 계산
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        streamlit_dir = os.path.dirname(current_file_dir)
        qa_file_path = os.path.join(streamlit_dir, "generated_qa_data.json")
        if os.path.exists(qa_file_path):
            try:
                with open(qa_file_path, "r", encoding="utf-8") as f:
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
                        if "generated_qa_pairs" in qa_item:
                            for j, qa_pair in enumerate(qa_item["generated_qa_pairs"]):
                                st.write(
                                    f"**질문 {j+1}:** {qa_pair.get('question', 'N/A')}"
                                )
                                st.write(
                                    f"**답변 {j+1}:** {qa_pair.get('answer', 'N/A')}"
                                )
                                st.write(
                                    f"**문서 ID:** {qa_pair.get('document_id', 'N/A')}"
                                )
                                st.write("---")
                        else:
                            st.write("QA 쌍 데이터가 없습니다.")

                # 전체 데이터 다운로드 버튼
                with open(qa_file_path, "r", encoding="utf-8") as f:
                    qa_file_content = f.read()

                st.download_button(
                    label="📥 생성된 QA 데이터 다운로드",
                    data=qa_file_content,
                    file_name="academic_chunks_sample_qa.json",
                    mime="application/json",
                )

            except Exception as e:
                st.error(f"❌ QA 데이터 파일을 읽는 중 오류가 발생했습니다: {str(e)}")
        else:
            st.warning("⚠️ 생성된 QA 데이터 파일을 찾을 수 없습니다.")
