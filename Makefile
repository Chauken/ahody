# Autocompletion for Makefile
.PHONY: setup install run lint lint-mypy lint-black lint-isort run-uvicorn

setup:
	@echo "Setting up Poetry environment..."
	poetry install --no-root

run:
	@echo "Running FastAPI development server using FastAPI CLI..."
	poetry run fastapi dev app/main.py --host 0.0.0.0 --port 8000

run-uvicorn:
	@echo "Running FastAPI development server using uvicorn..."
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --workers 1

run-docker:
	@echo "Building and running Docker container..."
	docker compose up --build

lint-mypy:
	@poetry run mypy app

lint-black:
	@poetry run black app

lint-isort:
	@poetry run isort app

lint: lint-mypy lint-black lint-isort

test:
	@echo "Running tests..."
	poetry run pytest
