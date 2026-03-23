#!/bin/bash
# RAG Eval Framework Docker 이미지 로드 및 실행 스크립트

set -e  # 오류 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 버전 확인
if [ $# -eq 0 ]; then
    # 최신 버전 찾기
    LATEST_VERSION=$(ls rag-eval-framework-v*.tar.gz 2>/dev/null | \
        sed 's/rag-eval-framework-v\(.*\)\.tar\.gz/\1/' | \
        sort -V | \
        tail -1)
    
    if [ -z "$LATEST_VERSION" ]; then
        print_error "rag-eval-framework 이미지 파일을 찾을 수 없습니다."
        exit 1
    fi
    
    VERSION="$LATEST_VERSION"
    print_info "최신 버전 발견: $VERSION"
else
    VERSION="$1"
fi

# 이미지 파일명 생성
IMAGE_FILE="rag-eval-framework-v$VERSION.tar.gz"

# 이미지 파일 존재 확인
if [ ! -f "$IMAGE_FILE" ]; then
    print_error "이미지 파일을 찾을 수 없습니다: $IMAGE_FILE"
    exit 1
fi

print_info "=== RAG Eval Framework Docker 이미지 로드 및 실행 ==="
print_info "선택된 버전: $VERSION"

# 1. 기존 컨테이너 중지 및 제거
print_info "기존 컨테이너 정리 중..."
if docker ps -q -f name=rag-eval-framework | grep -q .; then
    print_info "기존 컨테이너 중지 중..."
    docker stop rag-eval-framework
fi

if docker ps -aq -f name=rag-eval-framework | grep -q .; then
    print_info "기존 컨테이너 제거 중..."
    docker rm rag-eval-framework
fi

# 2. Docker 이미지 로드
print_info "Docker 이미지 로드 중: $IMAGE_FILE"
if docker load -i "$IMAGE_FILE"; then
    print_success "이미지 로드 완료"
else
    print_error "이미지 로드 실패"
    exit 1
fi

# 3. 이미지 확인
print_info "로드된 이미지 확인 중..."
docker images | grep rag-eval-framework

# 4. 환경 변수 확인
if [ -z "$OPENAI_API_KEY" ]; then
    print_warning "OPENAI_API_KEY 환경 변수가 설정되지 않았습니다."
    print_info "env.example 파일을 참고하여 환경 변수를 설정하세요."
    print_info "예: export OPENAI_API_KEY=your_api_key_here"
fi
export VERSION="$VERSION"  # 환경변수로 설정
# 5. Docker Compose로 실행
print_info "Docker Compose로 서비스 시작 중..."
if docker compose up -d; then
    print_success "서비스 시작 완료"
else
    print_error "서비스 시작 실패"
    exit 1
fi

# 6. 서비스 상태 확인
print_info "서비스 상태 확인 중..."
sleep 5
docker ps

# 7. 접속 정보 출력
print_success "=== 서비스 실행 완료 ==="
print_success "실행된 버전: $VERSION"
echo -e "${GREEN}API 서버:${NC} http://localhost:5000"
echo -e "${GREEN}Streamlit 웹 인터페이스:${NC} http://localhost:8501"
echo ""
print_info "로그 확인: docker logs rag-eval-framework"
print_info "컨테이너 중지: docker stop rag-eval-framework"
print_info "컨테이너 제거: docker rm rag-eval-framework"
print_info "컨테이너 재시작: docker restart rag-eval-framework"