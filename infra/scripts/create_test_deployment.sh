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

# Display usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Create a test deployment of Code Story for validation testing"
    echo ""
    echo "Options:"
    echo "  --env-name NAME          Environment name for the test deployment (default: test-env)"
    echo "  --location LOCATION      Azure region for deployment (default: eastus)"
    echo "  --subscription ID        Azure subscription ID to use (uses default if not specified)"
    echo "  --clean                  Clean up existing environment with the same name if it exists"
    echo "  --skip-tests             Skip running tests after deployment"
    echo "  --help                   Display this help message"
    exit 1
}

# Initialize variables
ENV_NAME="test-env-$(date +%s)"
LOCATION="eastus"
SUBSCRIPTION_ID=""
CLEAN=false
SKIP_TESTS=false

# Process command line args
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --env-name)
            ENV_NAME="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --subscription)
            SUBSCRIPTION_ID="$2"
            shift 2
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
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

# Get the absolute path to the repository root
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"

print_step "Setting up test deployment environment: $ENV_NAME"

# Check for required tools
for cmd in azd az docker; do
    if ! command -v $cmd &> /dev/null; then
        print_error "$cmd is not installed or not in PATH"
        exit 1
    fi
done

# Check if environment already exists
if azd env list 2>/dev/null | grep -q "$ENV_NAME"; then
    if [ "$CLEAN" = true ]; then
        print_warning "Environment $ENV_NAME already exists - cleaning up as requested"
        azd env delete "$ENV_NAME" -y
    else
        print_error "Environment $ENV_NAME already exists. Use --clean to replace it or choose a different name."
        exit 1
    fi
fi

# Set subscription if provided
if [ -n "$SUBSCRIPTION_ID" ]; then
    print_message "Setting Azure subscription to $SUBSCRIPTION_ID"
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# Create and configure a new environment
print_step "Creating new Azure Developer CLI environment"
azd env new "$ENV_NAME" --no-prompt

# Set required variables
echo "Setting environment variables..."
azd env set AZURE_LOCATION "$LOCATION"
azd env set NEO4J_PASSWORD "TestPassword123!" # Test password only
azd env set AUTH_ENABLED "false" # Disable auth for testing

# Generate unique names for resources
TIMESTAMP=$(date +%s)
azd env set AZURE_SERVICE_NAME "code-story-test-$TIMESTAMP-service"
azd env set AZURE_MCP_NAME "code-story-test-$TIMESTAMP-mcp"
azd env set AZURE_GUI_NAME "code-story-test-$TIMESTAMP-gui"
azd env set AZURE_NEO4J_NAME "code-story-test-$TIMESTAMP-neo4j"

# Provision infrastructure (but don't deploy code)
print_step "Provisioning Azure resources (this may take 15-20 minutes)"
if ! azd provision; then
    print_error "Failed to provision Azure resources. Check Azure portal for details."
    exit 1
fi

# Get deployment outputs
print_message "Getting deployment outputs..."
SERVICE_FQDN=$(azd env get-values | grep AZURE_SERVICE_FQDN | cut -d= -f2)
MCP_FQDN=$(azd env get-values | grep AZURE_MCP_FQDN | cut -d= -f2)
GUI_FQDN=$(azd env get-values | grep AZURE_GUI_FQDN | cut -d= -f2)
NEO4J_FQDN=$(azd env get-values | grep AZURE_NEO4J_FQDN | cut -d= -f2)

# Deploy code
print_step "Deploying code to Azure resources"
if ! azd deploy; then
    print_error "Failed to deploy code. Check Azure portal for details."
    exit 1
fi

# Run tests if not skipped
if [ "$SKIP_TESTS" = false ]; then
    print_step "Running deployment tests"
    
    # Allow some time for services to start
    print_message "Waiting 60 seconds for services to initialize..."
    sleep 60
    
    # Run the test script
    "$REPO_ROOT/infra/scripts/test_deployment.sh" \
        --service-url "https://$SERVICE_FQDN" \
        --mcp-url "https://$MCP_FQDN" \
        --gui-url "https://$GUI_FQDN" \
        --neo4j-uri "bolt://$NEO4J_FQDN:7687" \
        --neo4j-username "neo4j" \
        --neo4j-password "TestPassword123!" \
        --skip-ingestion
else
    print_message "Skipping tests as requested"
fi

# Print deployment information
print_step "Test Deployment Information"
echo "Environment name: $ENV_NAME"
echo "Service URL:      https://$SERVICE_FQDN"
echo "MCP URL:          https://$MCP_FQDN"
echo "GUI URL:          https://$GUI_FQDN"
echo "Neo4j Server:     $NEO4J_FQDN"

print_message "To delete this test deployment when no longer needed, run:"
echo "azd env select $ENV_NAME && azd down"

print_message "Test deployment completed successfully!"