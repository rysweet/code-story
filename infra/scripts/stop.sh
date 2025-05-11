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
echo -e "${BLUE}      Stopping Code Story Services    ${RESET}"
echo -e "${BLUE}======================================${RESET}"
echo ""

# Check if docker-compose.yaml exists
if [ ! -f docker-compose.yaml ]; then
    echo -e "${RED}Error: docker-compose.yaml not found. Make sure you're in the project root directory.${RESET}"
    exit 1
fi

# Check if services are running
if [ "$(docker-compose ps -q)" == "" ]; then
    echo -e "${YELLOW}No services are currently running.${RESET}"
    exit 0
fi

# Stop the services
echo -e "${BLUE}Stopping all services...${RESET}"
docker-compose down

echo -e "${GREEN}All services have been stopped.${RESET}"
echo ""
echo -e "${YELLOW}To remove all data volumes, run: docker-compose down -v${RESET}"
echo -e "${YELLOW}To start services again, run: ./infra/scripts/start.sh${RESET}"