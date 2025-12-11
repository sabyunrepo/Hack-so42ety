.PHONY: help setup dev prod test clean migrate backup down \
	dev-build dev-logs dev-logs-backend dev-logs-nginx dev-stop dev-down dev-restart \
	prod-build prod-logs prod-logs-backend prod-logs-nginx prod-logs-cloudflared prod-stop prod-down prod-restart \
	prod-deploy prod-update prod-health prod-status prod-pull \
	db-shell db-shell-prod db-migrate db-migrate-prod db-rollback db-rollback-prod db-reset db-backup db-backup-prod \
	test-unit test-integration test-e2e test-coverage lint format format-check \
	frontend-dev frontend-build frontend-test \
	clean-all clean-all-prod logs logs-prod logs-backend logs-postgres logs-nginx \
	shell-backend shell-backend-prod shell-postgres shell-postgres-prod ps ps-prod restart ci-test

# ==================== Colors ====================
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m  # No Color

# ==================== Variables ====================
PROJECT_NAME := MoriAI Storybook Service
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_DEV := docker-compose -f docker-compose.yml
DOCKER_COMPOSE_PROD := docker-compose -f docker-compose.prod.yml

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
	@echo "$(BLUE)Starting development environment (APP_ENV=dev)...$(NC)"
	$(DOCKER_COMPOSE_DEV) up -d postgres
	@echo "$(YELLOW)Waiting for PostgreSQL...$(NC)"
	@sleep 5
	$(DOCKER_COMPOSE_DEV) up -d backend nginx
	@echo "$(GREEN)✓ Development services started$(NC)"
	@echo "$(BLUE)Backend API: http://localhost:8000$(NC)"
	@echo "$(BLUE)API Docs: http://localhost:8000/docs$(NC)"
	@echo "$(BLUE)Nginx: http://localhost$(NC)"

dev-build: ## 개발 모드 이미지 빌드
	@echo "$(BLUE)Building development images...$(NC)"
	$(DOCKER_COMPOSE_DEV) build

dev-logs: ## 개발 모드 로그 확인
	$(DOCKER_COMPOSE_DEV) logs -f

dev-logs-backend: ## 개발 모드 백엔드 로그 확인
	$(DOCKER_COMPOSE_DEV) logs -f backend

dev-logs-nginx: ## 개발 모드 Nginx 로그 확인
	$(DOCKER_COMPOSE_DEV) logs -f nginx

dev-stop: ## 개발 모드 중지
	@echo "$(BLUE)Stopping development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) stop

dev-down: ## 개발 모드 중지 및 컨테이너 제거
	@echo "$(BLUE)Stopping and removing development containers...$(NC)"
	$(DOCKER_COMPOSE_DEV) down

dev-restart: ## 개발 모드 재시작
	@echo "$(BLUE)Restarting development environment...$(NC)"
	$(DOCKER_COMPOSE_DEV) restart

down: ## 모든 컨테이너 중지 및 제거 (기본: 개발 환경)
	@echo "$(BLUE)Stopping and removing all containers...$(NC)"
	$(DOCKER_COMPOSE_DEV) down
	@echo "$(GREEN)✓ All containers stopped and removed$(NC)"

# ==================== Production ====================
prod-build: ## 프로덕션 모드 이미지 빌드
	@echo "$(BLUE)Building production images (APP_ENV=prod)...$(NC)"
	$(DOCKER_COMPOSE_PROD) build

prod: prod-build ## 프로덕션 모드 실행
	@echo "$(BLUE)Starting production environment (APP_ENV=prod)...$(NC)"
	$(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)✓ Production services started$(NC)"
	@echo "$(BLUE)Application: http://localhost$(NC)"
	@echo "$(YELLOW)Note: Cloudflare Tunnel is enabled in production$(NC)"

prod-logs: ## 프로덕션 모드 로그 확인
	$(DOCKER_COMPOSE_PROD) logs -f

prod-logs-backend: ## 프로덕션 모드 백엔드 로그 확인
	$(DOCKER_COMPOSE_PROD) logs -f backend

