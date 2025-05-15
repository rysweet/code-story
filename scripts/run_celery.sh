#!/bin/bash
export PYTHONPATH="/src:$PYTHONPATH"
cd 
poetry run python scripts/celery_worker.py
