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
    echo "Usage: $0 [--env-name ENV_NAME]"
    echo "Validates the environment configuration for Code Story deployment"
    echo ""
    echo "Options:"
    echo "  --env-name    Name of the azd environment to validate (defaults to active env)"
    echo "  --help        Display this help message"
    exit 1
}

# Process command line args
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --env-name)
            ENV_NAME="$2"
            shift 2
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
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../.." && pwd )"

# If no env name provided, use current active environment
if [ -z "$ENV_NAME" ]; then
    ENV_NAME=$(azd env get-name 2>/dev/null || echo "")
    if [ -z "$ENV_NAME" ]; then
        print_error "No environment specified and no active environment found."
        print_error "Use 'azd env new <name>' to create a new environment or specify --env-name."
        exit 1
    fi
fi

print_message "Validating environment configuration for: $ENV_NAME"

# Check if environment exists
AZURE_ENV_DIR="${REPO_ROOT}/.azure/${ENV_NAME}"
if [ ! -d "$AZURE_ENV_DIR" ]; then
    print_error "Environment directory not found at: $AZURE_ENV_DIR"
    exit 1
fi

# Check for .env file
ENV_FILE="${AZURE_ENV_DIR}/.env"
if [ ! -f "$ENV_FILE" ]; then
    print_warning "Environment file not found at: $ENV_FILE"
    print_warning "Creating a new environment file..."
    touch "$ENV_FILE"
fi

# Load environment variables
export $(grep -v '^#' "${ENV_FILE}" | xargs)

# Define required variables
REQUIRED_VARS=(
    "NEO4J_PASSWORD"
)

# Define optional variables with defaults
OPTIONAL_VARS=(
    "AZURE_LOCATION:eastus"
    "AZURE_SUBSCRIPTION_ID:"
    "AUTH_ENABLED:false"
)

# Authentication-specific variables (required if AUTH_ENABLED=true)
AUTH_VARS=(
    "MCP_CLIENT_ID"
    "MCP_CLIENT_SECRET"
)

# Validate required variables
print_step "Checking required environment variables..."
missing=0

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required variable $var is not set"
        missing=$((missing + 1))
    else
        print_message "✓ $var is set"
    fi
done

# Check and set default values for optional variables
print_step "Checking optional environment variables..."
for var_with_default in "${OPTIONAL_VARS[@]}"; do
    # Split the string on the colon
    var_name=${var_with_default%%:*}
    default_value=${var_with_default#*:}
    
    if [ -z "${!var_name}" ]; then
        if [ -n "$default_value" ]; then
            print_warning "$var_name is not set, will use default: $default_value"
            # Add to .env file
            echo "$var_name=$default_value" >> "$ENV_FILE"
            # Also set in current environment
            export "$var_name=$default_value"
        else
            print_warning "$var_name is not set (no default value)"
        fi
    else
        print_message "✓ $var_name is set to: ${!var_name}"
    fi
done

# Check authentication variables if AUTH_ENABLED=true
if [ "${AUTH_ENABLED}" == "true" ]; then
    print_step "Authentication is enabled, checking required auth variables..."
    for var in "${AUTH_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Authentication variable $var is required when AUTH_ENABLED=true"
            missing=$((missing + 1))
        else
            print_message "✓ $var is set"
        fi
    done
fi

# Validate location is valid
if [ -n "$AZURE_LOCATION" ]; then
    valid_location=$(az account list-locations --query "[?name=='${AZURE_LOCATION}'].name" -o tsv)
    if [ -z "$valid_location" ]; then
        print_error "Invalid AZURE_LOCATION: $AZURE_LOCATION"
        print_message "Run 'az account list-locations --output table' to see valid locations"
        missing=$((missing + 1))
    else
        print_message "✓ AZURE_LOCATION is valid: $AZURE_LOCATION"
    fi
fi

# Validate subscription ID if provided
if [ -n "$AZURE_SUBSCRIPTION_ID" ]; then
    valid_subscription=$(az account list --query "[?id=='${AZURE_SUBSCRIPTION_ID}'].id" -o tsv)
    if [ -z "$valid_subscription" ]; then
        print_error "Invalid AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID"
        print_message "Run 'az account list --output table' to see valid subscriptions"
        missing=$((missing + 1))
    else
        print_message "✓ AZURE_SUBSCRIPTION_ID is valid: $AZURE_SUBSCRIPTION_ID"
    fi
fi

# Summarize validation results
if [ $missing -gt 0 ]; then
    print_error "Validation failed: $missing variables missing or invalid"
    print_error "Please set the required variables using 'azd env set <name> <value>'"
    exit 1
else
    print_message "✓ Environment validation successful!"
fi