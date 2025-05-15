#!/bin/bash
set -e

# Colors for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
}

# Display usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Run comprehensive tests against a deployed Code Story instance"
    echo ""
    echo "Options:"
    echo "  --service-url URL        Base URL of the service API (required)"
    echo "  --mcp-url URL            Base URL of the MCP API"
    echo "  --gui-url URL            Base URL of the GUI"
    echo "  --neo4j-uri URI          Neo4j connection URI (with protocol)"
    echo "  --neo4j-username USER    Neo4j username (default: neo4j)"
    echo "  --neo4j-password PASS    Neo4j password" 
    echo "  --test-repo URL          Git repo URL to use for testing ingestion"
    echo "  --skip-ingestion         Skip ingestion tests (faster)"
    echo "  --json                   Output results in JSON format"
    echo "  --help                   Display this help message"
    exit 1
}

# Initialize variables
SERVICE_URL=""
MCP_URL=""
GUI_URL=""
NEO4J_URI=""
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD=""
TEST_REPO="https://github.com/rysweet/small-test-repo"
SKIP_INGESTION=false
JSON_OUTPUT=false
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Process command line args
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --service-url)
            SERVICE_URL="$2"
            shift 2
            ;;
        --mcp-url)
            MCP_URL="$2"
            shift 2
            ;;
        --gui-url)
            GUI_URL="$2"
            shift 2
            ;;
        --neo4j-uri)
            NEO4J_URI="$2"
            shift 2
            ;;
        --neo4j-username)
            NEO4J_USERNAME="$2"
            shift 2
            ;;
        --neo4j-password)
            NEO4J_PASSWORD="$2"
            shift 2
            ;;
        --test-repo)
            TEST_REPO="$2"
            shift 2
            ;;
        --skip-ingestion)
            SKIP_INGESTION=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$SERVICE_URL" ]; then
    print_error "Service URL is required. Use --service-url to specify it."
    usage
fi

# Remove trailing slash from URLs if present
SERVICE_URL="${SERVICE_URL%/}"
MCP_URL="${MCP_URL%/}"
GUI_URL="${GUI_URL%/}"

# Function to run a test and record results
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    local skip="${3:-false}"
    
    ((TOTAL_TESTS++))
    
    if [ "$skip" = true ]; then
        print_test "$test_name [SKIPPED]"
        ((SKIPPED_TESTS++))
        return 0
    fi
    
    print_test "$test_name..."
    
    if eval "$test_cmd"; then
        print_message "✓ Test passed: $test_name"
        ((PASSED_TESTS++))
        return 0
    else
        print_error "✗ Test failed: $test_name"
        ((FAILED_TESTS++))
        return 1
    fi
}

# Start time tracking
START_TIME=$(date +%s)

print_step "Starting Code Story deployment validation tests"
print_message "Service URL: $SERVICE_URL"
[ -n "$MCP_URL" ] && print_message "MCP URL: $MCP_URL"
[ -n "$GUI_URL" ] && print_message "GUI URL: $GUI_URL"
[ -n "$NEO4J_URI" ] && print_message "Neo4j URI: $NEO4J_URI"

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    print_error "curl is not installed or not in PATH. Please install curl."
    exit 1
fi

# Create a temporary directory for test artifacts
TEMP_DIR=$(mktemp -d)
print_message "Created temporary directory: $TEMP_DIR"

