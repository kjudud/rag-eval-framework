# 기존 이미지를 베이스로 사용
FROM rag-eval-framework:v1.0

# 작업 디렉토리 설정
WORKDIR /app

# 현재 디렉토리의 모든 파일을 컨테이너로 복사
COPY . /app/

# 포트 노출
EXPOSE 5000 8501
