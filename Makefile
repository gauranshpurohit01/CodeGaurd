.PHONY: help demo seed test matrix run-backend run-frontend build-frontend build-sandbox install clean

PYTHON ?= .venv/bin/python3
PYTEST ?= .venv/bin/pytest
UVICORN ?= .venv/bin/uvicorn

help:
	@echo "CodeGuard - Compiler Construction & Plagiarism Detection Platform"
	@echo "Available commands:"
	@echo "  make demo            - Run end-to-end scripted demo (Python -> C -> Sandbox -> Detection)"
	@echo "  make seed            - Populate database with realistic mock submissions"
	@echo "  make test            - Run all pytest test suites"
	@echo "  make matrix          - Run full 8-family benchmark corpus similarity matrix"
	@echo "  make run-backend     - Start FastAPI backend server on port 8000"
	@echo "  make run-frontend    - Start Vite React frontend server on port 5173"
	@echo "  make build-frontend  - Build production frontend bundle"
	@echo "  make build-sandbox   - Build Alpine Docker sandbox image (codeguard-sandbox:latest)"
	@echo "  make install         - Install Python and Node dependencies"
	@echo "  make clean           - Remove temporary build and cache files"

demo:
	$(PYTHON) backend/app/demo.py

seed:
	$(PYTHON) backend/app/seed_data.py

build-sandbox:
	docker build -t codeguard-sandbox:latest -f docker/Dockerfile.sandbox docker


test:
	$(PYTEST) -v

matrix:
	$(PYTHON) tests/test_corpus_matrix.py

run-backend:
	$(UVICORN) app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf frontend/dist
