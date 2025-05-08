#!/bin/bash

# Script to start the entire Code Story project
# This script sets up the necessary components:
# 1. Neo4j database with the correct configuration
# 2. Redis instance if needed
# 3. Celery workers
# 4. Integration test environment

set -e  # Exit on any error

# Function to check if a port is in use
port_in_use() {
  lsof -i:$1 -t >/dev/null
}

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

# Function to wait for a service to be ready
wait_for_service() {
  local service_name=$1
  local check_command=$2
  local max_attempts=$3
  local interval=$4
  
  print_info "Waiting for $service_name to be ready..."
  
  for (( i=1; i<=$max_attempts; i++ )); do
    if eval "$check_command"; then
      print_success "$service_name is ready!"
      return 0
    fi
    
    echo "Attempt $i/$max_attempts - $service_name is not ready yet..."
    sleep $interval
  done
  
  print_error "$service_name failed to become ready after $max_attempts attempts"
  return 1
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

print_header "Starting Code Story Project"

# Check current environment
print_info "Checking current environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  print_error "Docker is not running. Please start Docker and try again."
  exit 1
fi
print_success "Docker is running"

# Check for Python 3.12
if ! python --version | grep -q "Python 3.12"; then
  print_error "Python 3.12 is required. Please install it and try again."
  exit 1
fi
print_success "Python 3.12 is installed"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
  print_error "Poetry is not installed. Please install it and try again."
  exit 1
fi
print_success "Poetry is installed"

# Install dependencies if needed
if [[ ! -d ".venv" ]]; then
  print_info "Installing dependencies with Poetry..."
  poetry install --no-interaction
else
  print_success "Dependencies already installed"
fi

# Set up environment variables
if [[ ! -f ".env" ]]; then
  print_info "Creating .env file from template..."
  cp .env-template .env
  
  # Update Neo4j ports to use non-standard ports
  sed -i.bak 's/NEO4J__URI=bolt:\/\/localhost:7687/NEO4J__URI=bolt:\/\/localhost:7689/' .env
  rm -f .env.bak
  
  print_success "Created .env file with non-standard Neo4j ports"
else
  print_info "Using existing .env file"
  # Check if Neo4j URI uses non-standard ports
  if grep -q "NEO4J__URI=bolt://localhost:7687" .env; then
    print_info "Updating Neo4j port in .env to non-standard port..."
    sed -i.bak 's/NEO4J__URI=bolt:\/\/localhost:7687/NEO4J__URI=bolt:\/\/localhost:7689/' .env
    rm -f .env.bak
  fi
fi

# Start Neo4j for testing
print_header "Starting Neo4j"

print_info "Starting Neo4j container for testing..."
# Use docker-compose.test.yml which already has non-standard ports
docker-compose -f docker-compose.test.yml up -d neo4j

# Wait for Neo4j to be ready
wait_for_service "Neo4j" "docker-compose -f docker-compose.test.yml exec -T neo4j cypher-shell -u neo4j -p password 'RETURN 1;' &> /dev/null" 30 2

# Clear database
print_info "Clearing Neo4j database..."
docker-compose -f docker-compose.test.yml exec -T neo4j cypher-shell -u neo4j -p password "MATCH (n) DETACH DELETE n;" || true

# Start Redis if not already running
print_header "Setting up Redis"

if port_in_use 6379; then
  print_success "Redis is already running on port 6379"
else
  print_info "Starting Redis container..."
  docker run -d --name codestory-redis -p 6379:6379 redis:7-alpine
  wait_for_service "Redis" "redis-cli ping | grep -q PONG" 10 1
fi

# Start Celery worker
print_header "Starting Celery Worker"

# Check if there's a Celery worker already running
if pgrep -f "celery" > /dev/null; then
  print_info "Celery worker is already running"
else
  print_info "Starting Celery worker..."
  
  # Using a new terminal window/tab to run the worker, different approaches for different OSes
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS approach
    osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'\" && source .venv/bin/activate && celery -A src.codestory.ingestion_pipeline.celery_app:app worker -l info -Q ingestion"'
  else
    # Linux approach (run in background)
    poetry run celery -A src.codestory.ingestion_pipeline.celery_app:app worker -l info -Q ingestion &
  fi
  
  # Wait a bit for the worker to start
  sleep 3
  print_success "Celery worker started"
fi

print_header "Environment Ready"
print_success "Code Story environment is ready for development and testing!"
print_info "Neo4j is running at: bolt://localhost:7688 (Test DB)"
print_info "Redis is running at: localhost:6379"
print_info "Celery worker is running for task processing"
print_info ""
print_info "You can now run integration tests with:"
print_info "  poetry run pytest tests/integration --run-neo4j --run-celery"
print_info ""
print_info "To stop the environment, run:"
print_info "  docker-compose -f docker-compose.test.yml down"
print_info "  docker stop codestory-redis"
print_info "  pkill -f 'celery'"