# Cleanup function
cleanup() {
    print_message "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

# Set up trap for cleanup on exit
trap cleanup EXIT

# TEST GROUP 1: Service Endpoints
print_step "Testing service endpoints"

# Service health check
run_test "Service health endpoint" \
    "curl -s -f -o /dev/null -w '%{http_code}' \"$SERVICE_URL/health\" | grep -q 200"

# Service API version endpoint
run_test "Service API version endpoint" \
    "curl -s -f \"$SERVICE_URL/version\" | grep -q 'version'"

# SERVICE TEST GROUP 2: MCP Endpoints (if URL provided)
if [ -n "$MCP_URL" ]; then
    print_step "Testing MCP endpoints"
    
    # MCP health check
    run_test "MCP health endpoint" \
        "curl -s -f -o /dev/null -w '%{http_code}' \"$MCP_URL/v1/health\" | grep -q 200"
    
    # MCP API version endpoint
    run_test "MCP API version endpoint" \
        "curl -s -f \"$MCP_URL/v1/version\" | grep -q 'version'"
else
    print_warning "Skipping MCP tests - no MCP URL provided"
fi

# SERVICE TEST GROUP 3: GUI Endpoints (if URL provided)
if [ -n "$GUI_URL" ]; then
    print_step "Testing GUI endpoints"
    
    # GUI check
    run_test "GUI main page" \
        "curl -s -f -o /dev/null -w '%{http_code}' \"$GUI_URL\" | grep -q '200\\|301\\|302'"
    
    # Check for common assets
    run_test "GUI assets" \
        "curl -s -f -o /dev/null -w '%{http_code}' \"$GUI_URL/assets/index.js\" | grep -q '200\\|301\\|302'"
else
    print_warning "Skipping GUI tests - no GUI URL provided"
fi

# SERVICE TEST GROUP 4: Neo4j Database (if URI provided)
if [ -n "$NEO4J_URI" ] && [ -n "$NEO4J_PASSWORD" ]; then
    print_step "Testing Neo4j database connection"
    
    # Check Neo4j connection
    run_test "Neo4j connection" \
        "curl -s -f -u \"$NEO4J_USERNAME:$NEO4J_PASSWORD\" -H 'Content-Type: application/json' -d '{\"statements\": [{\"statement\": \"RETURN 1 AS test\"}]}' \"$NEO4J_URI/db/neo4j/tx/commit\" | grep -q 'results'"
else
    print_warning "Skipping Neo4j tests - no Neo4j URI or password provided"
fi

# SERVICE TEST GROUP 5: Configuration API
print_step "Testing configuration API"

# Get configuration
run_test "Get configuration" \
    "curl -s -f \"$SERVICE_URL/api/config\" > \"$TEMP_DIR/config.json\" && cat \"$TEMP_DIR/config.json\" | grep -q 'settings'"

# SERVICE TEST GROUP 6: Ingestion Workflow (if not skipped)
if [ "$SKIP_INGESTION" = false ]; then
    print_step "Testing ingestion workflow"
    
    # Start ingestion job
    JOB_ID=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"repository_url\": \"$TEST_REPO\"}" "$SERVICE_URL/api/ingest" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$JOB_ID" ]; then
        print_message "Started ingestion job with ID: $JOB_ID"
        
        # Check ingestion job status
        run_test "Ingestion job created" \
            "[ -n \"$JOB_ID\" ]"
        
        # Poll job status until complete or timeout
        timeout=300  # 5 minutes timeout
        start_time=$(date +%s)
        status="pending"
        
        while [ "$status" != "completed" ] && [ "$status" != "failed" ] && [ "$(( $(date +%s) - start_time ))" -lt "$timeout" ]; do
            print_message "Checking ingestion status... (current: $status)"
            status=$(curl -s "$SERVICE_URL/api/ingest/$JOB_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            
            if [ -z "$status" ]; then
                status="unknown"
            fi
            
            sleep 10
        done
        
        # Check final job status
        run_test "Ingestion job completed" \
            "[ \"$status\" = \"completed\" ]"
        
        # Check if nodes were created in the graph
        if [ -n "$NEO4J_URI" ] && [ -n "$NEO4J_PASSWORD" ]; then
            run_test "Nodes created in graph" \
                "curl -s -f -u \"$NEO4J_USERNAME:$NEO4J_PASSWORD\" -H 'Content-Type: application/json' -d '{\"statements\": [{\"statement\": \"MATCH (n) RETURN count(n) AS count\"}]}' \"$NEO4J_URI/db/neo4j/tx/commit\" | grep -q '\"count\":[1-9]'"
        else
            print_warning "Skipping node count check - Neo4j credentials not provided"
        fi
    else
        print_error "Failed to start ingestion job"
        run_test "Start ingestion job" "false"
    fi
else
    print_warning "Skipping ingestion tests - use --skip-ingestion=false to enable"
fi

# Calculate test duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Print test summary
print_step "Test Summary"
echo "Total tests:   $TOTAL_TESTS"
echo "Passed tests:  $PASSED_TESTS"
echo "Failed tests:  $FAILED_TESTS"
echo "Skipped tests: $SKIPPED_TESTS"
echo "Duration:      ${DURATION}s"

# Output JSON results if requested
if [ "$JSON_OUTPUT" = true ]; then
    JSON_FILE="$TEMP_DIR/test_results.json"
    cat > "$JSON_FILE" << EOL
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "service_url": "$SERVICE_URL",
  "mcp_url": "$MCP_URL",
  "gui_url": "$GUI_URL",
  "neo4j_uri": "$NEO4J_URI",
  "test_results": {
    "total": $TOTAL_TESTS,
    "passed": $PASSED_TESTS,
    "failed": $FAILED_TESTS,
    "skipped": $SKIPPED_TESTS
  },
  "duration_seconds": $DURATION
}
EOL
    cat "$JSON_FILE"
fi

# Return success only if all tests passed
if [ $FAILED_TESTS -eq 0 ]; then
    print_message "✅ All tests passed successfully!"
    exit 0
else
    print_error "❌ Some tests failed. See above for details."
    exit 1
fi