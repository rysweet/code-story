#!/bin/bash

# CLI Demo Test - Phase 2: Service Infrastructure
# This script tests service health and Phase 2 functionality

set +e
echo "========================================="
echo "CLI Demo Test - Phase 2: Service Infrastructure"
echo "========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test result tracking
PASSED=0
FAILED=0
WARNINGS=0

# Function to log test results
log_test() {
    local status="$1"
    local message="$2"
    local details="$3"
    
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC}: $message"
            ((PASSED++))
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC}: $message"
            if [ -n "$details" ]; then
                echo -e "   ${RED}Details: $details${NC}"
            fi
            ((FAILED++))
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN${NC}: $message"
            if [ -n "$details" ]; then
                echo -e "   ${YELLOW}Details: $details${NC}"
            fi
            ((WARNINGS++))
            ;;
    esac
}

echo "Starting Phase 2 tests..."
echo ""

# Task 2.1: Service Health Checks
echo "=== Task 2.1: Service Health Checks ==="

# Test service status
echo "Testing service status..."
SERVICE_STATUS=$(codestory service status 2>/dev/null || echo "Service status unavailable")
if [[ $SERVICE_STATUS == *"Healthy"* ]]; then
    log_test "PASS" "Service is healthy" "$SERVICE_STATUS"
else
    log_test "FAIL" "Service is not healthy" "$SERVICE_STATUS"
fi

# Test Neo4j connection
echo "Testing Neo4j connection..."
NEO4J_STATUS=$(docker-compose logs neo4j 2>/dev/null | grep -i "connected" || echo "Neo4j connection failed")
if [[ $NEO4J_STATUS == *"connected"* ]]; then
    log_test "PASS" "Neo4j is connected" "$NEO4J_STATUS"
else
    log_test "FAIL" "Neo4j connection failed" "$NEO4J_STATUS"
fi

# Test Redis connection
echo "Testing Redis connection..."
REDIS_STATUS=$(docker-compose logs redis 2>/dev/null | grep -i "ready" || echo "Redis connection failed")
if [[ $REDIS_STATUS == *"ready"* ]]; then
    log_test "PASS" "Redis is ready" "$REDIS_STATUS"
else
    log_test "FAIL" "Redis connection failed" "$REDIS_STATUS"
fi

# Test OpenAI connection
echo "Testing OpenAI connection..."
OPENAI_STATUS=$(codestory service status 2>/dev/null | grep -i "OpenAI API connection successful" || echo "OpenAI connection failed")
if [[ $OPENAI_STATUS == *"successful"* ]]; then
    log_test "PASS" "OpenAI API connection successful" "$OPENAI_STATUS"
else
    log_test "FAIL" "OpenAI API connection failed" "$OPENAI_STATUS"
fi

echo ""

# Task 2.2: Phase 2 Functionality
echo "=== Task 2.2: Phase 2 Functionality ==="

# Test ingestion functionality
echo "Testing ingestion functionality..."
INGESTION_STATUS=$(codestory ingest start . --no-progress 2>/dev/null || echo "Ingestion failed")
if [[ $INGESTION_STATUS == *"Ingestion job started"* ]]; then
    log_test "PASS" "Ingestion started successfully" "$INGESTION_STATUS"
else
    log_test "FAIL" "Ingestion failed" "$INGESTION_STATUS"
fi

# Test visualization generation
echo "Testing visualization generation..."
VISUALIZATION_STATUS=$(codestory visualize generate --output visualization.html 2>/dev/null || echo "Visualization generation failed")
if [[ $VISUALIZATION_STATUS == *"Visualization generated"* ]]; then
    log_test "PASS" "Visualization generated successfully" "$VISUALIZATION_STATUS"
else
    log_test "FAIL" "Visualization generation failed" "$VISUALIZATION_STATUS"
fi

echo ""

# Summary
echo "=== Phase 2 Summary ==="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 2 completed successfully!${NC}"
    echo "Service infrastructure is functional and ready for use."
    exit 0
else
    echo -e "${RED}❌ Phase 2 has failures that must be resolved.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  1. Check Docker logs for errors"
    echo "  2. Verify environment variables in .env"
    echo "  3. Restart services: docker compose down && docker compose up --build"
    exit 1
fi