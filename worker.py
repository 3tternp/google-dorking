#!/usr/bin/env python3
"""Celery Worker — imports both dorking and recon tasks."""
import os
from dotenv import load_dotenv
load_dotenv()

from app.tasks import celery_app        # registers app.tasks.*
import app.recon_tasks                  # registers app.tasks.run_subdomain_enum  # noqa: F401

if __name__ == '__main__':
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=4',
        '-E',
    ])
