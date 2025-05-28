#!/usr/bin/env python
"""
Script to start the Celery worker with proper Python path configuration.

This should be run from the project root directory.
"""

import os
import sys

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

if __name__ == "__main__":
    # Now import the Celery app - importing here to avoid E402 error
    from codestory.ingestion_pipeline.celery_app import app

    print(f"Starting Celery worker. PYTHONPATH includes: {src_dir}")

    # Print information about the Celery app
    print("Registered tasks:")
    for task in app.tasks:
        print(f"  - {task}")

    # Set up command-line arguments for Celery
    sys.argv = [
        "celery",
        "-A",
        "codestory.ingestion_pipeline.celery_app:app",
        "worker",
        "-l",
        "debug",  # Increased log level for debugging
        "-Q",
        "ingestion",
        "--concurrency=1",  # Set concurrency to 1 for simpler debugging
        "--loglevel=DEBUG",  # Additional loglevel flag
    ]

    # Output final command for debugging
    print(f"Running Celery with command: {' '.join(sys.argv)}")

    # This is equivalent to running:
    # celery -A codestory.ingestion_pipeline.celery_app:app worker -l debug -Q ingestion \
    #     --concurrency=1 --loglevel=DEBUG
    from celery.__main__ import main

    sys.exit(main())
