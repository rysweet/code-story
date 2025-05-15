#!/bin/bash

# Comprehensive Integration Test Runner for Code Story
# This script ensures a consistent, isolated test environment with proper setup and teardown

set -e  # Exit on any error

# ANSI color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored headers
print_header() {
  echo -e "\n${BLUE}========== $1 ==========${NC}"
}

# Function to print success messages
print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

# Function to print warnings
print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print errors
print_error() {
  echo -e "${RED}❌ $1${NC}"
}

# Function to print info messages
print_info() {
  echo -e "${CYAN}ℹ️  $1${NC}"
}

# Function to print step messages
print_step() {
  echo -e "${PURPLE}▶ $1${NC}"
}

# Function to check if Docker is running
check_docker() {
  print_step "Checking if Docker is running..."
  if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
  fi
  print_success "Docker is running"
}

# Function to ensure we're in the project root
ensure_project_root() {
  if [[ ! -f "pyproject.toml" ]]; then
    if [[ -f "../pyproject.toml" ]]; then
      cd ..
      print_warning "Changed directory to project root: $(pwd)"
    else
      print_error "Please run this script from the project root or scripts directory"
      exit 1
    fi
  fi
  print_success "Running from project root: $(pwd)"
}

# Function to check if a container exists and is running
container_running() {
  local container_name=$1
  docker ps --filter "name=$container_name" --format '{{.Names}}' | grep -q "$container_name"
  return $?
}

# Function to create the fixtures directory structure if needed
ensure_fixtures_directory() {
  print_step "Ensuring fixtures directory structure exists..."
  mkdir -p tests/fixtures/cypher
  
  # Check if our fixture files exist
  if [[ ! -f "tests/fixtures/cypher/01_init_schema.cypher" ]]; then
    print_warning "Schema initialization script not found, creating it..."
    # Create a basic schema initialization script
    cat > tests/fixtures/cypher/01_init_schema.cypher << 'EOF'
// Schema Initialization
MATCH (n) DETACH DELETE n;
CREATE CONSTRAINT unique_file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE;
CREATE CONSTRAINT unique_directory_path IF NOT EXISTS FOR (d:Directory) REQUIRE d.path IS UNIQUE;
CREATE CONSTRAINT unique_function_id IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT unique_class_id IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE;
CREATE INDEX file_name IF NOT EXISTS FOR (f:File) ON (f.name);
EOF
  fi
  
  print_success "Fixtures directory structure ready"
}

# Function to start the test environment
start_test_environment() {
  print_header "Starting Test Environment"

  # Check if containers are already running
  if container_running "codestory-neo4j-test" && container_running "codestory-redis-test"; then
    print_warning "Test containers are already running"
    
    if [[ "$1" == "--force-restart" ]]; then
      print_step "Force restarting containers as requested..."
      docker-compose -f docker-compose.test.yml down
    else
      print_info "Using existing containers. Use --force-restart to recreate containers."
    fi
  fi
  
  # Start containers defined in docker-compose.test.yml
  print_step "Starting containers with health checks..."
  docker-compose -f docker-compose.test.yml up -d
  
  # Wait for containers to be healthy
  print_step "Waiting for Neo4j to be healthy..."
  local retries=0
  local max_retries=30
  
  while ! docker-compose -f docker-compose.test.yml ps neo4j | grep -q "healthy"; do
    if [[ $retries -eq $max_retries ]]; then
      print_error "Neo4j did not become healthy within the timeout period"
      docker-compose -f docker-compose.test.yml logs neo4j
      exit 1
    fi
    
    retries=$((retries+1))
    echo -ne "${YELLOW}Waiting for Neo4j to be healthy... ($retries/$max_retries)${NC}\r"
    sleep 2
  done
  echo ""
  print_success "Neo4j is healthy"
  
  print_step "Waiting for Redis to be healthy..."
  retries=0
  max_retries=15
  
  while ! docker-compose -f docker-compose.test.yml ps redis | grep -q "healthy"; do
    if [[ $retries -eq $max_retries ]]; then
      print_error "Redis did not become healthy within the timeout period"
      docker-compose -f docker-compose.test.yml logs redis
      exit 1
    fi
    
    retries=$((retries+1))
    echo -ne "${YELLOW}Waiting for Redis to be healthy... ($retries/$max_retries)${NC}\r"
    sleep 2
  done
  echo ""
  print_success "Redis is healthy"
  
  # Initialize Neo4j database
  print_step "Initializing Neo4j database..."

  # Always clear the database first to ensure a clean state
  print_step "Clearing database..."
  docker exec -i codestory-neo4j-test cypher-shell -u neo4j -p password --database=testdb \
    "MATCH (n) DETACH DELETE n;"

  print_success "Database cleared"

  # Check if the schema initialization file exists
  if [[ -f "tests/fixtures/cypher/01_init_schema.cypher" ]]; then
    print_step "Running schema initialization..."
    # Load schema initialization file
    docker exec -i codestory-neo4j-test cypher-shell -u neo4j -p password --database=testdb < tests/fixtures/cypher/01_init_schema.cypher

    if [[ $? -eq 0 ]]; then
      print_success "Schema initialized successfully"

      # Load any test data fixtures in numerical order
      for fixture in tests/fixtures/cypher/0[2-9]_*.cypher; do
        if [[ -f "$fixture" ]]; then
          print_step "Loading test data from $fixture..."
          docker exec -i codestory-neo4j-test cypher-shell -u neo4j -p password --database=testdb < "$fixture"

          if [[ $? -eq 0 ]]; then
            print_success "Test data from $fixture loaded successfully"
          else
            print_warning "Failed to load test data from $fixture"
          fi
        fi
      done
    else
      print_warning "Schema initialization failed"
      print_info "Tests will run with basic schema only"
    fi
  else
    print_warning "Schema initialization file not found, skipping schema setup"
    print_info "Tests will run with an empty database"
  fi
  
  # No Celery worker container in this simplified setup
  print_warning "Using simplified Docker setup without Celery container"
  print_info "Tests that need Celery will use a local worker"
  
  print_success "Test environment is ready"
}

