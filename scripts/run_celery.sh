#!/bin/bash
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
cd $(pwd)
poetry run python scripts/celery_worker.py
