# Quick Start Guide

Get the Google Dorking Tool running in 5 minutes!

## Prerequisites

- Python 3.8+
- Redis server
- Git (optional)

## Installation (5 min)

### Option 1: Traditional Setup (Recommended for Development)

```bash
# 1. Navigate to project directory
cd /home/prem/google-dorking

# 2. Run quick setup
bash setup.sh

# 3. Activate virtual environment
source venv/bin/activate

# 4. Make sure Redis is running
redis-cli ping  # Should return "PONG"

# If Redis not running, start it:
# redis-server

# 5. Terminal 1 - Start Flask server
python run.py

# 6. Terminal 2 - Start Celery worker
python worker.py

# 7. Open browser
# http://localhost:5000
```

### Option 2: Docker Setup (1 command!)

```bash
# 1. Navigate to project directory
cd /home/prem/google-dorking

# 2. Start everything
docker-compose up -d

# 3. Open browser
# http://localhost:5000

# View logs
docker-compose logs -f flask
```

### Option 3: Using Make Commands

```bash
# Install and setup
make dev-setup

# Terminal 1: Run Flask
make run

# Terminal 2: Run Worker
make run-worker
```

---

## First Scan (2 min)

1. **Open Web Interface**: Navigate to `http://localhost:5000`

2. **Enter Domain**: 
   - Simple: `example.com`
   - Wildcard: `example.*.com`
   - Full URL: `https://api.example.com`

3. **Select Categories** (Optional):
   - Leave blank for all categories
   - Or select specific ones like "wordpress", "phpmyadmin"

4. **Click "Start Scan"**

5. **Watch Progress**: Real-time progress bar updates as queries execute

6. **View Results**: Results displayed by category with success rates

7. **Export Results**: Download as JSON or CSV

---

## Troubleshooting

### Redis Connection Error

```bash
# Check if Redis is running
redis-cli ping

# Start Redis
redis-server

# Or run in Docker
docker run -d -p 6379:6379 redis:latest
```

### Port Already in Use

```bash
# Change the port in .env
FLASK_PORT=8000

# Or kill the process
lsof -i :5000
kill -9 <PID>
```

### Tasks Stuck in PENDING

```bash
# Restart the Celery worker
# Kill the worker process and restart:
python worker.py
```

### Slow Scans

```bash
# Increase REQUEST_DELAY_SECONDS in .env (default 1.5)
# This avoids Google rate limiting
REQUEST_DELAY_SECONDS=2.0

# Or increase Celery workers
celery -A app.tasks worker --concurrency=8
```

---

## Useful Commands

```bash
# Using Make
make run              # Start Flask
make run-worker       # Start Celery
make stop             # Stop services
make test             # Run tests
make clean            # Clean files

# Using Manual Commands
python run.py                    # Flask server
python worker.py                 # Celery worker
celery -A app.tasks worker       # Alternative worker start
python -m pytest tests.py        # Run tests

# Using Docker
docker-compose up -d             # Start all services
docker-compose down              # Stop all services
docker-compose logs -f flask     # View logs
docker-compose exec flask bash   # Shell access
```

---

## API Quick Reference

### Start Scan
```bash
curl -X POST http://localhost:5000/api/start-scan \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "categories": ["wordpress"]}'
```

### Check Status
```bash
curl http://localhost:5000/api/scan-status/TASK_ID
```

### Get Results
```bash
curl http://localhost:5000/api/scan-results/TASK_ID
```

### Export Results
```bash
# JSON
curl http://localhost:5000/api/export-results/TASK_ID?format=json -o results.json

# CSV
curl http://localhost:5000/api/export-results/TASK_ID?format=csv -o results.csv
```

### Get Categories
```bash
curl http://localhost:5000/api/categories
```

---

## File Structure Overview

```
google-dorking/
├── app/
│   ├── dorking_queries.py      # 200+ dorking queries
│   ├── search_engine.py        # Google search implementation
│   ├── tasks.py                # Background task execution
│   ├── routes.py               # API and web endpoints
│   ├── templates/              # HTML pages
│   └── static/                 # CSS and JavaScript
├── run.py                      # Start Flask server
├── worker.py                   # Start Celery worker
├── requirements.txt            # Python dependencies
├── Makefile                    # Convenient commands
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Multi-container setup
├── README.md                   # Full documentation
├── API.md                      # API reference
├── DOCKER.md                   # Docker instructions
└── QUICKSTART.md               # This file
```

---

## Configuration

Edit `.env` to customize:

```ini
# Server
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=True

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Scanning
REQUEST_DELAY_SECONDS=1.5    # Delay between requests
MAX_RESULTS_PER_QUERY=10      # Results to extract per query
```

---

## Next Steps

1. ✅ Install and run the tool
2. 📖 Read [README.md](README.md) for detailed documentation
3. 🔌 Check [API.md](API.md) for API integration
4. 🐳 See [DOCKER.md](DOCKER.md) for Docker deployment
5. 🔐 Review security notes (see README - Important Notes section)

---

## Support Resources

- 📚 **Full Documentation**: See [README.md](README.md)
- 🔌 **API Reference**: See [API.md](API.md)
- 🐳 **Docker Guide**: See [DOCKER.md](DOCKER.md)
- ❓ **Help Page**: Visit `/help` in the web interface

---

## Key Points to Remember

✅ **For authorized security testing only!**

- Always get written authorization before scanning
- Respect robots.txt and Terms of Service
- Google may rate limit - adjust delays if needed
- Export results for documentation and reporting

---

## Performance Tips

- **Single scan**: Expected time varies by query count (usually 5-15 min)
- **Increase speed**: Adjust `REQUEST_DELAY_SECONDS` lower (at your own risk)
- **Batch processing**: Use API to scan multiple domains in parallel
- **Production**: Use Docker for reliable deployment

---

Happy scanning! 🚀

For issues or questions, check the [README.md](README.md) troubleshooting section.
