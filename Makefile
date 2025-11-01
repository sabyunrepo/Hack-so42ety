.PHONY: up down logs build rebuild clean help certs

# Docker Compose 설정
COMPOSE_FILE = docker-compose.yml
COMPOSE = docker compose -f $(COMPOSE_FILE)

# 인증서 설정
CERTS_DIR = docker/nginx/certs
CERT_FILE = $(CERTS_DIR)/nginx.crt
KEY_FILE = $(CERTS_DIR)/nginx.key

# 기본 타겟
.DEFAULT_GOAL := help

## certs: SSL 인증서 생성 (SAN 포함)
certs:
	@echo "==================================================="
	@echo "  SSL 인증서 생성 중..."
	@echo "==================================================="
	@mkdir -p $(CERTS_DIR)
	@if [ ! -f "$(CERT_FILE)" ]; then \
		echo "🔐 Generating SSL certificate with SAN..."; \
		openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
			-keyout $(KEY_FILE) \
			-out $(CERT_FILE) \
			-subj "/C=KR/ST=Seoul/L=Seoul/O=MoriAI/OU=Development/CN=localhost" \
			-addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:::1"; \
		chmod 644 $(CERT_FILE); \
		chmod 600 $(KEY_FILE); \
		echo "✅ Certificate: $(CERT_FILE)"; \
		echo "✅ Private Key: $(KEY_FILE)"; \
	else \
		echo "✅ SSL 인증서가 이미 존재합니다."; \
	fi
	@echo "==================================================="

## up: 모든 서비스 시작 (detached mode)
up: certs
	@echo "==================================================="
	@echo "  Docker 이미지 빌드 및 서비스 시작 중..."
	@echo "==================================================="
	$(COMPOSE) up -d --build
	@echo "==================================================="
	@echo "  완료! 서비스가 시작되었습니다."
	@echo "==================================================="

## down: 모든 서비스 중지 및 볼륨 삭제
down:
	$(COMPOSE) down -v

## logs: 모든 서비스 로그 출력 (실시간)
logs:
	$(COMPOSE) logs -f

## build: 특정 서비스 빌드 (사용법: make build <서비스명>)
build:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Error: 서비스명이 필요합니다."; \
		echo "사용법: make build <서비스명>"; \
		echo "예시: make build nginx"; \
		exit 1; \
	fi
	$(COMPOSE) build $(filter-out $@,$(MAKECMDGOALS))

## rebuild: 특정 서비스 재빌드 및 재시작 (사용법: make rebuild <서비스명>)
rebuild:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Error: 서비스명이 필요합니다."; \
		echo "사용법: make rebuild <서비스명>"; \
		echo "예시: make rebuild nginx"; \
		exit 1; \
	fi
	$(COMPOSE) up -d --build $(filter-out $@,$(MAKECMDGOALS))

## rebuild-nocache: 특정 서비스 캐시 없이 재빌드 및 재시작 (사용법: make rebuild-nocache <서비스명>)
rebuild-no:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Error: 서비스명이 필요합니다."; \
		echo "사용법: make rebuild-nocache <서비스명>"; \
		echo "예시: make rebuild-nocache nginx"; \
		exit 1; \
	fi
	@echo "==================================================="
	@echo "  [$(filter-out $@,$(MAKECMDGOALS))] 캐시 없이 빌드 시작..."
	@echo "==================================================="
	$(COMPOSE) build --no-cache $(filter-out $@,$(MAKECMDGOALS))
	@echo "==================================================="
	@echo "  [$(filter-out $@,$(MAKECMDGOALS))] 재시작 중..."
	@echo "==================================================="
	$(COMPOSE) up -d $(filter-out $@,$(MAKECMDGOALS))
	@echo "==================================================="
	@echo "  완료!"
	@echo "==================================================="

# 서비스명을 타겟으로 받기 위한 패턴
%:
	@:

## build-all: 모든 서비스 빌드
build-all:
	$(COMPOSE) build

## restart: 모든 서비스 재시작
restart:
	$(COMPOSE) restart

## stop: 모든 서비스 중지 (볼륨 유지)
stop:
	$(COMPOSE) stop

## ps: 실행 중인 컨테이너 확인
ps:
	$(COMPOSE) ps

## clean: 모든 컨테이너, 네트워크, 볼륨, 이미지, 빌드 캐시 완전 정리
clean:
	@echo "==================================================="
	@echo "  전체 정리 시작 (컨테이너, 볼륨, 이미지, 빌드 캐시)"
	@echo "==================================================="
	$(COMPOSE) down -v --rmi all --remove-orphans
	@echo ""
	@echo "빌드 캐시 정리 중..."
	docker builder prune -f
	@echo ""
	@echo "사용하지 않는 볼륨 정리 중..."
	docker volume prune -f
	@echo ""
	@echo "==================================================="
	@echo "  정리 완료!"
	@echo "==================================================="

## help: Makefile 명령어 도움말
help:
	@echo "==================================================="
	@echo "  MoriAI Docker Compose Makefile"
	@echo "==================================================="
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
	@echo ""
	@echo "서비스 목록:"
	@echo "  - tts-api"
	@echo "  - frontend-builder"
	@echo "  - nginx"
	@echo ""
