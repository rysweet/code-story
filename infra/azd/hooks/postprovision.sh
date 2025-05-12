#!/bin/bash
set -e

# Colors for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

# Function to check if a service endpoint is up
check_endpoint() {
    local endpoint=$1
    local max_attempts=$2
    local wait_seconds=$3
    local attempt=1
    local status_code

    print_message "Checking endpoint: $endpoint"

    while [ $attempt -le $max_attempts ]; do
        print_message "  Attempt $attempt of $max_attempts..."

        status_code=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint" || echo "failed")

        if [[ "$status_code" == "200" || "$status_code" == "401" ]]; then
            print_message "  ✓ Endpoint is up and responding (status: $status_code)"
            return 0
        else
            print_warning "  Endpoint returned status: $status_code, waiting $wait_seconds seconds..."
            sleep $wait_seconds
            ((attempt++))
        fi
    done

    print_error "  ✗ Endpoint failed to respond after $max_attempts attempts"
    return 1
}

# Get repository root
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../.." && pwd )"

# Load environment variables
AZURE_ENV_DIR="${REPO_ROOT}/.azure/${AZURE_ENV_NAME}"
ENV_FILE="${AZURE_ENV_DIR}/.env"

if [ -f "${ENV_FILE}" ]; then
    print_message "Loading environment variables from ${ENV_FILE}"
    export $(grep -v '^#' "${ENV_FILE}" | xargs)
else
    print_warning "Environment file not found at ${ENV_FILE}"
fi

print_step "Running post-provisioning validation..."

# Check if all required environment variables are set
required_vars=(
    "AZURE_SERVICE_FQDN"
    "AZURE_MCP_FQDN"
    "AZURE_GUI_FQDN"
    "AZURE_NEO4J_FQDN"
)

missing_vars=0
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required variable $var is not set"
        ((missing_vars++))
    fi
done

if [ $missing_vars -gt 0 ]; then
    print_error "Post-provision validation failed: $missing_vars required variables missing"
    exit 1
fi

# Validate that the services are running
print_step "Validating deployed services (this may take a few minutes)..."

# Define endpoints to check
service_endpoint="https://${AZURE_SERVICE_FQDN}/health"
mcp_endpoint="https://${AZURE_MCP_FQDN}/v1/health"
gui_endpoint="https://${AZURE_GUI_FQDN}"

# Check each endpoint with retries
failed=0
check_endpoint "$service_endpoint" 10 30 || ((failed++))
check_endpoint "$mcp_endpoint" 10 30 || ((failed++))
check_endpoint "$gui_endpoint" 10 30 || ((failed++))

if [ $failed -gt 0 ]; then
    print_warning "Some service endpoints are not responding yet. This could be normal during initial deployment."
    print_warning "Please check the Azure Portal for deployment status."
else
    print_message "✓ All service endpoints are up and running!"
fi

# Save deployment outputs to a file for reference
output_file="${AZURE_ENV_DIR}/deployment_info.json"
print_step "Saving deployment information to $output_file..."

cat > "$output_file" << EOL
{
  "environment": "${AZURE_ENV_NAME}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "endpoints": {
    "service": "https://${AZURE_SERVICE_FQDN}",
    "mcp": "https://${AZURE_MCP_FQDN}",
    "gui": "https://${AZURE_GUI_FQDN}",
    "neo4j": "${AZURE_NEO4J_FQDN}"
  }
}
EOL

print_message "✓ Deployment information saved to $output_file"

# Print summary of the deployment
print_step "Deployment Summary"
echo -e "${GREEN}┌────────────────────────────────────────────────────┐${NC}"
echo -e "${GREEN}│              CODE STORY DEPLOYMENT                 │${NC}"
echo -e "${GREEN}├────────────────────────────────────────────────────┤${NC}"
echo -e "${GREEN}│${NC} Environment:  ${AZURE_ENV_NAME}"
echo -e "${GREEN}│${NC} Region:       ${AZURE_LOCATION}"
echo -e "${GREEN}│${NC} Service URL:  https://${AZURE_SERVICE_FQDN}"
echo -e "${GREEN}│${NC} MCP URL:      https://${AZURE_MCP_FQDN}"
echo -e "${GREEN}│${NC} GUI URL:      https://${AZURE_GUI_FQDN}"
echo -e "${GREEN}│${NC} Neo4j Server: ${AZURE_NEO4J_FQDN}"
echo -e "${GREEN}└────────────────────────────────────────────────────┘${NC}"

print_step "Next Steps"
echo "1. Initialize the application by running: curl -X POST https://${AZURE_SERVICE_FQDN}/api/system/init"
echo "2. Access the GUI at: https://${AZURE_GUI_FQDN}"
echo "3. Monitor application health in Azure portal"
echo "4. Set up monitoring alerts if enabled"
echo ""

print_message "Post-provision hook completed successfully!"