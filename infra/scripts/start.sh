#!/bin/bash
set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Welcome message
echo -e "${BLUE}======================================${RESET}"
echo -e "${BLUE}   Code Story Development Environment ${RESET}"
echo -e "${BLUE}======================================${RESET}"
echo ""

# Check if .env file exists, create it if not
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating default .env file...${RESET}"
    cat > .env << EOF
# Neo4j Configuration
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis Configuration
REDIS_URI=redis://redis:6379

# Service Configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
LOG_LEVEL=INFO

# MCP Configuration
AUTH_ENABLED=false
MCP_HOST=0.0.0.0
MCP_PORT=8001
MCP_WORKERS=2
MCP_DEBUG=true

# Optional Azure Authentication
#AZURE_TENANT_ID=
#AZURE_CLIENT_ID=
#AZURE_CLIENT_SECRET=
EOF
    echo -e "${GREEN}Created default .env file. Edit this file to configure your environment.${RESET}"
    echo ""
fi

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${RESET}"
    exit 1
fi

# Create necessary directories
mkdir -p logs

# Pull latest images and build
echo -e "${BLUE}Pulling latest images and building services...${RESET}"
docker-compose pull
docker-compose build

# Start the services
echo -e "${BLUE}Starting services...${RESET}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to be ready...${RESET}"
MAX_RETRIES=30
RETRY_INTERVAL=5
SERVICES=("neo4j" "redis" "service" "mcp")

for service in "${SERVICES[@]}"; do
    retries=0
    echo -n "Waiting for ${service} "
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if docker-compose exec -T $service bash -c "exit 0" > /dev/null 2>&1; then
            health_status=$(docker inspect --format='{{.State.Health.Status}}' "$(docker-compose ps -q $service)" 2>/dev/null)
            
            if [ "$health_status" = "healthy" ]; then
                echo -e "${GREEN}✓${RESET}"
                break
            fi
        fi
        
        echo -n "."
        sleep $RETRY_INTERVAL
        retries=$((retries+1))
        
        if [ $retries -eq $MAX_RETRIES ]; then
            echo ""
            echo -e "${RED}Service ${service} is not becoming healthy. Check logs with: docker-compose logs ${service}${RESET}"
            exit 1
        fi
    done
done

echo -e "${GREEN}All services are up and running!${RESET}"
echo ""
echo -e "${BLUE}Service endpoints:${RESET}"
echo -e "  Neo4j Browser:  ${GREEN}http://localhost:7474${RESET}"
echo -e "  Service API:    ${GREEN}http://localhost:8000${RESET}"
echo -e "  MCP API:        ${GREEN}http://localhost:8001${RESET}"
echo -e "  GUI:            ${GREEN}http://localhost:5173${RESET}"
echo ""
echo -e "${YELLOW}To stop the services, run: ./infra/scripts/stop.sh${RESET}"
echo -e "${YELLOW}To check service health, run: ./infra/scripts/healthcheck.sh${RESET}"
echo -e "${YELLOW}To view logs, run: docker-compose logs -f [service_name]${RESET}"