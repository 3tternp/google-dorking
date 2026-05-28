#!/usr/bin/env python3
"""
Celery Worker Entry Point
Run this in a separate terminal to process background tasks
"""

from app.tasks import celery_app
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=4',  # Number of worker processes
        '-E'  # Enable events for monitoring
    ])
