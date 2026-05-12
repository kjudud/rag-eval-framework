#!/bin/bash
# Docker 이미지 빌드 및 이전 버전 정리 스크립트
# 사용법: ./new_version_build.sh <version>
# 예시: ./new_version_build.sh v2.0

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "사용법: $0 <version>"
    echo "예시: $0 v2.0"
    exit 1
fi

# 1. 새 버전 빌드 (이전 버전을 베이스로 사용)
echo "🔨 새 버전 빌드 중..."

LATEST_VERSION=$(docker images rag-eval-framework --format "{{.Tag}}" | \
    grep -v "latest" | \
    sort -V | \
    tail -1)
# 프로젝트 루트에서 실행할 것 (-f 및 컨텍스트 . 기준)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"
docker build --build-arg BASE_VERSION=$LATEST_VERSION -f docker_dir/Dockerfile -t rag-eval-framework:$VERSION .

# 2. Docker 이미지 압축 파일 생성
echo "📦 이미지 압축 파일 생성 중..."
docker save rag-eval-framework:$VERSION | gzip > rag-eval-framework-$VERSION.tar.gz
echo "✅ 압축 파일 생성 완료: rag-eval-framework-$VERSION.tar.gz"

# 3. 이전 버전들 삭제 (새 버전 제외)
echo "🧹 이전 버전 삭제 중..."
docker images rag-eval-framework --format "table {{.Tag}}\t{{.CreatedAt}}" | \
    tail -n +2 | \
    grep -v "$VERSION" | \
    awk '{print "rag-eval-framework:" $1}' | \
    xargs -r docker rmi

# 4. 사용하지 않는 레이어 정리
docker image prune -f

# 5. 관련 컨테이너 삭제 (필요시)
docker rm $(docker ps -aq --filter ancestor=rag-eval-framework:v1.0) 2>/dev/null || true

# 6. 완료 및 결과 확인
echo "✅ rag-eval-framework:$VERSION 빌드 완료!"
echo "📊 현재 이미지들:"
docker images | grep rag-eval-framework
echo "📁 생성된 압축 파일:"
ls -lh rag-eval-framework-$VERSION.tar.gz