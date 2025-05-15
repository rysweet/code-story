#!/bin/bash
# Run the filesystem integration tests with the appropriate options

# Ensure we're in the project root directory
cd "$(dirname "$0")/.." || exit 1

# Set up the Python path to include the src directory
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Run the direct filesystem tests (no Celery dependency)
echo "Running direct filesystem tests..."
python -m pytest tests/integration/test_ingestion_pipeline/test_filesystem_direct.py \
  --run-neo4j \
  -v

# Uncomment this when ready to run the Celery-based tests
# echo "Running Celery-based filesystem tests..."
# python -m pytest tests/integration/test_ingestion_pipeline/test_filesystem_integration.py \
#  --run-neo4j \
#  --run-celery \
#  -v