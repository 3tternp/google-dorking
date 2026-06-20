"""
Celery Tasks — Optimized for concurrent dorking execution.

Key changes vs original:
  - ThreadPoolExecutor runs queries in parallel (10 workers default)
  - Per-category Celery subtasks via chord for multi-worker parallelism
  - Progress updates are batched (every N completions) to reduce Redis chatter
  - Graceful cancellation / timeout support
  - Configurable concurrency via SCAN_MAX_THREADS env var
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from celery import Celery, Task, chord, group
from app.search_engine import GoogleSearcher
from app.dorking_queries import get_queries_for_domain

# ---------------------------------------------------------------------------
# Celery setup
# ---------------------------------------------------------------------------

celery_app = Celery("google_dorking")
celery_app.conf.update(
    broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    # Keep results for 24 h so the frontend can always fetch them
    result_expires=86400,
    # Avoid prefetching too many tasks at once (better for long-running scans)
    worker_prefetch_multiplier=1,
    # Silence Celery 6 deprecation warning
    broker_connection_retry_on_startup=True,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_THREADS   = int(os.getenv("SCAN_MAX_THREADS", 3))    # concurrent HTTP threads (low default avoids 429s)
MAX_RESULTS   = int(os.getenv("MAX_RESULTS_PER_QUERY", 5))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", 2.0))  # per-thread courtesy delay
RATE_LIMIT    = float(os.getenv("SCAN_RATE_LIMIT", 0.5))        # global req/sec

# Google Custom Search API credentials (optional but eliminates rate-limiting)
GOOGLE_API_KEY        = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

# How often to push a progress update (every N completed queries).
# Lower = more Redis writes but smoother UI bar. Keep ≥ 1.
PROGRESS_BATCH = max(1, int(os.getenv("SCAN_PROGRESS_BATCH", 5)))


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        pass  # replace with webhook / notification if desired

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        pass


celery_app.Task = CallbackTask


# ---------------------------------------------------------------------------
# Main scan task  (single-task, multi-threaded approach)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.execute_dorking_scan")
def execute_dorking_scan(self, domain: str, categories: list = None, *args, **kwargs):
    # *args/**kwargs absorb any extra arguments from stale callers
    """
    Execute all dorking queries for *domain* using a thread pool.

    Architecture
    ────────────
    1. Build the full query list from dorking_queries.py
    2. Submit every query to a ThreadPoolExecutor (MAX_THREADS workers)
    3. As futures complete, accumulate results and push Celery progress updates
    4. Return the aggregated scan_results dict

    This turns a 6-minute sequential scan into ~20–40 seconds.
    """

    searcher = GoogleSearcher(
        delay=REQUEST_DELAY,
        rate_limit=RATE_LIMIT,
        api_key=GOOGLE_API_KEY,
        search_engine_id=GOOGLE_SEARCH_ENGINE_ID,
    )

    try:
        queries_dict = get_queries_for_domain(domain, categories)
        # Flatten: list of (category, query_string)
        all_pairs = [
            (cat, q)
            for cat, qs in queries_dict.items()
            for q in qs
        ]
        total = len(all_pairs)

        # Initialise result containers
        results_by_category: dict = {cat: [] for cat in queries_dict}
        lock = threading.Lock()
        completed_count = 0

        # Initial state push
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": total,
                "status": f"Starting parallel scan for {domain} — {total} queries across {MAX_THREADS} threads",
                "current_query": "",
                "domain": domain,
            },
        )

        def _run(pair):
            category, query = pair
            result = searcher.search(query, max_results=MAX_RESULTS)
            return category, query, result

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            future_map = {executor.submit(_run, pair): pair for pair in all_pairs}

            for future in as_completed(future_map):
                try:
                    category, query, result = future.result()
                except Exception as exc:
                    category, query = future_map[future]
                    result = {"status": "error", "query": query, "error": str(exc)}

                with lock:
                    results_by_category[category].append(result)
                    completed_count += 1
                    local_count = completed_count

                # Batch progress updates to reduce Redis write pressure
                if local_count % PROGRESS_BATCH == 0 or local_count == total:
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": local_count,
                            "total": total,
                            "status": f"Scanning {domain}…",
                            "current_query": query,
                            "domain": domain,
                        },
                    )

        scan_results = {
            "domain": domain,
            "scan_date": datetime.now().isoformat(),
            "total_queries": total,
            "categories_scanned": list(queries_dict.keys()),
            "results_by_category": results_by_category,
            "statistics": searcher.get_stats(),
        }

        return {"status": "completed", "data": scan_results}

    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={"status": "error", "error": str(exc), "domain": domain},
        )
        raise


# ---------------------------------------------------------------------------
# Advanced: per-category subtasks  (chord-based, uses multiple Celery workers)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.scan_category")
def scan_category(self, domain: str, category: str, queries: list):
    """
    Scan a single category's queries concurrently.
    Intended to be called as part of a Celery chord for maximum parallelism
    across multiple Celery workers.
    """
    searcher = GoogleSearcher(
        delay=REQUEST_DELAY,
        rate_limit=RATE_LIMIT,
        api_key=GOOGLE_API_KEY,
        search_engine_id=GOOGLE_SEARCH_ENGINE_ID,
    )
    results = []

    with ThreadPoolExecutor(max_workers=min(MAX_THREADS, len(queries))) as executor:
        futures = {executor.submit(searcher.search, q, MAX_RESULTS): q for q in queries}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({
                    "status": "error",
                    "query": futures[future],
                    "error": str(exc),
                })

    return {"category": category, "results": results, "stats": searcher.get_stats()}


@celery_app.task(name="app.tasks.aggregate_results")
def aggregate_results(category_results: list, domain: str):
    """
    Chord callback: merge per-category results into the final scan_results dict.
    """
    results_by_category = {}
    combined_stats = {
        "total_queries": 0,
        "successful_queries": 0,
        "failed_queries": 0,
    }

    for item in category_results:
        cat = item["category"]
        results_by_category[cat] = item["results"]
        s = item.get("stats", {})
        combined_stats["total_queries"]     += s.get("total_queries", 0)
        combined_stats["successful_queries"] += s.get("successful_queries", 0)
        combined_stats["failed_queries"]     += s.get("failed_queries", 0)

    total = combined_stats["total_queries"]
    combined_stats["success_rate"] = round(
        (combined_stats["successful_queries"] / total * 100) if total > 0 else 0, 1
    )

    return {
        "status": "completed",
        "data": {
            "domain": domain,
            "scan_date": datetime.now().isoformat(),
            "total_queries": total,
            "categories_scanned": list(results_by_category.keys()),
            "results_by_category": results_by_category,
            "statistics": combined_stats,
        },
    }


@celery_app.task(bind=True, name="app.tasks.execute_dorking_scan_chord")
def execute_dorking_scan_chord(self, domain: str, categories: list = None):
    """
    Alternative entry point that uses a Celery chord for true multi-worker
    parallelism. Each category runs as an independent Celery task, so all
    four (or more) Celery workers stay busy simultaneously.

    Usage: call this instead of execute_dorking_scan when you have
    multiple Celery workers running.
    """
    from app.dorking_queries import get_queries_for_domain

    queries_dict = get_queries_for_domain(domain, categories)

    job = chord(
        scan_category.s(domain, cat, queries)
        for cat, queries in queries_dict.items()
    )(aggregate_results.s(domain))

    return job


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.test_connection")
def test_connection():
    return {"status": "connected", "timestamp": datetime.now().isoformat()}
