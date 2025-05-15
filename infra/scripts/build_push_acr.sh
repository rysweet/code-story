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
    echo "Usage: $0 -r <registry_name> [-e <environment>] [-s <subscription>] [--no-push]"
    echo ""
    echo "Options:"
    echo "  -r, --registry       Azure Container Registry name"
    echo "  -e, --environment    Environment tag for images (dev, prod). Default: dev"
    echo "  -s, --subscription   Azure subscription ID (default: current subscription)"
    echo "  --no-push            Build images locally only, don't push to ACR"
    echo "  -h, --help           Display this help message"
    exit 1
}

# Default values
ENVIRONMENT="dev"
PUSH=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -r|--registry)
            REGISTRY_NAME="$2"
            shift
            shift
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift
            shift
            ;;
        -s|--subscription)
            SUBSCRIPTION="$2"
            shift
            shift
            ;;
        --no-push)
            PUSH=false
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
if [[ -z "$REGISTRY_NAME" ]]; then
    print_error "Missing required parameters."
    usage
fi

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="$ROOT_DIR/infra/docker"

# If subscription is provided, set it
if [[ -n "$SUBSCRIPTION" ]]; then
    print_message "Setting Azure subscription to: $SUBSCRIPTION"
    az account set --subscription "$SUBSCRIPTION"
fi

# Get current subscription
CURRENT_SUB=$(az account show --query name -o tsv)
print_message "Using Azure subscription: $CURRENT_SUB"

# Check if registry exists
if ! az acr show --name "$REGISTRY_NAME" &> /dev/null; then
    print_error "Container registry not found: $REGISTRY_NAME"
    exit 1
fi

# Login to ACR if pushing
if $PUSH; then
    print_message "Logging in to Azure Container Registry: $REGISTRY_NAME"
    az acr login --name "$REGISTRY_NAME"
fi

# Set registry URL
ACR_URL="${REGISTRY_NAME}.azurecr.io"

# Function to build and push an image
build_and_push() {
    local service=$1
    local dockerfile=$2
    local build_args=$3
    local tag="$ACR_URL/codestory/$service:$ENVIRONMENT"
    
    print_message "Building $service image..."
    docker build -f "$dockerfile" -t "$tag" $build_args $ROOT_DIR
    
    if $PUSH; then
        print_message "Pushing $service image to $ACR_URL..."
        docker push "$tag"
    fi
}

# Build service image
print_message "Building and tagging images for environment: $ENVIRONMENT"
build_and_push "service" "$DOCKER_DIR/service.Dockerfile" "--target production"

# Build worker image
build_and_push "worker" "$DOCKER_DIR/service.Dockerfile" "--target worker"

# Build MCP image
build_and_push "mcp" "$DOCKER_DIR/mcp.Dockerfile" "--target production"

# Build GUI image
build_and_push "gui" "$DOCKER_DIR/gui.Dockerfile" "--target production"

print_message "All images built successfully!"
if $PUSH; then
    print_message "All images pushed to $ACR_URL"
else
    print_message "Images were not pushed (--no-push flag used)"
fi

print_message "Image tags:"
echo "- $ACR_URL/codestory/service:$ENVIRONMENT"
echo "- $ACR_URL/codestory/worker:$ENVIRONMENT"
echo "- $ACR_URL/codestory/mcp:$ENVIRONMENT"
echo "- $ACR_URL/codestory/gui:$ENVIRONMENT"
echo ""