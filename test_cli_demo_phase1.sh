#!/bin/bash

# CLI Demo Test - Phase 1: Infrastructure Setup
# This script tests the foundational infrastructure requirements

set +e
echo "========================================="
echo "CLI Demo Test - Phase 1: Infrastructure Setup"
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

echo "Starting Phase 1 tests..."
echo ""

# Task 1.1: Environment Verification
echo "=== Task 1.1: Environment Verification ==="

# Test Docker installation
echo "Testing Docker installation..."
if command -v docker >/dev/null 2>&1; then
    DOCKER_VERSION=$(docker --version 2>/dev/null || echo "unknown")
    log_test "PASS" "Docker is installed" "$DOCKER_VERSION"
    
    # Test Docker is running
    if docker ps >/dev/null 2>&1; then
        log_test "PASS" "Docker is running"
    else
        log_test "FAIL" "Docker is not running" "Try: sudo systemctl start docker"
    fi
else
    log_test "FAIL" "Docker is not installed" "Install Docker from https://docker.com"
fi

# Test Docker Compose
echo "Testing Docker Compose..."
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version 2>/dev/null || echo "unknown")
    log_test "PASS" "Docker Compose is available" "$COMPOSE_VERSION"
else
    log_test "FAIL" "Docker Compose is not available" "Ensure Docker Compose v2+ is installed"
fi

# Test project structure
echo "Testing project structure..."
REQUIRED_FILES=("docker-compose.yml" "Dockerfile.service" "Dockerfile.worker" ".env.template")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_test "PASS" "Required file exists: $file"
    else
        log_test "FAIL" "Missing required file: $file" "Ensure you're in the project root directory"
    fi
done

# Test Python environment
echo "Testing Python environment..."
if command -v python >/dev/null 2>&1; then
    PYTHON_VERSION=$(python --version 2>/dev/null || echo "unknown")
    log_test "PASS" "Python is available" "$PYTHON_VERSION"
    
    # Test if codestory package is accessible
    if python -c "import codestory" 2>/dev/null; then
        log_test "PASS" "CodeStory package is importable"
    else
        log_test "WARN" "CodeStory package not installed" "Run: pip install -e ."
    fi
else
    log_test "FAIL" "Python is not available" "Install Python 3.12+"
fi

# Test CLI availability
echo "Testing CLI availability..."
if command -v codestory >/dev/null 2>&1; then
    CLI_VERSION=$(codestory --version 2>/dev/null || echo "unknown")
    log_test "PASS" "CodeStory CLI is in PATH" "$CLI_VERSION"
elif python -m codestory.cli.main --version >/dev/null 2>&1; then
    CLI_VERSION=$(python -m codestory.cli.main --version 2>/dev/null || echo "unknown")
    log_test "PASS" "CodeStory CLI available via Python module" "$CLI_VERSION"
else
    log_test "WARN" "CodeStory CLI not available" "Install with: pip install -e ."
fi

echo ""

# Task 1.2: Configuration Setup
echo "=== Task 1.2: Configuration Setup ==="

# Check for .env.template
if [ -f ".env.template" ]; then
    log_test "PASS" "Environment template exists"
    
    # Check if .env exists
    if [ -f ".env" ]; then
        log_test "PASS" "Environment file exists"
        
        # Validate required variables
        REQUIRED_VARS=("NEO4J__URI" "NEO4J__USERNAME" "NEO4J__PASSWORD" "REDIS__URI" "SERVICE__HOST" "SERVICE__PORT")
        for var in "${REQUIRED_VARS[@]}"; do
            if grep -q "^${var}=" .env 2>/dev/null; then
                log_test "PASS" "Required variable configured: $var"
            elif grep -q "^# ${var}=" .env 2>/dev/null; then
                log_test "WARN" "Variable commented out: $var" "Uncomment if needed"
            else
                log_test "FAIL" "Missing required variable: $var"
            fi
        done
    else
        echo "Creating .env file from template..."
        if cp .env.template .env; then
            log_test "PASS" "Created .env from template"
            
            # Configure for Docker environment
            echo "Configuring for Docker environment..."
            sed -i.bak 's/^# NEO4J__URI=bolt:\/\/neo4j:7687/NEO4J__URI=bolt:\/\/neo4j:7687/' .env 2>/dev/null || true
            sed -i.bak 's/^NEO4J__URI=bolt:\/\/localhost:7687/# NEO4J__URI=bolt:\/\/localhost:7687/' .env 2>/dev/null || true
            sed -i.bak 's/^# REDIS__URI=redis:\/\/redis:6379/REDIS__URI=redis:\/\/redis:6379/' .env 2>/dev/null || true
            sed -i.bak 's/^REDIS__URI=redis:\/\/localhost:6379/# REDIS__URI=redis:\/\/localhost:6379/' .env 2>/dev/null || true
            sed -i.bak 's/^# SERVICE__HOST=0.0.0.0/SERVICE__HOST=0.0.0.0/' .env 2>/dev/null || true
            sed -i.bak 's/^SERVICE__HOST=localhost/# SERVICE__HOST=localhost/' .env 2>/dev/null || true
            rm -f .env.bak 2>/dev/null || true
            log_test "PASS" "Configured .env for Docker environment"
        else
            log_test "FAIL" "Could not create .env file"
        fi
    fi
else
    log_test "FAIL" "Environment template missing"
fi

# Check configuration file permissions
if [ -f ".env" ]; then
    if [ -r ".env" ]; then
        log_test "PASS" "Environment file is readable"
    else
        log_test "FAIL" "Environment file is not readable" "Check permissions: chmod 644 .env"
    fi
fi

echo ""

# Summary
echo "=== Phase 1 Summary ==="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 1 completed successfully!${NC}"
    echo "Ready to proceed to Phase 2: Service Infrastructure"
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./test_cli_demo_phase2.sh"
    echo "  2. Or manually start services: docker compose up -d"
    exit 0
else
    echo -e "${RED}❌ Phase 1 has failures that must be resolved before proceeding.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  1. Install missing dependencies"
    echo "  2. Start Docker service"
    echo "  3. Run from correct directory"
    echo "  4. Install CodeStory package: pip install -e ."
    exit 1
fi