#!/bin/bash
set -e

# Colors for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Function to check if a required variable is set
check_required_var() {
    local var_name=$1
    local var_value=${!var_name}

    if [ -z "$var_value" ]; then
        print_error "Required variable $var_name is not set"
        return 1
    else
        print_message "✓ Variable $var_name is set"
        return 0
    fi
}

# Validate Docker installation
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_error "Please install Docker from https://docs.docker.com/get-docker/"
        return 1
    else
        docker_version=$(docker --version)
        print_message "✓ Docker is installed: $docker_version"
        return 0
    fi
}

# Validate Azure CLI installation
check_azure_cli() {
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed or not in PATH"
        print_error "Please install Azure CLI from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        return 1
    else
        az_version=$(az --version | head -n 1)
        print_message "✓ Azure CLI is installed: $az_version"
        return 0
    fi
}

# Validate login status
check_azure_login() {
    if ! az account show &> /dev/null; then
        print_error "Not logged in to Azure. Please run 'az login'"
        return 1
    else
        account_info=$(az account show --query "{subscription:name,id:id,user:user.name}" -o tsv)
        print_message "✓ Logged in to Azure: $account_info"
        return 0
    fi
}

# Get the absolute path to the repository root
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

print_message "Pre-deploy hook is running..."

# Check prerequisites
print_message "Checking prerequisites..."
failed=0

check_docker || ((failed++))
check_azure_cli || ((failed++))
check_azure_login || ((failed++))

# Check required variables for deployment
print_message "Validating required environment variables..."

# Core environment variables
check_required_var "AZURE_ENV_NAME" || ((failed++))
check_required_var "AZURE_LOCATION" || ((failed++))
check_required_var "AZURE_SUBSCRIPTION_ID" || ((failed++))

# Neo4j required variables
check_required_var "NEO4J_PASSWORD" || ((failed++))

# Authentication variables if enabled
if [ "${AUTH_ENABLED}" == "true" ]; then
    check_required_var "MCP_CLIENT_ID" || ((failed++))
    check_required_var "MCP_CLIENT_SECRET" || ((failed++))
fi

# Validate Bicep files
print_message "Validating Bicep files..."
if ! az bicep build --file "${REPO_ROOT}/infra/azd/main.bicep" 2>/dev/null; then
    print_error "Bicep validation failed for main.bicep"
    ((failed++))
else
    print_message "✓ Bicep validation succeeded for main.bicep"
fi

if [ $failed -gt 0 ]; then
    print_error "Pre-deploy validation failed with $failed errors"
    exit 1
fi

# Ensure services are ready for deployment
print_message "Running pre-deployment preparations..."

# Ensure resource providers are registered
print_message "Ensuring required resource providers are registered..."
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Cache

print_message "Pre-deploy hook completed successfully!"