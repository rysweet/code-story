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

# In a full implementation, you might want to add any custom preparation steps here
# such as database migrations, etc.

print_message "Pre-deploy hook completed successfully!"