prod-logs-nginx: ## 프로덕션 모드 Nginx 로그 확인
	$(DOCKER_COMPOSE_PROD) logs -f nginx

prod-logs-cloudflared: ## 프로덕션 모드 Cloudflare Tunnel 로그 확인
	$(DOCKER_COMPOSE_PROD) logs -f cloudflared

prod-stop: ## 프로덕션 모드 중지
	@echo "$(BLUE)Stopping production environment...$(NC)"
	$(DOCKER_COMPOSE_PROD) stop

prod-down: ## 프로덕션 모드 중지 및 컨테이너 제거
	@echo "$(BLUE)Stopping and removing production containers...$(NC)"
	$(DOCKER_COMPOSE_PROD) down

prod-restart: ## 프로덕션 모드 재시작
	@echo "$(BLUE)Restarting production environment...$(NC)"
	$(DOCKER_COMPOSE_PROD) restart

prod-deploy: ## 🚀 프로덕션 초기 배포 (환경 설정 + 빌드 + 실행 + 마이그레이션)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)🚀 Production Deployment Starting...$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 1/5: Checking environment...$(NC)"
	@if [ ! -f .env.production ]; then \
		echo "$(RED)❌ .env.production not found!$(NC)"; \
		echo "$(YELLOW)Creating from template...$(NC)"; \
		cp .env.production.example .env.production; \
		echo "$(YELLOW)⚠️  Please edit .env.production with your credentials$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Environment file found$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 2/5: Pulling latest code...$(NC)"
	git pull origin main
	@echo "$(GREEN)✓ Code updated$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 3/5: Building production images...$(NC)"
	$(DOCKER_COMPOSE_PROD) build --no-cache
	@echo "$(GREEN)✓ Images built$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 4/5: Starting services...$(NC)"
	$(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 5/5: Running database migrations...$(NC)"
	@sleep 10
	$(DOCKER_COMPOSE_PROD) exec -T backend alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)🎉 Deployment completed successfully!$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(BLUE)Run 'make prod-status' to check service health$(NC)"

prod-update: ## 🔄 프로덕션 업데이트 (코드 업데이트 + 재빌드 + 재시작 + 마이그레이션)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)🔄 Production Update Starting...$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 1/6: Backing up database...$(NC)"
	$(MAKE) db-backup-prod
	@echo "$(GREEN)✓ Database backed up$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 2/6: Pulling latest code...$(NC)"
	git pull origin main
	@echo "$(GREEN)✓ Code updated$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 3/6: Rebuilding images...$(NC)"
	$(DOCKER_COMPOSE_PROD) build
	@echo "$(GREEN)✓ Images rebuilt$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 4/6: Restarting services...$(NC)"
	$(DOCKER_COMPOSE_PROD) up -d --force-recreate
	@echo "$(GREEN)✓ Services restarted$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 5/6: Running migrations...$(NC)"
	@sleep 10
	$(DOCKER_COMPOSE_PROD) exec -T backend alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 6/6: Checking service health...$(NC)"
	$(MAKE) prod-health
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)🎉 Update completed successfully!$(NC)"
	@echo "$(GREEN)========================================$(NC)"

prod-pull: ## 📥 코드 업데이트만 (Git Pull)
	@echo "$(BLUE)Pulling latest code...$(NC)"
	git pull origin main
	@echo "$(GREEN)✓ Code updated$(NC)"
	@echo "$(YELLOW)Run 'make prod-update' to apply changes$(NC)"

