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

# Load environment variables
AZURE_ENV_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../.." && pwd )/.azure/${AZURE_ENV_NAME}"
ENV_FILE="${AZURE_ENV_DIR}/.env"

if [ -f "${ENV_FILE}" ]; then
    print_message "Loading environment variables from ${ENV_FILE}"
    export $(grep -v '^#' "${ENV_FILE}" | xargs)
else
    print_warning "Environment file not found at ${ENV_FILE}"
fi

print_message "Post-provision hook executed successfully!"
print_message "Code Story deployment resources:"
echo "Service URL:  https://${AZURE_SERVICE_FQDN}"
echo "MCP URL:      https://${AZURE_MCP_FQDN}"
echo "GUI URL:      https://${AZURE_GUI_FQDN}"
echo "Neo4j Server: ${AZURE_NEO4J_FQDN}"

print_message "Next steps:"
echo "1. Initialize the application by running: curl -X POST https://${AZURE_SERVICE_FQDN}/api/system/init"
echo "2. Access the GUI at: https://${AZURE_GUI_FQDN}"
echo ""