"""
공통 유틸리티 모듈
- RAGAPIClient: RAG API 클라이언트
- display_logo: 로고 표시 함수
- get_project_root: 프로젝트 루트 경로 반환
- run_in_conda_env: conda 환경에서 스크립트 실행
"""

import streamlit as st
import os
import requests
import subprocess
import shutil
from typing import Optional, List


def get_project_root():
    """프로젝트 루트 경로를 반환합니다.

    Returns:
        str: 프로젝트 루트의 절대 경로
    """
    # 현재 파일 위치 (utils.py) 기준으로 프로젝트 루트 찾기
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    # utils.py는 streamlit/ 디렉토리에 있으므로, 부모 디렉토리가 프로젝트 루트
    project_root = os.path.dirname(current_file_dir)
    return project_root


class RAGAPIClient:
    """RAG API 클라이언트 클래스"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "User-Agent": "RAG-Eval-Framework/1.0"}
        )

    def health_check(self, chunks_file: str = None):
        """API 서버 헬스 체크

        Args:
            chunks_file: 청크 파일 경로 (선택사항)
        """
        try:
            params = {}
            if chunks_file:
                params["chunks_file"] = chunks_file
            print(params)
            response = self.session.get(
                f"{self.base_url}/health", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"헬스 체크 실패: {str(e)}")

    def get_config(self):
        """API 설정 정보 조회"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/rag/config", timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"설정 정보 조회 실패: {str(e)}")

    def batch_query(self, questions: list, top_k: int = 3, chunks_file: str = None):
        """배치 질의응답"""
        try:
            payload = {"queries": questions, "top_k": top_k}
            params = {}
            if chunks_file:
                params["chunks_file"] = chunks_file

            response = self.session.post(
                f"{self.base_url}/api/rag/batch",
                json=payload,
                params=params,
                timeout=self.timeout * len(questions),
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"배치 질의응답 실패: {str(e)}")


