# RAG 평가 프레임워크 - Docker Compose 가이드

이 가이드는 Docker Compose를 사용하여 RAG 평가 프레임워크를 실행하는 방법을 설명합니다.

## 🚀 빠른 시작

### 1. 환경 변수 설정

```bash
# 환경 변수 파일 복사
cp env.example .env

# .env 파일을 편집하여 OpenAI API 키 설정
nano .env
```

`.env` 파일에서 `OPENAI_API_KEY`를 실제 API 키로 변경하세요.

### 2. Docker Compose로 서비스 시작

```bash
# 모든 서비스 시작
docker compose up -d

### 3. 서비스 접속
- **API 서버**: http://localhost:5000
- **Streamlit 웹 인터페이스**: http://localhost:8501
- **Milvus (선택사항)**: localhost:19530

## 🛠️ 서비스 관리
### 서비스 재시작

```bash
# 모든 서비스 재시작
docker compose restart

# 특정 서비스만 재시작
docker compose restart rag-api
docker compose restart streamlit-app
```

### 서비스 중지

```bash
# 모든 서비스 중지
docker compose down

# 볼륨까지 삭제하며 중지
docker compose down -v
```

## 🔧 설정 옵션

### 포트 변경

`docker-compose.yml`에서 포트 매핑을 수정할 수 있습니다:

```yaml
services:
  rag-api:
    ports:
      - "8080:5000"  # API 포트를 8080으로 변경
  streamlit-app:
    ports:
      - "8502:8501"  # Streamlit 포트를 8502로 변경
```

### 메모리 제한

```yaml
services:
  rag-api:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### 환경 변수 추가
`docker-compose.yml`의 `environment` 섹션에 추가할 수 있습니다:

```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - CUSTOM_VAR=value
```

## 🐛 문제 해결

### 일반적인 문제

1. **API 서버 연결 실패**
   ```bash
   # API 서버 로그 확인
   docker compose logs rag-api
   
   # API 서버 재시작
   docker compose restart rag-api
   ```

2. **메모리 부족**
   ```bash
   # 시스템 리소스 확인
   docker stats
   
   # 메모리 제한 설정
   # docker compose.yml에서 memory limits 추가
   ```

3. **포트 충돌**
   ```bash
   # 포트 사용 확인
   netstat -tulpn | grep :5000
   netstat -tulpn | grep :8501
   
   # 포트 변경
   # docker-compose.yml에서 포트 매핑 수정
   ```

### 로그 확인

```bash
# 모든 서비스 로그
docker-compose logs

# 실시간 로그 스트리밍
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs rag-api
docker-compose logs streamlit-app
```

### 컨테이너 내부 접속

```bash
# API 서버 컨테이너 접속
docker-compose exec rag-api bash

# Streamlit 앱 컨테이너 접속
docker-compose exec streamlit-app bash

### 리소스 모니터링

```bash
# 컨테이너 리소스 사용량
docker stats

# 특정 컨테이너 모니터링
docker stats rag-api-server
docker stats rag-streamlit-app
```

## 🔄 업데이트

### 이미지 재빌드

```bash
# 버전 업데이트 빌드
bash new_version_build.sh <version>
# ex) bash new_version_build.sh v1.2

### 코드 변경 후 재시작

```bash
# 코드 변경사항 반영
docker-compose restart
```

## 📝 주의사항

1. **OpenAI API 키**: 반드시 `.env` 파일에 올바른 API 키를 설정하세요.
5. **포트 충돌**: 다른 서비스와 포트가 충돌하지 않는지 확인하세요.
