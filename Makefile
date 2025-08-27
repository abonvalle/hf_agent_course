# Makefile for Final Assignment Template

.PHONY: help install dev check run clean lint format test

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using uv
	uv sync

dev: ## Install with development dependencies
	uv sync --all-extras

check: ## Check if all dependencies are installed
	uv run python check_setup.py

run: ## Run the main application
	uv run python app.py

clean: ## Clean up cache and temporary files
	rm -rf .venv/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

lint: ## Run linting tools
	uv run --extra dev mypy *.py
	uv run --extra dev flake8 *.py

format: ## Format code using black
	uv run --extra dev black *.py

test: ## Run tests
	uv run --extra dev pytest

# Alternative commands for those familiar with pip/poetry
pip-install: ## Install using pip (legacy)
	pip install -r requirements.txt

# Docker commands
docker-build: ## Build Docker image
	docker build -t final-assignment-template:latest .

docker-run: ## Run Docker container
	docker run -d --name final-assignment-app -p 7860:7860 --env-file .env -v "$(PWD):/app" final-assignment-template:latest

docker-up: ## Start with docker-compose
	docker compose up -d

docker-down: ## Stop docker-compose
	docker compose down

docker-stop: ## Stop Docker containers
	docker stop final-assignment-app || true
	docker compose down || true

docker-clean: ## Clean up Docker resources
	docker stop final-assignment-app || true
	docker rm final-assignment-app || true
	docker compose down || true
	docker rmi final-assignment-template:latest || true

docker-logs: ## Show Docker container logs
	docker logs final-assignment-app || docker compose logs

docker-shell: ## Open shell in Docker container
	docker exec -it final-assignment-app /bin/bash
