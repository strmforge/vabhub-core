# VabHub 多仓库管理 Makefile

.PHONY: help status sync build deploy clean test

# 默认目标
help:
	@echo "VabHub 多仓库管理命令"
	@echo ""
	@echo "可用命令:"
	@echo "  make status     显示所有仓库状态"
	@echo "  make sync       同步所有仓库"
	@echo "  make build      构建所有仓库"
	@echo "  make deploy     部署完整系统"
	@echo "  make test       运行测试"
	@echo "  make clean      清理构建文件"
	@echo ""
	@echo "单个仓库操作:"
	@echo "  make sync-core      同步核心仓库"
	@echo "  make build-frontend 构建前端仓库"
	@echo "  make deploy-staging 部署到测试环境"
	@echo ""

# 显示仓库状态
status:
	@python scripts/multi_repo_manager.py status

# 同步所有仓库
sync:
	@python scripts/multi_repo_manager.py sync

# 构建所有仓库
build:
	@python scripts/multi_repo_manager.py build

# 部署完整系统
deploy:
	@python scripts/multi_repo_manager.py deploy

# 单个仓库同步
sync-core:
	@python scripts/multi_repo_manager.py sync --repo vabhub-core

sync-frontend:
	@python scripts/multi_repo_manager.py sync --repo vabhub-frontend

sync-plugins:
	@python scripts/multi_repo_manager.py sync --repo vabhub-plugins

sync-resources:
	@python scripts/multi_repo_manager.py sync --repo vabhub-resources

sync-deploy:
	@python scripts/multi_repo_manager.py sync --repo vabhub-deploy

# 单个仓库构建
build-core:
	@python scripts/multi_repo_manager.py build --repo vabhub-core

build-frontend:
	@python scripts/multi_repo_manager.py build --repo vabhub-frontend

build-plugins:
	@python scripts/multi_repo_manager.py build --repo vabhub-plugins

build-resources:
	@python scripts/multi_repo_manager.py build --repo vabhub-resources

build-deploy:
	@python scripts/multi_repo_manager.py build --repo vabhub-deploy

# 环境特定部署
development:
	@./scripts/deploy_multirepo.sh -e development

staging:
	@./scripts/deploy_multirepo.sh -e staging

production:
	@./scripts/deploy_multirepo.sh -e production

# 测试
test:
	@echo "运行测试..."
	@cd vabhub-Core && python -m pytest tests/ -v
	@cd vabhub-frontend && npm test

# 清理
clean:
	@echo "清理构建文件..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@cd vabhub-frontend && rm -rf node_modules dist .nuxt 2>/dev/null || true
	@echo "清理完成"

# 快速开发命令
dev:
	@echo "启动开发环境..."
	@./scripts/deploy_multirepo.sh -e development

# 查看日志
logs:
	@cd vabhub-deploy && docker-compose logs -f

# 重启服务
restart:
	@cd vabhub-deploy && docker-compose restart

# 停止服务
stop:
	@cd vabhub-deploy && docker-compose down

# 更新所有仓库
update:
	@echo "更新所有仓库..."
	@make sync
	@make build
	@make deploy

# 初始化项目（首次使用）
init:
	@echo "初始化 VabHub 多仓库项目..."
	@make sync
	@make build
	@echo "初始化完成，使用 'make deploy' 启动系统"