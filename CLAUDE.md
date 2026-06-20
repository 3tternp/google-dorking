# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start Flask server (Terminal 1)
python run.py

# Start Celery worker (Terminal 2) — required for background scan tasks
python worker.py

# Run tests
python -m pytest tests.py -v

# Run a single test
python -m pytest tests.py::TestFlaskApp::test_api_health -v

# Lint
flake8 app/ --max-line-length=120

# Format
black app/ run.py worker.py

# Docker (alternative to manual setup)
make docker-up    # starts Flask + Celery + Redis via docker-compose
make docker-down
```

Redis must be running before either `run.py` or `worker.py` starts:
```bash
redis-cli ping   # should return PONG
```

## Architecture

The application has two independently launchable scan pipelines, both powered by Celery + Redis:

### 1. Google Dorking Pipeline
- **Trigger**: `POST /api/start-scan` → `app/routes.py`
- **Task**: `execute_dorking_scan` in `app/tasks.py` — uses a `ThreadPoolExecutor` (default 10 threads) to run all dork queries in parallel, reducing a ~6-minute sequential scan to ~20–40 seconds
- **Queries**: `app/dorking_queries.py` — 200+ pre-built dork templates keyed by category; `{domain}` is substituted at scan time
- **Search**: `app/search_engine.py` — `GoogleSearcher` class; uses `googlesearch-python` as primary, falls back to `requests` + `BeautifulSoup`; thread-safe with a token-bucket `RateLimiter`
- **Results view**: `GET /results/<task_id>` → `results.html`

There is also a chord-based variant (`execute_dorking_scan_chord`) in `app/tasks.py` for multi-worker setups where each category runs as its own Celery subtask.

### 2. Passive Recon Pipeline
- **Trigger**: `POST /api/start-recon` → `app/routes.py`
- **Task**: `run_subdomain_enum` in `app/recon_tasks.py`
- **Engine**: `app/recon_engine.py` — queries crt.sh, HackerTarget, AlienVault OTX, ThreatCrowd, then optionally DNS brute-forces against `COMMON_SUBDOMAINS`; no Google or API keys needed
- **Results view**: `GET /recon/<task_id>` → `recon.html`

### App factory & wiring
- `app/__init__.py` — Flask app factory (`create_app`); registers `main_bp` (web routes) and `api_bp` (prefixed `/api`)
- `worker.py` — Celery worker entry point; must import both `app.tasks` and `app.recon_tasks` to register all task names
- `config.py` — `Config`/`DevelopmentConfig`/`ProductionConfig`/`TestingConfig`; selected via `FLASK_ENV`

### Scan status polling
The frontend polls `GET /api/scan-status/<task_id>` (dorking) or `GET /api/recon-status/<task_id>` (recon). Task state transitions: `PENDING → PROGRESS → SUCCESS | FAILURE`. Celery result TTL is 24 hours.

## Key env vars

| Variable | Default | Purpose |
|---|---|---|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Task result store |
| `SCAN_MAX_THREADS` | `10` | Thread pool size per scan |
| `MAX_RESULTS_PER_QUERY` | `5` | Results per dork query |
| `REQUEST_DELAY_SECONDS` | `0.3` | Per-thread courtesy delay |
| `SCAN_RATE_LIMIT` | `3.0` | Global req/sec cap |
| `SCAN_PROGRESS_BATCH` | `5` | Progress update frequency |
| `GOOGLE_API_KEY` | — | Optional Google Custom Search API key |

## Adding dorking queries

Edit `app/dorking_queries.py`. Use `{domain}` as the placeholder — it is substituted at scan time by `get_queries_for_domain()`:

```python
DORKING_QUERIES = {
    "my_category": [
        'site:{domain} inurl:admin',
    ],
}
```