# Function to set up environment variables for tests
setup_environment_variables() {
  print_header "Setting Up Environment Variables"
  
  # Set Neo4j environment variables
  export NEO4J_URI="bolt://localhost:7688"
  export NEO4J_USERNAME="neo4j"
  export NEO4J_PASSWORD="password"
  export NEO4J_DATABASE="testdb"

  # Set Neo4j settings for codestory app (double underscore format)
  export NEO4J__URI="bolt://localhost:7688"
  export NEO4J__USERNAME="neo4j"
  export NEO4J__PASSWORD="password"
  export NEO4J__DATABASE="testdb"
  
  # Set Redis environment variables
  export REDIS_URI="redis://localhost:6380/0"
  export REDIS__URI="redis://localhost:6380/0"
  
  # Set OpenAI mock credentials for tests
  export OPENAI_API_KEY="sk-test-key-openai"
  export OPENAI__API_KEY="sk-test-key-openai"
  export OPENAI__EMBEDDING_MODEL="text-embedding-3-small"
  export OPENAI__CHAT_MODEL="gpt-4o"
  export OPENAI__REASONING_MODEL="gpt-4o"
  
  # Set Python path to include src directory
  export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
  
  print_success "Environment variables set"
  
  # Print the most important variables for debugging
  print_info "NEO4J_URI = $NEO4J_URI"
  print_info "REDIS_URI = $REDIS_URI"
  print_info "PYTHONPATH = $PYTHONPATH"
}

# Function to ensure a local Celery worker is running if needed
ensure_celery_worker() {
  print_header "Ensuring Celery Worker"
  
  print_step "Starting local Celery worker for tests..."
  
  # Check if Celery is already running
  CELERY_PID_FILE="$(pwd)/.celery_test.pid"
  if [[ -f "$CELERY_PID_FILE" ]] && kill -0 $(cat "$CELERY_PID_FILE") 2>/dev/null; then
    print_success "Local Celery worker is already running"
  else
    # Check if celery is running without a PID file
    if pgrep -f "celery.*codestory.ingestion_pipeline.*test" > /dev/null; then
      print_warning "Celery worker is running without PID file"
    else
      print_step "Starting new Celery worker..."
      
      # Create a log directory if it doesn't exist
      mkdir -p logs
      
      # Start Celery in the background with correct import path
      poetry run celery -A codestory.ingestion_pipeline.celery_app:app worker \
        -l info -Q ingestion --detach \
        --logfile="$(pwd)/logs/celery_test.log" \
        --pidfile="$CELERY_PID_FILE"
      
      # Wait a bit for the worker to start
      sleep 3
      if [[ -f "$CELERY_PID_FILE" ]] && kill -0 $(cat "$CELERY_PID_FILE") 2>/dev/null; then
        print_success "Local Celery worker started successfully"
      else
        print_warning "Failed to start local Celery worker. Check logs/celery_test.log for details"
        print_warning "Will attempt to run tests, but Celery-dependent tests may fail"
      fi
    fi
  fi
}

