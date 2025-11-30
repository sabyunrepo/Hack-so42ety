.PHONY: help setup dev prod test clean migrate backup

# ==================== Colors ====================
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m  # No Color

# ==================== Variables ====================
PROJECT_NAME := MoriAI Storybook Service
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_DEV := docker-compose -f docker-compose.yml -f docker-compose.dev.yml

# ==================== Help ====================
help: ## 사용 가능한 명령어 목록 표시
	@echo "$(BLUE)$(PROJECT_NAME) - Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ==================== Setup ====================
setup: ## 초기 설정 (환경 변수 복사, 디렉토리 생성)
	@echo "$(BLUE)Setting up project...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env file created$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env file already exists$(NC)"; \
	fi
	@mkdir -p data/{book,image,video,sound}
	@echo "$(GREEN)✓ Data directories created$(NC)"
	@echo "$(BLUE)Please edit .env file with your credentials$(NC)"

# ==================== Development ====================
dev: ## 개발 모드 실행 (Hot Reload)
	@echo "$(BLUE)Starting development environment...$(NC)"
	$(DOCKER_COMPOSE) up -d postgres
	@echo "$(YELLOW)Waiting for PostgreSQL...$(NC)"
	@sleep 5
	$(DOCKER_COMPOSE) up -d backend
	@echo "$(GREEN)✓ Backend started$(NC)"
	@echo "$(BLUE)Backend: http://localhost:8000$(NC)"
	@echo "$(BLUE)API Docs: http://localhost:8000/docs$(NC)"

dev-logs: ## 개발 모드 로그 확인
	$(DOCKER_COMPOSE) logs -f backend

dev-stop: ## 개발 모드 중지
	$(DOCKER_COMPOSE) stop

# ==================== Production ====================
build: ## Docker 이미지 빌드
	@echo "$(BLUE)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build

prod: build ## 프로덕션 모드 실행
	@echo "$(BLUE)Starting production environment...$(NC)"
	$(DOCKER_COMPOSE) --profile production up -d
	@echo "$(GREEN)✓ All services started$(NC)"
	@echo "$(BLUE)Application: http://localhost$(NC)"

prod-logs: ## 프로덕션 모드 로그 확인
	$(DOCKER_COMPOSE) logs -f

prod-stop: ## 프로덕션 모드 중지
	$(DOCKER_COMPOSE) --profile production down

# ==================== Database ====================
db-shell: ## PostgreSQL 셸 접속
	@echo "$(BLUE)Connecting to PostgreSQL...$(NC)"
	$(DOCKER_COMPOSE) exec postgres psql -U moriai_user -d moriai_db

db-migrate: ## 데이터베이스 마이그레이션 실행
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(DOCKER_COMPOSE) exec backend alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"

db-rollback: ## 마이그레이션 롤백 (1단계)
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	$(DOCKER_COMPOSE) exec backend alembic downgrade -1

db-reset: ## 데이터베이스 초기화 (⚠️ 주의: 모든 데이터 삭제)
	@echo "$(RED)⚠️  This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) exec postgres psql -U moriai_user -d moriai_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
		$(MAKE) db-migrate; \
		echo "$(GREEN)✓ Database reset completed$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

db-backup: ## 데이터베이스 백업
	@echo "$(BLUE)Backing up database...$(NC)"
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec -T postgres pg_dump -U moriai_user moriai_db > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup completed$(NC)"

# ==================== Testing ====================
test: ## 전체 테스트 실행
	@echo "$(BLUE)Running all tests...$(NC)"
	$(DOCKER_COMPOSE) exec backend pytest tests/ -v

test-unit: ## 단위 테스트만 실행
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(DOCKER_COMPOSE) exec backend pytest tests/unit/ -v

test-integration: ## 통합 테스트만 실행
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(DOCKER_COMPOSE) exec backend pytest tests/integration/ -v

test-e2e: ## E2E 테스트 실행
	@echo "$(BLUE)Running E2E tests...$(NC)"
	$(DOCKER_COMPOSE) exec backend pytest tests/e2e/ -v

test-coverage: ## 테스트 커버리지 리포트
	@echo "$(BLUE)Generating test coverage report...$(NC)"
	$(DOCKER_COMPOSE) exec backend pytest tests/ --cov=backend --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated: htmlcov/index.html$(NC)"

# ==================== Code Quality ====================
lint: ## 코드 린트 (Ruff)
	@echo "$(BLUE)Running linter...$(NC)"
	$(DOCKER_COMPOSE) exec backend ruff check backend/

format: ## 코드 포맷 (Black + isort)
	@echo "$(BLUE)Formatting code...$(NC)"
	$(DOCKER_COMPOSE) exec backend black backend/
	$(DOCKER_COMPOSE) exec backend isort backend/

format-check: ## 포맷 검사 (CI용)
	@echo "$(BLUE)Checking code format...$(NC)"
	$(DOCKER_COMPOSE) exec backend black --check backend/
	$(DOCKER_COMPOSE) exec backend isort --check backend/

# ==================== Frontend ====================
frontend-dev: ## 프론트엔드 개발 모드 실행
	@echo "$(BLUE)Starting frontend development server...$(NC)"
	cd frontend && npm run dev

frontend-build: ## 프론트엔드 빌드
	@echo "$(BLUE)Building frontend...$(NC)"
	cd frontend && npm run build

frontend-test: ## 프론트엔드 테스트
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && npm run test

# ==================== Cleanup ====================
clean: ## 임시 파일 및 캐시 정리
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

clean-all: clean ## 모든 데이터 삭제 (Docker volumes 포함)
	@echo "$(RED)⚠️  This will delete all Docker volumes and data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		rm -rf data/*; \
		echo "$(GREEN)✓ All data deleted$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ==================== Logs ====================
logs: ## 모든 서비스 로그 확인
	$(DOCKER_COMPOSE) logs -f

logs-backend: ## 백엔드 로그 확인
	$(DOCKER_COMPOSE) logs -f backend

logs-postgres: ## PostgreSQL 로그 확인
	$(DOCKER_COMPOSE) logs -f postgres

logs-nginx: ## Nginx 로그 확인
	$(DOCKER_COMPOSE) logs -f nginx

# ==================== Utilities ====================
shell-backend: ## 백엔드 컨테이너 셸 접속
	$(DOCKER_COMPOSE) exec backend /bin/bash

shell-postgres: ## PostgreSQL 컨테이너 셸 접속
	$(DOCKER_COMPOSE) exec postgres /bin/sh

ps: ## 실행 중인 컨테이너 목록
	$(DOCKER_COMPOSE) ps

restart: ## 모든 서비스 재시작
	$(DOCKER_COMPOSE) restart

# ==================== CI/CD ====================
ci-test: ## CI 환경에서 테스트 실행
	@echo "$(BLUE)Running CI tests...$(NC)"
	$(DOCKER_COMPOSE) up -d postgres
	@sleep 10
	$(DOCKER_COMPOSE) run --rm backend pytest tests/ -v --cov=backend --cov-report=xml

# ==================== Default ====================
.DEFAULT_GOAL := help
