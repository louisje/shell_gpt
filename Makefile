.PHONY: install install-dev install-test clean test test-coverage lint format type-check pre-commit build publish help

# 顏色定義
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## 顯示此幫助訊息
	@echo "$(BLUE)可用的指令：$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## 安裝套件
	pip install .

install-dev: ## 安裝開發環境依賴
	pip install -e ".[dev,test,litellm]"
	pre-commit install

install-test: ## 僅安裝測試依賴
	pip install -e ".[test]"

clean: ## 清理建置檔案和快取
	@echo "$(YELLOW)清理中...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	@echo "$(GREEN)清理完成！$(NC)"

test: ## 執行測試
	pytest tests/ -v

test-coverage: ## 執行測試並產生覆蓋率報告
	pytest tests/ -v --cov=sgpt --cov-report=html --cov-report=term

test-integration: ## 執行整合測試
	pytest tests/_integration.py -v

lint: ## 執行程式碼檢查 (ruff)
	ruff check sgpt/ tests/

lint-fix: ## 自動修復程式碼問題
	ruff check --fix sgpt/ tests/

format: ## 格式化程式碼
	black sgpt/ tests/
	isort sgpt/ tests/

format-check: ## 檢查程式碼格式
	black --check sgpt/ tests/
	isort --check sgpt/ tests/

type-check: ## 執行型別檢查
	mypy sgpt/

spell-check: ## 執行拼字檢查
	codespell sgpt/ tests/ README.md CONTRIBUTING.md

pre-commit: ## 執行 pre-commit 所有檢查
	pre-commit run --all-files

build: clean ## 建置套件
	@echo "$(YELLOW)建置中...$(NC)"
	pip install --upgrade build
	python -m build
	@echo "$(GREEN)建置完成！$(NC)"

publish-test: build ## 發布到 TestPyPI
	pip install --upgrade twine
	twine upload --repository testpypi dist/*

publish: build ## 發布到 PyPI
	@echo "$(YELLOW)確認要發布到 PyPI？ [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	pip install --upgrade twine
	twine upload dist/*

docker-build: ## 建置 Docker 映像
	docker build -t shell_gpt .

docker-run: ## 執行 Docker 容器
	docker run -it shell_gpt

check-all: format lint type-check spell-check test ## 執行所有檢查
	@echo "$(GREEN)所有檢查通過！$(NC)"

version: ## 顯示當前版本
	@python -c "from sgpt.__version__ import __version__; print(__version__)"

deps-update: ## 顯示可更新的依賴
	pip list --outdated

# 開發工作流程
dev-setup: clean install-dev ## 完整的開發環境設置
	@echo "$(GREEN)開發環境設置完成！$(NC)"
	@echo "執行 'make help' 查看可用指令"

# CI/CD 用的指令
ci-test: install-test test lint type-check spell-check ## CI 環境執行的測試
