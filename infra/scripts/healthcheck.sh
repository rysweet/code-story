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
echo -e "${BLUE}    Code Story Service Health Check   ${RESET}"
echo -e "${BLUE}======================================${RESET}"
echo ""

# Check if docker-compose.yaml exists
if [ ! -f docker-compose.yaml ]; then
    echo -e "${RED}Error: docker-compose.yaml not found. Make sure you're in the project root directory.${RESET}"
    exit 1
fi

# Check if services are running
if [ "$(docker-compose ps -q)" == "" ]; then
    echo -e "${RED}No services are currently running. Start them with: ./infra/scripts/start.sh${RESET}"
    exit 1
fi

# Define services and their health check endpoints
declare -A SERVICES=(
    ["neo4j"]="http://localhost:7474"
    ["service"]="http://localhost:8000/health"
    ["mcp"]="http://localhost:8001/health"
)

# Check Redis separately as it needs a different method
echo -e "${BLUE}Checking Redis...${RESET}"
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo -e "  Redis: ${GREEN}HEALTHY${RESET}"
else
    echo -e "  Redis: ${RED}UNHEALTHY${RESET}"
fi

# Check services using HTTP endpoints
for service in "${!SERVICES[@]}"; do
    endpoint=${SERVICES[$service]}
    echo -e "${BLUE}Checking ${service}...${RESET}"
    
    # Get container status
    container_status=$(docker-compose ps -q $service)
    if [ -z "$container_status" ]; then
        echo -e "  ${service}: ${RED}NOT RUNNING${RESET}"
        continue
    fi
    
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$(docker-compose ps -q $service)" 2>/dev/null)
    if [ -z "$health_status" ]; then
        health_status="N/A"
    fi
    
    # Try connecting to the endpoint
    if curl -s --max-time 5 -o /dev/null -w "%{http_code}" $endpoint | grep -q "200\|401"; then
        echo -e "  ${service}: ${GREEN}HEALTHY${RESET} (Container Health: ${health_status})"
        
        # Get additional info where available
        if [ "$service" == "service" ]; then
            version=$(curl -s $endpoint | grep -o '"version":"[^"]*"' | cut -d':' -f2 | tr -d '"')
            if [ ! -z "$version" ]; then
                echo -e "    Version: ${version}"
            fi
        fi
    else
        echo -e "  ${service}: ${RED}UNHEALTHY${RESET} (Container Health: ${health_status})"
        echo -e "    Endpoint ${endpoint} not responding properly"
    fi
done

# Check GUI service
echo -e "${BLUE}Checking GUI...${RESET}"
if docker-compose ps -q gui > /dev/null 2>&1; then
    echo -e "  GUI: ${GREEN}RUNNING${RESET}"
    echo -e "    Access at: http://localhost:5173"
else
    echo -e "  GUI: ${RED}NOT RUNNING${RESET}"
fi

# Check worker service
echo -e "${BLUE}Checking worker...${RESET}"
if docker-compose ps -q worker > /dev/null 2>&1; then
    # Get last log entry to see if worker is properly connected
    echo -e "  Worker: ${GREEN}RUNNING${RESET}"
    echo -e "    Last log entry:"
    docker-compose logs --tail=1 worker | sed 's/^worker.*//g'
else
    echo -e "  Worker: ${RED}NOT RUNNING${RESET}"
fi

echo ""
echo -e "${BLUE}System Resources:${RESET}"
echo -e "  Container CPU & Memory Usage:"
docker stats --no-stream --format "  {{.Name}}: {{.CPUPerc}} CPU, {{.MemUsage}} Memory"

echo ""
echo -e "${YELLOW}For detailed logs, run: docker-compose logs -f [service_name]${RESET}"