"""
Streamlit 메인 페이지 - 홈/대시보드
Streamlit의 멀티페이지 기능을 사용하여 pages/ 디렉토리의 파일들이 자동으로 서브페이지로 등록됩니다.
"""

import streamlit as st
import os

from utils import display_logo, apply_sidebar_style

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="RAG-eval-framework",
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

# 메인 페이지 콘텐츠
st.title("🔬 RAG 평가 프레임워크")
st.markdown("---")

st.markdown("""
### 📋 개요

이 프레임워크는 테스트 데이터셋 생성부터 평가 리포팅까지 RAG 평가를 위한 End-to-End 과정을 지원합니다.

### 🚀 주요 기능

1. **Step 1: Benchmark Generation**
   - JSON 형식의 corpus 파일 업로드
   - DataMorgana를 사용한 QA 데이터 생성
   - 생성된 QA 데이터 미리보기 및 다운로드

2. **Step 2: RAG 실행**
   - 참가자의 RAG API 호출
   - 배치 방식으로 질문에 대한 답변 생성
   - RAG 실행 결과 저장 및 표시

3. **Step 3: Evaluation**
   - RAGChecker를 사용한 성능 평가
   - 다양한 메트릭 계산 (retriever, generator 등)
   - 평가 결과 다운로드

4. **API 테스트**
   - RAG API 직접 테스트
   - 단일/배치 질의 테스트
   - API 스펙 정보 확인

### 📖 사용 방법

1. **Step 1**에서 corpus 파일을 업로드하고 QA 데이터를 생성합니다.
2. **Step 2**에서 생성된 QA 데이터를 사용하여 RAG API를 호출합니다.
3. **Step 3**에서 RAG 실행 결과를 평가합니다.
4. **API 테스트**에서 API를 직접 테스트할 수 있습니다.

### 📌 Acknowledgment
해당 연구는 2024년도 정부(과학기술정보통신부)의 재원으로 정보통신기획평가원의 지원을 받아 수행된 연구임
(No.2710017875, 멀티모달 데이터 입력 기반 검색 증강 생성 기술 개발)
""")

st.markdown("---")

# 파이프라인 다이어그램
st.subheader("🔄 평가 파이프라인")

# 다이어그램 이미지 표시
# 현재 파일 위치 기준으로 경로 계산
current_dir = os.path.dirname(os.path.abspath(__file__))
diagram_path = os.path.join(current_dir, "..", "assets", "diagram.png")
diagram_path = os.path.normpath(diagram_path)

if os.path.exists(diagram_path):
    st.image(diagram_path, use_container_width=True, caption="RAG 평가 프레임워크 전체 동작 과정")
    
st.markdown("""
```
Corpus 파일 업로드
        ↓
    QA 데이터 생성 (Step 1)
        ↓
    RAG API 호출 (Step 2)
        ↓
    성능 평가 (Step 3)
        ↓
    결과 리포팅 (step 4)
```
""")

st.info("💡 **시작하기**: 왼쪽 사이드바에서 'Step Benchmark Generation' 페이지를 선택하여 시작하세요!")
