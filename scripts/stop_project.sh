#!/bin/bash

# Script to stop all Code Story project components
# This script stops:
# 1. Neo4j database
# 2. Redis instance
# 3. Celery workers

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

print_header "Stopping Code Story Project"

# Stop Celery workers
print_info "Stopping Celery workers..."
if pgrep -f "celery" > /dev/null; then
  pkill -f "celery"
  print_success "Celery workers stopped"
else
  print_info "No Celery workers found running"
fi

# Stop Neo4j containers
print_info "Stopping Neo4j containers..."
if docker ps | grep -q "codestory-neo4j"; then
  docker-compose -f docker-compose.test.yml down
  print_success "Neo4j containers stopped"
else
  print_info "No Neo4j containers found running"
fi

# Stop Redis
print_info "Stopping Redis container..."
if docker ps | grep -q "codestory-redis"; then
  docker stop codestory-redis
  docker rm codestory-redis 2>/dev/null || true
  print_success "Redis container stopped and removed"
elif docker ps | grep -q "redis"; then
  print_info "Redis container exists but wasn't started by this script"
  print_info "Skipping Redis shutdown to avoid affecting other services"
else
  print_info "No Redis container found running"
fi

print_header "Environment Shutdown Complete"
print_success "All Code Story components have been stopped"