prod-health: ## 🏥 프로덕션 서비스 헬스체크
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)🏥 Production Health Check$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Backend API:$(NC)"
	@curl -f http://localhost/api/health 2>/dev/null && echo " $(GREEN)✓ OK$(NC)" || echo " $(RED)✗ Failed$(NC)"
	@echo ""
	@echo "$(YELLOW)Nginx:$(NC)"
	@curl -f http://localhost 2>/dev/null > /dev/null && echo " $(GREEN)✓ OK$(NC)" || echo " $(RED)✗ Failed$(NC)"
	@echo ""
	@echo "$(YELLOW)PostgreSQL:$(NC)"
	@$(DOCKER_COMPOSE_PROD) exec -T postgres pg_isready -U moriai_user 2>/dev/null && echo " $(GREEN)✓ OK$(NC)" || echo " $(RED)✗ Failed$(NC)"
	@echo ""
	@echo "$(YELLOW)Redis:$(NC)"
	@$(DOCKER_COMPOSE_PROD) exec -T redis redis-cli ping 2>/dev/null && echo " $(GREEN)✓ OK$(NC)" || echo " $(RED)✗ Failed$(NC)"
	@echo ""

prod-status: ## 📊 프로덕션 서비스 상태 확인 (상세)
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)📊 Production Status$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Running Containers:$(NC)"
	@$(DOCKER_COMPOSE_PROD) ps
	@echo ""
	@echo "$(YELLOW)Resource Usage:$(NC)"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -n 10
	@echo ""
	@echo "$(YELLOW)Disk Usage:$(NC)"
	@df -h | grep -E '(Filesystem|/dev/root|/dev/xvda|/dev/nvme)'
	@echo ""
	@$(MAKE) prod-health

# ==================== Database ====================
db-shell: ## PostgreSQL 셸 접속 (개발 환경)
	@echo "$(BLUE)Connecting to PostgreSQL (dev)...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec postgres psql -U moriai_user -d moriai_db

db-shell-prod: ## PostgreSQL 셸 접속 (프로덕션 환경)
	@echo "$(BLUE)Connecting to PostgreSQL (prod)...$(NC)"
	$(DOCKER_COMPOSE_PROD) exec postgres psql -U moriai_user -d moriai_db

db-migrate: ## 데이터베이스 마이그레이션 실행 (개발 환경)
	@echo "$(BLUE)Running database migrations (dev)...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"

db-migrate-prod: ## 데이터베이스 마이그레이션 실행 (프로덕션 환경)
	@echo "$(BLUE)Running database migrations (prod)...$(NC)"
	$(DOCKER_COMPOSE_PROD) exec backend alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"

db-rollback: ## 마이그레이션 롤백 (1단계, 개발 환경)
	@echo "$(YELLOW)Rolling back last migration (dev)...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend alembic downgrade -1

db-rollback-prod: ## 마이그레이션 롤백 (1단계, 프로덕션 환경)
	@echo "$(RED)⚠️  Rolling back in PRODUCTION!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE_PROD) exec backend alembic downgrade -1; \
		echo "$(GREEN)✓ Rollback completed$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

db-reset: ## 데이터베이스 초기화 (⚠️ 주의: 모든 데이터 삭제, 개발 환경)
	@echo "$(RED)⚠️  This will delete all data in DEV!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE_DEV) exec postgres psql -U moriai_user -d moriai_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
		$(MAKE) db-migrate; \
		echo "$(GREEN)✓ Database reset completed$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

db-backup: ## 데이터베이스 백업 (개발 환경)
	@echo "$(BLUE)Backing up database (dev)...$(NC)"
	@mkdir -p backups
	$(DOCKER_COMPOSE_DEV) exec -T postgres pg_dump -U moriai_user moriai_db > backups/backup_dev_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup completed$(NC)"

db-backup-prod: ## 데이터베이스 백업 (프로덕션 환경)
	@echo "$(BLUE)Backing up database (prod)...$(NC)"
	@mkdir -p backups
	$(DOCKER_COMPOSE_PROD) exec -T postgres pg_dump -U moriai_user moriai_db > backups/backup_prod_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup completed$(NC)"

# ==================== Testing ====================
test: ## 전체 테스트 실행 (개발 환경)
	@echo "$(BLUE)Running all tests (dev)...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend pytest tests/ -v

test-unit: ## 단위 테스트만 실행
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend pytest tests/unit/ -v