# Function to run the tests
run_tests() {
  print_header "Running Integration Tests"
  
  # Parse command line arguments
  TEST_PATH=${1:-"tests/integration"}
  PYTEST_ARGS=${@:2}
  
  print_step "Running tests: $TEST_PATH"
  print_info "Using command: poetry run pytest $TEST_PATH -v --override-ini=\"addopts=\" $PYTEST_ARGS"
  
  # Run the tests
  poetry run pytest "$TEST_PATH" -v --override-ini="addopts=" $PYTEST_ARGS
  
  # Store the exit code for later use
  TEST_EXIT_CODE=$?
  
  # Check test result
  if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_header "Test Results"
    print_success "All tests passed successfully!"
  else
    print_header "Test Results"
    print_error "Some tests failed. Exit code: $TEST_EXIT_CODE"
    
    # Provide some diagnostic hints
    print_info ""
    print_info "For troubleshooting:"
    print_info "1. Check Neo4j logs: docker logs codestory-neo4j-test"
    print_info "2. Check Redis logs: docker logs codestory-redis-test"
    print_info "3. Check Celery logs: cat logs/celery_test.log"
    print_info "4. Try restarting the environment: $0 --force-restart"
    print_info ""
  fi
  
  return $TEST_EXIT_CODE
}

# Function to cleanup after tests if requested
cleanup_environment() {
  if [[ "$1" == "--cleanup" || "$1" == "-c" ]]; then
    print_header "Cleaning Up Test Environment"
    
    # Stop the local Celery worker if it's running
    CELERY_PID_FILE="$(pwd)/.celery_test.pid"
    if [[ -f "$CELERY_PID_FILE" ]] && kill -0 $(cat "$CELERY_PID_FILE") 2>/dev/null; then
      print_step "Stopping local Celery worker..."
      kill -TERM $(cat "$CELERY_PID_FILE")
      rm -f "$CELERY_PID_FILE"
      print_success "Local Celery worker stopped"
    fi
    
    # Stop the Docker containers
    print_step "Stopping Docker containers..."
    docker-compose -f docker-compose.test.yml down
    print_success "Test environment cleaned up"
  else
    print_info "Test environment is still running"
    print_info "To stop it, run: $0 --cleanup"
  fi
}

# Function to display usage information
show_usage() {
  echo "Usage: $0 [options] [test_path] [pytest_args]"
  echo ""
  echo "Options:"
  echo "  --force-restart    Force restart of test containers even if they're running"
  echo "  --cleanup, -c      Clean up test environment after tests"
  echo "  --help, -h         Show this help message"
  echo ""
  echo "Example: $0 tests/integration/test_graphdb --force-restart -c"
  echo "Example: $0 tests/integration/test_ingestion_pipeline -k test_filesystem"
  echo ""
}

# Main function
main() {
  # Check for help flag
  if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_usage
    exit 0
  fi
  
  # Parse arguments
  FORCE_RESTART=""
  CLEANUP=""
  TEST_PATH=""
  PYTEST_ARGS=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force-restart)
        FORCE_RESTART="--force-restart"
        shift
        ;;
      --cleanup|-c)
        CLEANUP="--cleanup"
        shift
        ;;
      -*)
        # This is a pytest argument
        PYTEST_ARGS="$PYTEST_ARGS $1"
        shift
        ;;
      *)
        if [[ -z "$TEST_PATH" ]]; then
          TEST_PATH="$1"
        else
          PYTEST_ARGS="$PYTEST_ARGS $1"
        fi
        shift
        ;;
    esac
  done
  
  # Set default test path if not specified
  if [[ -z "$TEST_PATH" ]]; then
    TEST_PATH="tests/integration"
  fi
  
  # Run the workflow
  check_docker
  ensure_project_root
  ensure_fixtures_directory
  start_test_environment $FORCE_RESTART
  setup_environment_variables
  ensure_celery_worker
  run_tests "$TEST_PATH" $PYTEST_ARGS
  EXIT_CODE=$?
  cleanup_environment $CLEANUP
  
  exit $EXIT_CODE
}

# Run the main function
main "$@"