def apply_sidebar_style():
    """사이드바 스타일 커스터마이징"""
    st.markdown(
        """
    <style>
        /* 사이드바 전체 스타일 */
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa !important;
        }
        
        /* 사이드바 내 모든 링크 스타일 (메인 콘텐츠 제외) */
        section[data-testid="stSidebar"] a:not([href*="keti.re.kr"]) {
            font-size: 1.15rem !important;
            font-weight: 500 !important;
            color: #262730 !important;
            padding: 0.8rem 1rem !important;
            margin: 0.3rem 0 !important;
            border-radius: 8px !important;
            display: block !important;
            transition: all 0.3s ease !important;
            text-decoration: none !important;
        }
        
        /* 사이드바 링크 호버 효과 */
        section[data-testid="stSidebar"] a:not([href*="keti.re.kr"]):hover {
            background-color: #e3f2fd !important;
            color: #1f77b4 !important;
            transform: translateX(5px) !important;
            font-weight: 600 !important;
        }
        
        /* 사이드바 활성 링크 스타일 */
        section[data-testid="stSidebar"] a[aria-current="page"],
        section[data-testid="stSidebar"] a[data-baseweb="button"][aria-selected="true"] {
            background-color: #1f77b4 !important;
            color: white !important;
            font-weight: 600 !important;
        }
        
        /* 사이드바 활성 링크 호버 */
        section[data-testid="stSidebar"] a[aria-current="page"]:hover {
            background-color: #1565c0 !important;
            color: white !important;
        }
        
        /* 사이드바 제목/헤더 스타일 */
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            font-size: 1.3rem !important;
            font-weight: 700 !important;
            color: #1f77b4 !important;
            margin-bottom: 1rem !important;
        }
        
        /* 사이드바 텍스트 스타일 */
        section[data-testid="stSidebar"] p {
            font-size: 1rem !important;
            line-height: 1.6 !important;
        }
        
        /* 메인 콘텐츠 영역의 링크는 사이드바 스타일 영향 받지 않도록 */
        [data-testid="stAppViewContainer"] > [data-testid="stAppViewBlockContainer"] a,
        [data-testid="stAppViewContainer"] > [data-testid="stAppViewBlockContainer"] * a {
            font-size: inherit !important;
            font-weight: inherit !important;
            padding: inherit !important;
            margin: inherit !important;
            border-radius: inherit !important;
            display: inherit !important;
            transition: inherit !important;
        }
        
        /* 메인 콘텐츠 영역의 이미지는 사이드바 스타일 영향 받지 않도록 */
        [data-testid="stAppViewContainer"] img,
        [data-testid="stAppViewBlockContainer"] img {
            display: inline-block !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


def display_logo():
    """페이지 상단에 로고 표시"""
    # 현재 파일 위치 기준으로 경로 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "..", "assets", "KETI_logo.svg")
    logo_path = os.path.normpath(logo_path)

    # 제목과 로고를 같은 높이에 배치
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(
            """
            <div style="margin: 0; padding: 0; display: flex; flex-direction: column; justify-content: center; height: 100%;">
                <h1 style="margin: 0; padding: 0; color: #1f77b4;">RAG-eval-framework</h1>
                <p style="margin: 5px 0 0 0; padding: 0; font-size: 12px; color: #666666; line-height: 1.3;">
                    해당 연구는 2024년도 정부(과학기술정보통신부)의 재원으로 정보통신기획평가원의 지원을 받아 수행된 연구임<br>
                    (No.2710017875, 멀티모달 데이터 입력 기반 검색 증강 생성 기술 개발)
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        if os.path.exists(logo_path):
            try:
                # 오른쪽 정렬된 로고
                st.markdown(
                    """
                    <div style="text-align: right; margin: 0; padding: 0; display: flex; justify-content: flex-end; align-items: center; height: 100%;">
                    """,
                    unsafe_allow_html=True,
                )
                st.image(logo_path, width=250)
                st.markdown(
                    """
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.error(f"이미지 로드 실패: {str(e)}")

        else:
            # 로고 파일이 없을 때
            st.markdown(
                """
                <div style="text-align: right; margin: 0; padding: 0; display: flex; justify-content: flex-end;">
                    <a href="https://www.keti.re.kr" target="_blank" 
                       style="text-decoration: none; color: #1f77b4; font-size: 18px; font-weight: bold;">
                        KETI
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def find_conda_python(env_name: str) -> Optional[str]:
    """
    conda 환경의 Python 경로 찾기 (여러 경로 시도)

    Args:
        env_name: conda 환경 이름

    Returns:
        Python 경로 또는 None (conda run 사용)
    """
    # 1. conda run 사용 가능 여부 확인 (가장 선호)
    if shutil.which("conda"):
        # conda run이 작동하는지 간단히 테스트
        try:
            result = subprocess.run(
                ["conda", "run", "-n", env_name, "python", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return None  # conda run 사용
        except:
            pass

    # 2. 환경 변수에서 conda base 경로 확인
    conda_base = os.environ.get("CONDA_PREFIX", "")
    if conda_base:
        conda_base = os.path.dirname(os.path.dirname(conda_base))

    # 3. 일반적인 conda 설치 경로들 시도
    possible_bases = [
        conda_base,
        os.path.expanduser("~/anaconda3"),
        os.path.expanduser("~/miniconda3"),
        os.path.expanduser("~/conda"),
        os.environ.get("CONDA_BASE_PATH", ""),
    ]

    for base in possible_bases:
        if not base:
            continue
        python_path = os.path.join(base, "envs", env_name, "bin", "python")
        if os.path.exists(python_path):
            return python_path

    # 4. 직접 지정된 경로 확인
    env_python = os.environ.get(
        f'CONDA_ENV_{env_name.upper().replace("-", "_")}_PYTHON'
    )
    if env_python and os.path.exists(env_python):
        return env_python

    raise FileNotFoundError(
        f"conda 환경 '{env_name}'을 찾을 수 없습니다.\n"
        f"환경 변수 CONDA_BASE_PATH를 설정하거나, "
        f"CONDA_ENV_{env_name.upper().replace('-', '_')}_PYTHON을 설정하세요."
    )


def run_in_conda_env(
    env_name: str,
    script_path: str,
    args: List[str] = None,
    cwd: str = None,
    **popen_kwargs,
) -> subprocess.Popen:
    """
    특정 conda 환경에서 Python 스크립트 실행

    Args:
        env_name: conda 환경 이름
        script_path: 실행할 스크립트 경로
        args: 스크립트에 전달할 인자들
        cwd: 작업 디렉토리
        **popen_kwargs: subprocess.Popen에 전달할 추가 인자들

    Returns:
        subprocess.Popen 객체
    """
    args = args or []

    try:
        python_path = find_conda_python(env_name)

        if python_path is None:
            # conda run 사용 (가장 선호)
            cmd = ["conda", "run", "-n", env_name, "python", script_path] + args
        else:
            # 직접 Python 경로 사용
            cmd = [python_path, script_path] + args

        # 기본값 설정
        popen_kwargs.setdefault("stdout", subprocess.PIPE)
        popen_kwargs.setdefault("stderr", subprocess.PIPE)
        popen_kwargs.setdefault("text", True)
        popen_kwargs.setdefault("bufsize", 0)
        popen_kwargs.setdefault("universal_newlines", True)

        process = subprocess.Popen(cmd, cwd=cwd, **popen_kwargs)

        return process

    except FileNotFoundError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"conda 환경 '{env_name}'에서 스크립트 실행 실패: {e}")
