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

usage() {
    echo "Usage: $0 -e <environment> -g <resource_group> [-l <location>] [-s <subscription>]"
    echo ""
    echo "Options:"
    echo "  -e, --environment     Environment to deploy (dev, test, prod)"
    echo "  -g, --resource-group  Azure Resource Group name"
    echo "  -l, --location        Azure location (default: eastus)"
    echo "  -s, --subscription    Azure subscription ID (default: current subscription)"
    echo "  -h, --help            Display this help message"
    exit 1
}

# Default values
LOCATION="eastus"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -e|--environment)
            ENVIRONMENT="$2"
            shift
            shift
            ;;
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift
            shift
            ;;
        -l|--location)
            LOCATION="$2"
            shift
            shift
            ;;
        -s|--subscription)
            SUBSCRIPTION="$2"
            shift
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "$ENVIRONMENT" || -z "$RESOURCE_GROUP" ]]; then
    print_error "Missing required parameters."
    usage
fi

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "test" && "$ENVIRONMENT" != "prod" ]]; then
    print_error "Environment must be one of: dev, test, prod"
    exit 1
fi

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
BICEP_DIR="$ROOT_DIR/infra/azure"
PARAMS_FILE="$BICEP_DIR/parameters/$ENVIRONMENT.parameters.json"

# Check if parameters file exists
if [[ ! -f "$PARAMS_FILE" ]]; then
    print_error "Parameters file not found: $PARAMS_FILE"
    exit 1
fi

# If subscription is provided, set it
if [[ -n "$SUBSCRIPTION" ]]; then
    print_message "Setting Azure subscription to: $SUBSCRIPTION"
    az account set --subscription "$SUBSCRIPTION"
fi

# Get current subscription
CURRENT_SUB=$(az account show --query id -o tsv)
print_message "Using Azure subscription: $CURRENT_SUB"

# Check if resource group exists, create if not
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    print_message "Creating resource group: $RESOURCE_GROUP"
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
else
    print_message "Using existing resource group: $RESOURCE_GROUP"
fi

# Prompt for secure parameters
read -sp "Enter Neo4j Password: " NEO4J_PASSWORD
echo
read -sp "Enter Azure OpenAI API Key (or press enter to skip): " AZURE_OPENAI_KEY
echo
read -sp "Enter OpenAI API Key (or press enter to skip): " OPENAI_KEY
echo
read -sp "Enter Entra Client Secret (or press enter to skip): " ENTRA_CLIENT_SECRET
echo

# Get Admin Object ID (for Key Vault access)
ADMIN_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)

# Deploy Azure resources
print_message "Starting deployment to $ENVIRONMENT environment in $RESOURCE_GROUP resource group..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_DIR/main.bicep" \
    --parameters "@$PARAMS_FILE" \
    --parameters neo4jPassword="$NEO4J_PASSWORD" \
    --parameters azureOpenaiApiKey="$AZURE_OPENAI_KEY" \
    --parameters openaiApiKey="$OPENAI_KEY" \
    --parameters mcpClientSecret="$ENTRA_CLIENT_SECRET" \
    --parameters secretsOfficerObjectId="$ADMIN_OBJECT_ID"

# Check deployment status
if [ $? -eq 0 ]; then
    print_message "Deployment completed successfully!"
else
    print_error "Deployment failed."
    exit 1
fi

# Get deployment outputs
print_message "Deployment outputs:"
CONTAINER_REGISTRY=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name main --query properties.outputs.containerRegistryName.value -o tsv)
SERVICE_FQDN=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name main --query properties.outputs.serviceFqdn.value -o tsv)
MCP_FQDN=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name main --query properties.outputs.mcpFqdn.value -o tsv)
GUI_FQDN=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name main --query properties.outputs.guiFqdn.value -o tsv)

echo ""
echo "Container Registry: $CONTAINER_REGISTRY"
echo "Service URL: https://$SERVICE_FQDN"
echo "MCP URL: https://$MCP_FQDN"
echo "GUI URL: https://$GUI_FQDN"
echo ""

print_message "Next steps:"
echo "1. Build and push Docker images to the Azure Container Registry"
echo "2. Verify your deployment by accessing the GUI URL"
echo ""