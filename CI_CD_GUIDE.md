# 🚀 CI/CD 및 배포 환경 구성 가이드

이 문서는 GitHub Actions를 이용한 자동 배포 시스템 구축을 위한 환경 설정 가이드입니다.

---

## 1. GitHub Repository 설정 (Secrets)

GitHub Actions가 GHCR(Container Registry)에 접근하고 이미지를 푸시하기 위해 권한 설정이 필요합니다.

### 1-1. GitHub Token 권한 설정
1. GitHub 리포지토리 설정 페이지로 이동: `Settings` > `Actions` > `General`
2. **Workflow permissions** 섹션에서:
   - ✅ **Read and write permissions** 선택
   - ✅ **Allow GitHub Actions to create and approve pull requests** 체크
3. `Save` 저장

### 1-2. GitHub Container Registry (GHCR) 사용
별도의 Secret 설정 없이 `GITHUB_TOKEN`을 사용하도록 워크플로우가 구성되어 있습니다. 위 권한 설정만 되어 있다면 자동으로 동작합니다.

---

## 2. 배포 서버 (Dev/Prod) 환경 구성

서버에서 도커 이미지를 받아 실행하기 위한 준비 과정입니다.

### 2-1. 필수 도구 설치
`make`와 `docker`, `docker-compose`가 설치되어 있어야 합니다.

```bash
# Docker & Docker Compose 설치 (Ubuntu 기준)
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg make
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Docker 리포지토리 추가
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 권한 설정 (로그아웃 후 재로그인 필요)
sudo usermod -aG docker $USER
```

### 2-2. 환경 변수 파일 생성 (.env.prod)
프로덕션(또는 Dev 서버) 실행을 위한 환경 변수 파일을 생성해야 합니다.

```bash
# 서버의 프로젝트 루트에서 실행
cp .env.example .env.prod
vi .env.prod
```

**⚠️ 중요 변경 사항 (Prod 환경):**
- `APP_ENV=prod`
- `DEBUG=false`
- `POSTGRES_HOST=postgres`
- `REDIS_HOST=redis`
- `STORAGE_PROVIDER=local` (또는 s3)

### 2-3. 초기 배포 명령어
서버에 처음 프로젝트를 세팅할 때 다음 명령어를 실행합니다.

```bash
# 1. 코드 가져오기
git clone https://github.com/YOUR_ORG/Hack-so42ety.git
cd Hack-so42ety

# 2. 초기 배포 (이미지 Pull -> 실행 -> 마이그레이션)
make prod-deploy
```

---

## 3. 자동 배포 테스트 (현재 브랜치)

현재 작업 중인 브랜치(`infra/git_action_develop`)에서 CI/CD를 테스트하는 방법입니다.

1. **코드 푸시:**
   ```bash
   git add .
   git commit -m "chore: configure ci and production docker settings"
   git push origin infra/git_action_develop
   ```

2. **GitHub Actions 확인:**
   GitHub 리포지토리의 `Actions` 탭에서 워크플로우가 **초록색(Success)**으로 끝나는지 확인합니다.

3. **이미지 확인:**
   GitHub 리포지토리 메인 화면 우측 하단의 `Packages` 섹션에 `moriai-backend`, `moriai-frontend` 패키지가 생성되었는지 확인합니다.

---

## 4. (참고) Watchtower### 6. 자동 업데이트 설정 (Watchtower) - **설정 완료됨**

이제 `docker-compose.prod.yml`에 **Watchtower**가 포함되어 있습니다.
따라서 별도의 설정 없이 `make prod-deploy`를 실행하면 자동으로 Watchtower가 함께 실행됩니다.

Watchtower는 5분마다 레지스트리를 검사하여 새 이미지가 있으면 자동으로 서비스를 재시작합니다.

**로그 확인:**
```bash
docker logs -f watchtower
```
