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
print_info "Ensuring dependencies are installed with Poetry..."
poetry install --no-interaction

# Force sync dependencies in case pyproject.toml has been updated
VENV_PATH=$(poetry env info -p 2>/dev/null)
if [[ -n "$VENV_PATH" ]]; then
  print_success "Poetry environment found at: $VENV_PATH"
else
  print_error "Poetry environment not found. This is unexpected."
  exit 1
fi

# Set up environment variables
if [[ ! -f ".env" ]]; then
  print_info "Creating .env file from template..."
  cp .env-template .env
  
  # Update Neo4j ports to use non-standard ports
  sed -i.bak 's/NEO4J__URI=bolt:\/\/localhost:7687/NEO4J__URI=bolt:\/\/localhost:7688/' .env
  rm -f .env.bak
  
  print_success "Created .env file with non-standard Neo4j ports"
else
  print_info "Using existing .env file"
  # Check if Neo4j URI uses standard ports
  if grep -q "NEO4J__URI=bolt://localhost:7687" .env; then
    print_info "Updating Neo4j port in .env to non-standard port..."
    sed -i.bak 's/NEO4J__URI=bolt:\/\/localhost:7687/NEO4J__URI=bolt:\/\/localhost:7688/' .env
    rm -f .env.bak
  # Check if Neo4j URI uses wrong non-standard port
  elif grep -q "NEO4J__URI=bolt://localhost:7689" .env; then
    print_info "Updating Neo4j port in .env to correct non-standard port..."
    sed -i.bak 's/NEO4J__URI=bolt:\/\/localhost:7689/NEO4J__URI=bolt:\/\/localhost:7688/' .env
    rm -f .env.bak
  fi
fi

# Start Neo4j for testing
print_header "Starting Neo4j"

# Make sure no container with that name is running or stopped first
./scripts/stop_project.sh > /dev/null 2>&1

print_info "Starting Neo4j container for testing..."
# Use docker-compose.test.yml which already has non-standard ports
docker-compose -f docker-compose.test.yml up -d neo4j

# Wait for Neo4j to be ready
print_info "Waiting for Neo4j to be ready... (this may take up to 60 seconds)"
wait_for_service "Neo4j" "docker exec codestory-neo4j-test cypher-shell -u neo4j -p password 'RETURN 1;' &> /dev/null" 60 3

# Check if Neo4j is running after waiting
if ! docker ps | grep -q "codestory-neo4j-test"; then
  print_error "Neo4j container failed to start properly. Checking logs..."
  docker logs codestory-neo4j-test
  
  print_error "Trying to restart container..."
  docker-compose -f docker-compose.test.yml restart neo4j
  
  print_info "Waiting for Neo4j to be ready after restart..."
  wait_for_service "Neo4j" "docker exec codestory-neo4j-test cypher-shell -u neo4j -p password 'RETURN 1;' &> /dev/null" 60 3
fi

# Check one more time if it's working
if docker ps | grep -q "codestory-neo4j-test" && \
   docker exec codestory-neo4j-test cypher-shell -u neo4j -p password 'RETURN 1;' &> /dev/null; then
  print_success "Neo4j container is running and responsive"
  
  # Clear database
  print_info "Clearing Neo4j database..."
  docker exec codestory-neo4j-test cypher-shell -u neo4j -p password "MATCH (n) DETACH DELETE n;" || true
  print_success "Neo4j database cleared"
else
  print_error "Neo4j container failed to start or respond. Please check docker logs."
  exit 1
fi

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
CELERY_PID_FILE="$(pwd)/.celery.pid"

if pgrep -f "celery.*codestory.ingestion_pipeline" > /dev/null; then
  print_info "Celery worker is already running"
else
  print_info "Starting Celery worker..."
  
  # Create a log directory if it doesn't exist
  mkdir -p logs
  
  # Start Celery in the background with correct import path
  # Create log directory if it doesn't exist
  mkdir -p logs
  
  # Use our custom celery worker script with proper Python path
  export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
  
  # Create a simple script to run Celery with the right environment
  cat > ./scripts/run_celery.sh << EOL
#!/bin/bash
export PYTHONPATH="${pwd}/src:\$PYTHONPATH"
cd ${pwd}
poetry run python scripts/celery_worker.py
EOL
  chmod +x ./scripts/run_celery.sh
  
  # Run celery in background with nohup
  nohup ./scripts/run_celery.sh > ./logs/celery.log 2>&1 &
  CELERY_PID=$!
  echo $CELERY_PID > "$CELERY_PID_FILE"
  
  # Log for debugging
  print_info "Started Celery worker with PYTHONPATH including $(pwd)/src (PID: $CELERY_PID)"
  
  # Wait a bit and check if it started properly
  sleep 3
  if [[ -f "$CELERY_PID_FILE" ]] && kill -0 $(cat "$CELERY_PID_FILE") 2>/dev/null; then
    print_success "Celery worker started successfully (PID: $(cat "$CELERY_PID_FILE"))"
  else
    print_error "Celery worker failed to start properly. Check logs/celery.log for details"
    print_info "You can try starting it manually with:"
    print_info "poetry run celery -A codestory.ingestion_pipeline.celery_app:app worker -l info -Q ingestion"
  fi
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