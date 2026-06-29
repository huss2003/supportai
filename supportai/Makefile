.PHONY: install install-dev run-api run-dashboard run-all test test-watch lint lint-fix typecheck check-all seed clean docker-build docker-run help

PYTHON := python
PIP := pip
STREAMLIT := streamlit
UVICORN := uvicorn
DATA_DIR := data

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest-watch

run-api:
	$(UVICORN) supportai.api.main:app --host 0.0.0.0 --port 8000 --reload

run-dashboard:
	$(STREAMLIT) run supportai/dashboard/app.py --server.port 8501

run-all:
	$(UVICORN) supportai.api.main:app --host 0.0.0.0 --port 8000 &
	$(STREAMLIT) run supportai/dashboard/app.py --server.port 8501

test:
	$(PYTHON) -m pytest tests/ -v --cov=supportai --cov-report=term --cov-report=html

test-watch:
	$(PYTHON) -m pytest-watch tests/ -- -v

lint:
	$(PYTHON) -m ruff check supportai/ tests/
	$(PYTHON) -m mypy supportai/ --ignore-missing-imports

lint-fix:
	$(PYTHON) -m ruff check --fix supportai/ tests/

typecheck:
	$(PYTHON) -m mypy supportai/ --ignore-missing-imports

check-all: lint typecheck test

seed:
	$(PYTHON) -m supportai.scripts.seed

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache *.egg-info
	rm -rf supportai/**/__pycache__ tests/**/__pycache__
	rm -rf htmlcov .coverage
	rm -rf $(DATA_DIR)

docker-build:
	docker build -t supportai:latest .

docker-run:
	docker run -d --name supportai -p 8000:8000 -p 8501:8501 supportai:latest

help:
	@echo "install       - install production dependencies"
	@echo "install-dev   - install all dev dependencies"
	@echo "run-api       - start FastAPI dev server on :8000"
	@echo "run-dashboard - start Streamlit dashboard on :8501"
	@echo "run-all       - start both servers"
	@echo "test          - run pytest with coverage"
	@echo "test-watch    - run tests in watch mode"
	@echo "lint          - run ruff + mypy"
	@echo "lint-fix      - auto-fix ruff violations"
	@echo "typecheck     - run mypy only"
	@echo "check-all     - lint + typecheck + test"
	@echo "seed          - seed the database"
	@echo "clean         - remove caches and data"
	@echo "docker-build  - build Docker image"
	@echo "docker-run    - run Docker container"
