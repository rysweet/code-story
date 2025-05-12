#!/bin/bash

# Script to run integration tests for the Code Story project
# This script ensures the environment is set up and running properly before executing tests

set -e  # Exit on any error

# Function to print colored messages
print_header() {
  echo -e "\n\033[1;34m==== $1 ====\033[0m"
}

print_success() {
  echo -e "\033[1;32m✅ $1\033[0m"
}

print_info() {
  echo -e "\033[1;36m$1\033[0m"
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

print_header "Running Integration Tests"

# First check if the environment is set up
print_info "Checking if the environment is set up..."

# Check if Neo4j is running
if ! docker ps | grep -q "codestory-neo4j-test"; then
  print_info "Neo4j container not found. Setting up environment first..."
  ./scripts/start_project.sh
else
  print_success "Neo4j container is running"
fi

# Check if Celery worker is running
CELERY_PID_FILE="$(pwd)/.celery.pid"
if [[ -f "$CELERY_PID_FILE" ]] && kill -0 $(cat "$CELERY_PID_FILE") 2>/dev/null; then
  print_success "Celery worker is running"
else
  if pgrep -f "celery.*codestory.ingestion_pipeline" > /dev/null; then
    print_success "Celery worker is running (without PID file)"
  else
    print_info "Celery worker not found. Restarting Celery..."
    # Create a log directory if it doesn't exist
    mkdir -p logs
    
    # Start Celery in the background with correct import path
    export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
    poetry run celery -A codestory.ingestion_pipeline.celery_app:app worker -l info -Q ingestion --detach \
      --logfile="$(pwd)/logs/celery.log" \
      --pidfile="$CELERY_PID_FILE"
      
    print_info "Started Celery worker with PYTHONPATH including $(pwd)/src"
    
    # Wait a bit for the worker to start
    sleep 3
    if [[ -f "$CELERY_PID_FILE" ]] && kill -0 $(cat "$CELERY_PID_FILE") 2>/dev/null; then
      print_success "Celery worker started successfully"
    else
      print_error "Failed to start Celery worker. Check logs/celery.log for details"
      exit 1
    fi
  fi
fi

# Parse the test arguments
SPECIFIC_TEST="${1:-tests/integration/test_ingestion_pipeline}"

print_header "Running Tests: $SPECIFIC_TEST"
print_info "Using the following command:"
print_info "PYTHONPATH=$(pwd)/src poetry run pytest $SPECIFIC_TEST -v --run-neo4j --run-celery --override-ini='addopts='"
print_info ""

# Run the tests with poetry and the correct Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
export REDIS__URI="redis://localhost:6380/0"
export NEO4J__URI="bolt://localhost:7688"
export NEO4J__USERNAME="neo4j"
export NEO4J__PASSWORD="password"
export NEO4J__DATABASE="codestory-test"

poetry run pytest $SPECIFIC_TEST -v --run-neo4j --run-celery --override-ini="addopts="

# Check test result
if [ $? -eq 0 ]; then
  print_header "Test Results"
  print_success "All tests passed successfully!"
else
  print_header "Test Results"
  print_error "Some tests failed. Please check the output above for details."
  
  # Provide some diagnostic hints
  print_info ""
  print_info "For troubleshooting:"
  print_info "1. Check Neo4j logs: docker logs codestory-neo4j-test"
  print_info "2. Check Celery logs: cat logs/celery.log"
  print_info "3. Restart the environment: ./scripts/stop_project.sh && ./scripts/start_project.sh"
  print_info ""
fi

print_info "To stop the environment when done:"
print_info "  ./scripts/stop_project.sh"