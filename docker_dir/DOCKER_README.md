# Docker Compose

Compose·Dockerfile·스크립트는 **`docker_dir/`** 에 있습니다.

## 빠른 시작

1. **환경 변수** — 프로젝트 루트의 `env.example`을 복사해 `docker_dir/.env`를 만들고 `OPENAI_API_KEY` 등을 설정합니다.

   ```bash
   cp env.example docker_dir/.env
   ```

2. **실행** — 아래 중 하나입니다.

   ```bash
   cd docker_dir
   docker compose up -d
   ```

   프로젝트 루트에 있을 때는 `docker compose -f docker_dir/docker-compose.yml up -d`

3. **접속** (`docker_dir/docker-compose.yml` 기준 호스트 포트)

   | 구분 | URL |
   |------|-----|
   | API | http://localhost:20500 |
   | Streamlit | http://localhost:20501 |

Compose는 이미지 `rag-eval-framework:v${VERSION:-latest}` 를 사용합니다. 로컬에 해당 태그가 없으면 아래 **이미지 빌드**를 먼저 하거나, 배포된 tar를 `docker load` 한 뒤 실행하세요.

## 자주 쓰는 명령

`docker compose`는 **`docker_dir`에서** 실행하는 편이 단순합니다.

```bash
cd docker_dir
docker compose down
docker compose logs -f rag-app
docker compose restart rag-app
docker compose exec rag-app bash
```

서비스 이름은 `rag-app`, 컨테이너 이름은 `rag-eval-framework` 입니다.

## 이미지 빌드

빌드 컨텍스트는 항상 **프로젝트 루트**(`requirements.txt`·앱 코드 포함)입니다.

- **베이스 이미지** (최초 `latest` 등)

  ```bash
  docker build -f docker_dir/Dockerfile.base -t rag-eval-framework:latest .
  ```

- **버전 이미지 + tar.gz** (`new_version_build.sh`는 스크립트 위치를 기준으로 루트로 이동한 뒤 빌드합니다)

  ```bash
  bash docker_dir/new_version_build.sh v1.2
  ```

  생성물 `rag-eval-framework-<버전>.tar.gz`는 **프로젝트 루트**에 생깁니다.

## 그 외

- **포트·환경 변수**: `docker_dir/docker-compose.yml` 의 `ports`, `environment` 를 수정합니다.
- **저장 이미지로 기동**: `docker_dir`에서 `bash docker-start.sh` (같은 디렉터리에 `rag-eval-framework-v*.tar.gz` 가 있어야 합니다).
