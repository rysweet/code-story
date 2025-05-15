#!/bin/bash

# Script to start a Celery worker for testing

# Function to print colored messages
print_info() {
  echo -e "\033[1;36m$1\033[0m"
}

print_success() {
  echo -e "\033[1;32m✅ $1\033[0m"
}

print_error() {
  echo -e "\033[1;31m❌ $1\033[0m"
}

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
  if [[ -f "../pyproject.toml" ]]; then
    cd ..
  else
    print_error "Please run this script from the project root or scripts directory"
    exit 1
  fi
fi

# Create a log directory if it doesn't exist
mkdir -p logs

print_info "Starting Celery worker for testing with Redis on port 6380..."

# Set environment variables for testing
export REDIS_URI="redis://localhost:6380/0"
export NEO4J__URI="bolt://localhost:7688"
export NEO4J__USERNAME="neo4j"
export NEO4J__PASSWORD="password"
export NEO4J__DATABASE="codestory-test"

# Start the Celery worker
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
poetry run celery -A codestory.ingestion_pipeline.celery_app:app worker -l info -Q ingestion --detach \
  --logfile="$(pwd)/logs/celery_test.log" \
  --pidfile="$(pwd)/.celery_test.pid"

# Check if the worker is running
if [[ -f "$(pwd)/.celery_test.pid" ]] && kill -0 $(cat "$(pwd)/.celery_test.pid") 2>/dev/null; then
  print_success "Celery worker started successfully with PID: $(cat "$(pwd)/.celery_test.pid")"
  print_info "Log file: $(pwd)/logs/celery_test.log"
else
  print_error "Failed to start Celery worker"
  print_info "Check $(pwd)/logs/celery_test.log for details"
  exit 1
fi