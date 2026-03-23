# Build argument로 버전 받기
ARG BASE_VERSION=latest
FROM rag-eval-framework:${BASE_VERSION}

# 작업 디렉토리 설정
WORKDIR /app

# 현재 디렉토리의 모든 파일을 컨테이너로 복사
COPY . /app/