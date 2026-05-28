.PHONY: help install setup run run-worker stop clean test docker-build docker-up docker-down docker-logs lint format

help:
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║     Google Dorking Tool - Available Commands           ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install       - Install dependencies"
	@echo "  make setup         - Run quick setup script"
	@echo ""
	@echo "Running the Application:"
	@echo "  make run           - Start Flask development server"
	@echo "  make run-worker    - Start Celery worker"
	@echo "  make stop          - Stop all running services"
	@echo ""
	@echo "Development:"
	@echo "  make test          - Run unit tests"
	@echo "  make lint          - Run code linting"
	@echo "  make format        - Format code with black"
	@echo "  make clean         - Clean generated files"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-up     - Start Docker containers"
	@echo "  make docker-down   - Stop Docker containers"
	@echo "  make docker-logs   - View Docker logs"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

setup:
	@echo "Running setup script..."
	bash setup.sh
	@echo "✓ Setup complete"

run:
	@echo "Starting Flask development server..."
	@echo "Navigate to: http://localhost:5000"
	python run.py

run-worker:
	@echo "Starting Celery worker..."
	python worker.py

stop:
	@echo "Stopping services..."
	@pkill -f "python run.py" || true
	@pkill -f "celery" || true
	@echo "✓ Services stopped"

test:
	@echo "Running tests..."
	python -m pytest tests.py -v
	@echo "✓ Tests complete"

lint:
	@echo "Linting code..."
	flake8 app/ --max-line-length=120
	@echo "✓ Linting complete"

format:
	@echo "Formatting code with black..."
	black app/ run.py worker.py
	@echo "✓ Formatting complete"

clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".egg-info" -delete
	@echo "✓ Cleanup complete"

docker-build:
	@echo "Building Docker images..."
	docker-compose build
	@echo "✓ Docker images built"

docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d
	@echo "✓ Containers started"
	@echo "Access at: http://localhost:5000"

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down
	@echo "✓ Containers stopped"

docker-logs:
	docker-compose logs -f flask

docker-shell:
	docker-compose exec flask /bin/bash

# Development quick start
dev-setup: install setup
	@echo ""
	@echo "✓ Development environment ready!"
	@echo "Run these commands in separate terminals:"
	@echo "  1. make run"
	@echo "  2. make run-worker"

# Production quick start
prod-setup: install
	@echo ""
	@echo "✓ Production environment ready!"
	@echo "Use Docker for production:"
	@echo "  make docker-build"
	@echo "  make docker-up"