test-integration: ## 통합 테스트만 실행
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend pytest tests/integration/ -v

test-e2e: ## E2E 테스트 실행
	@echo "$(BLUE)Running E2E tests...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend pytest tests/e2e/ -v

test-coverage: ## 테스트 커버리지 리포트
	@echo "$(BLUE)Generating test coverage report...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend pytest tests/ --cov=backend --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated: htmlcov/index.html$(NC)"

# ==================== Code Quality ====================
lint: ## 코드 린트 (Ruff)
	@echo "$(BLUE)Running linter...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend ruff check backend/

format: ## 코드 포맷 (Black + isort)
	@echo "$(BLUE)Formatting code...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend black backend/
	$(DOCKER_COMPOSE_DEV) exec backend isort backend/

format-check: ## 포맷 검사 (CI용)
	@echo "$(BLUE)Checking code format...$(NC)"
	$(DOCKER_COMPOSE_DEV) exec backend black --check backend/
	$(DOCKER_COMPOSE_DEV) exec backend isort --check backend/

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

clean-all: clean ## 모든 데이터 삭제 (Docker volumes 포함, 개발 환경)
	@echo "$(RED)⚠️  This will delete all Docker volumes and data in DEV!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE_DEV) down -v; \
		rm -rf data/*; \
		echo "$(GREEN)✓ All data deleted$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

clean-all-prod: clean ## 모든 데이터 삭제 (Docker volumes 포함, 프로덕션 환경)
	@echo "$(RED)⚠️  This will delete all Docker volumes and data in PRODUCTION!$(NC)"
	@read -p "Are you ABSOLUTELY sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE_PROD) down -v; \
		echo "$(GREEN)✓ All production data deleted$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ==================== Logs ====================
logs: ## 모든 서비스 로그 확인 (개발 환경)
	$(DOCKER_COMPOSE_DEV) logs -f

logs-prod: ## 모든 서비스 로그 확인 (프로덕션 환경)
	$(DOCKER_COMPOSE_PROD) logs -f

logs-backend: ## 백엔드 로그 확인 (개발 환경)
	$(DOCKER_COMPOSE_DEV) logs -f backend

logs-postgres: ## PostgreSQL 로그 확인 (개발 환경)
	$(DOCKER_COMPOSE_DEV) logs -f postgres

logs-nginx: ## Nginx 로그 확인 (개발 환경)
	$(DOCKER_COMPOSE_DEV) logs -f nginx

# ==================== Utilities ====================
shell-backend: ## 백엔드 컨테이너 셸 접속 (개발 환경)
	$(DOCKER_COMPOSE_DEV) exec backend /bin/bash

shell-backend-prod: ## 백엔드 컨테이너 셸 접속 (프로덕션 환경)
	$(DOCKER_COMPOSE_PROD) exec backend /bin/bash

shell-postgres: ## PostgreSQL 컨테이너 셸 접속 (개발 환경)
	$(DOCKER_COMPOSE_DEV) exec postgres /bin/sh

shell-postgres-prod: ## PostgreSQL 컨테이너 셸 접속 (프로덕션 환경)
	$(DOCKER_COMPOSE_PROD) exec postgres /bin/sh

ps: ## 실행 중인 컨테이너 목록 (개발 환경)
	$(DOCKER_COMPOSE_DEV) ps

ps-prod: ## 실행 중인 컨테이너 목록 (프로덕션 환경)
	$(DOCKER_COMPOSE_PROD) ps

restart: ## 모든 서비스 재시작 (개발 환경)
	$(DOCKER_COMPOSE_DEV) restart

# ==================== CI/CD ====================
ci-test: ## CI 환경에서 테스트 실행
	@echo "$(BLUE)Running CI tests...$(NC)"
	$(DOCKER_COMPOSE_DEV) up -d postgres
	@sleep 10
	$(DOCKER_COMPOSE_DEV) run --rm backend pytest tests/ -v --cov=backend --cov-report=xml

# ==================== Default ====================
.DEFAULT_GOAL := help
