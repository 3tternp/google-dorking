# Docker Setup for Google Dorking Tool

## Dockerfile for Flask Application

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Default command
CMD ["python", "run.py"]

## docker-compose.yml

version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: google-dorking-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  flask:
    build: .
    container_name: google-dorking-flask
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=False
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./app:/app/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  celery_worker:
    build: .
    container_name: google-dorking-worker
    command: python worker.py
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./app:/app/app
    restart: on-failure

volumes:
  redis_data:

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed

### Steps

1. Create Dockerfile and docker-compose.yml as shown above

2. Copy .env.example to .env and update if needed:
   ```bash
   cp .env.example .env
   ```

3. Build and start services:
   ```bash
   docker-compose up -d
   ```

4. Check service status:
   ```bash
   docker-compose ps
   ```

5. View logs:
   ```bash
   docker-compose logs -f flask
   docker-compose logs -f celery_worker
   ```

6. Access application:
   - Web UI: http://localhost:5000
   - API: http://localhost:5000/api/

7. Stop services:
   ```bash
   docker-compose down
   ```

## Useful Docker Commands

```bash
# View all containers
docker-compose ps

# Rebuild images
docker-compose build --no-cache

# Execute command in container
docker-compose exec flask python run.py

# View container logs
docker-compose logs flask -f

# Stop all services
docker-compose stop

# Remove all containers
docker-compose down -v

# Run single command and exit
docker-compose run --rm flask python tests.py
```
