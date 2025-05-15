#!/bin/bash

# Script to deploy Neo4j on Azure Container Apps
# This script sets up Neo4j in Azure Container Apps with proper configuration

set -e

# Default values
RESOURCE_GROUP="codestory-rg"
LOCATION="westus2"
AZURE_CONTAINER_REGISTRY="codestoryacr"
CONTAINER_APP_ENV="codestory-env"
NEO4J_APP_NAME="codestory-neo4j"
NEO4J_IMAGE="neo4j:5.18.0-enterprise"
NEO4J_CPU="2.0"
NEO4J_MEMORY="4Gi"
NEO4J_MIN_REPLICAS=1
NEO4J_MAX_REPLICAS=1

# Process command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --location)
      LOCATION="$2"
      shift 2
      ;;
    --registry)
      AZURE_CONTAINER_REGISTRY="$2"
      shift 2
      ;;
    --env)
      CONTAINER_APP_ENV="$2"
      shift 2
      ;;
    --app-name)
      NEO4J_APP_NAME="$2"
      shift 2
      ;;
    --image)
      NEO4J_IMAGE="$2"
      shift 2
      ;;
    --cpu)
      NEO4J_CPU="$2"
      shift 2
      ;;
    --memory)
      NEO4J_MEMORY="$2"
      shift 2
      ;;
    --min-replicas)
      NEO4J_MIN_REPLICAS="$2"
      shift 2
      ;;
    --max-replicas)
      NEO4J_MAX_REPLICAS="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed or not in PATH"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo "Error: Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "Creating Azure resources for CodeStory Neo4j deployment..."

# Create resource group if it doesn't exist
if ! az group show --name "${RESOURCE_GROUP}" &> /dev/null; then
    echo "Creating resource group: ${RESOURCE_GROUP}"
    az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
fi

# Create Azure Container Registry if it doesn't exist
if ! az acr show --name "${AZURE_CONTAINER_REGISTRY}" &> /dev/null; then
    echo "Creating Azure Container Registry: ${AZURE_CONTAINER_REGISTRY}"
    az acr create --resource-group "${RESOURCE_GROUP}" --name "${AZURE_CONTAINER_REGISTRY}" --sku Standard
    
    # Enable admin user
    az acr update --name "${AZURE_CONTAINER_REGISTRY}" --admin-enabled true
fi

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name "${AZURE_CONTAINER_REGISTRY}" --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name "${AZURE_CONTAINER_REGISTRY}" --query "passwords[0].value" -o tsv)

# Import Neo4j image to ACR
echo "Importing Neo4j image to ACR..."
az acr import --name "${AZURE_CONTAINER_REGISTRY}" --source "${NEO4J_IMAGE}" --image "neo4j:latest"

# Create Container App Environment if it doesn't exist
if ! az containerapp env show --name "${CONTAINER_APP_ENV}" --resource-group "${RESOURCE_GROUP}" &> /dev/null; then
    echo "Creating Container App Environment: ${CONTAINER_APP_ENV}"
    az containerapp env create \
        --name "${CONTAINER_APP_ENV}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}"
fi

# Create Azure Files share for Neo4j data
echo "Creating Storage Account for Neo4j data..."
STORAGE_ACCOUNT_NAME="codestoryneo4j"
STORAGE_SHARE_NAME="neo4jdata"

# Create storage account if it doesn't exist
if ! az storage account show --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RESOURCE_GROUP}" &> /dev/null; then
    az storage account create \
        --name "${STORAGE_ACCOUNT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --sku Standard_LRS
fi

# Get storage key
STORAGE_KEY=$(az storage account keys list --account-name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RESOURCE_GROUP}" --query "[0].value" -o tsv)

# Create file share if it doesn't exist
if ! az storage share exists --name "${STORAGE_SHARE_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}" --account-key "${STORAGE_KEY}" | grep -q "true"; then
    az storage share create \
        --name "${STORAGE_SHARE_NAME}" \
        --account-name "${STORAGE_ACCOUNT_NAME}" \
        --account-key "${STORAGE_KEY}"
fi

# Create sub-directories
for DIR in "data" "logs" "import" "plugins"; do
    az storage directory create \
        --name "${DIR}" \
        --share-name "${STORAGE_SHARE_NAME}" \
        --account-name "${STORAGE_ACCOUNT_NAME}" \
        --account-key "${STORAGE_KEY}"
done

# Create Azure Key Vault for secrets
KEYVAULT_NAME="codestory-kv"
if ! az keyvault show --name "${KEYVAULT_NAME}" --resource-group "${RESOURCE_GROUP}" &> /dev/null; then
    echo "Creating Key Vault: ${KEYVAULT_NAME}"
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}"
fi

# Generate Neo4j password if not already in Key Vault
if ! az keyvault secret show --name "neo4j-password" --vault-name "${KEYVAULT_NAME}" &> /dev/null; then
    NEO4J_PASSWORD=$(openssl rand -base64 16)
    az keyvault secret set \
        --name "neo4j-password" \
        --vault-name "${KEYVAULT_NAME}" \
        --value "${NEO4J_PASSWORD}"
else
    NEO4J_PASSWORD=$(az keyvault secret show --name "neo4j-password" --vault-name "${KEYVAULT_NAME}" --query "value" -o tsv)
fi

# Deploy Neo4j Container App
echo "Deploying Neo4j Container App: ${NEO4J_APP_NAME}"
az containerapp create \
    --name "${NEO4J_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --environment "${CONTAINER_APP_ENV}" \
    --registry-server "${AZURE_CONTAINER_REGISTRY}.azurecr.io" \
    --registry-username "${ACR_USERNAME}" \
    --registry-password "${ACR_PASSWORD}" \
    --image "${AZURE_CONTAINER_REGISTRY}.azurecr.io/neo4j:latest" \
    --target-port 7474 \
    --ingress external \
    --min-replicas "${NEO4J_MIN_REPLICAS}" \
    --max-replicas "${NEO4J_MAX_REPLICAS}" \
    --cpu "${NEO4J_CPU}" \
    --memory "${NEO4J_MEMORY}" \
    --env-vars \
        "NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}" \
        "NEO4J_ACCEPT_LICENSE_AGREEMENT=yes" \
        "NEO4J_PLUGINS=[\"apoc\", \"graph-data-science\"]" \
        "NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*" \
        "NEO4J_dbms_memory_heap_initial__size=1G" \
        "NEO4J_dbms_memory_heap_max__size=2G" \
        "NEO4J_dbms_memory_pagecache_size=1G" \
        "NEO4J_metrics_enabled=true" \
        "NEO4J_metrics_prometheus_enabled=true" \
    --scale-rule-name "http-scale" \
    --scale-rule-http-concurrency 100

# Add storage mount
echo "Adding Azure Files storage mount to Container App..."
az containerapp update \
    --name "${NEO4J_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --volume-name neo4j-storage \
    --volume-storage-type AzureFile \
    --volume-storage-name "${STORAGE_SHARE_NAME}" \
    --volume-storage-account-name "${STORAGE_ACCOUNT_NAME}" \
    --volume-storage-account-key "${STORAGE_KEY}" \
    --mount-name neo4j-data \
    --mount-path /data \
    --mount-name neo4j-logs \
    --mount-path /logs \
    --mount-name neo4j-import \
    --mount-path /import \
    --mount-name neo4j-plugins \
    --mount-path /plugins

# Expose additional ports
echo "Exposing additional ports in Container App..."
az containerapp ingress update \
    --name "${NEO4J_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --target-port 7474 \
    --exposed-port 7474 \
    --transport auto \
    --type external \
    --allow-insecure

az containerapp ingress update \
    --name "${NEO4J_APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --target-port 7687 \
    --exposed-port 7687 \
    --transport auto \
    --type external \
    --allow-insecure

# Output connection information
NEO4J_URL=$(az containerapp show --name "${NEO4J_APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Deployment complete!"
echo "Neo4j Browser URL: https://${NEO4J_URL}"
echo "Neo4j Bolt URL: bolt://${NEO4J_URL}:7687"
echo "Neo4j Username: neo4j"
echo "Neo4j Password: [stored in Key Vault '${KEYVAULT_NAME}' as 'neo4j-password']"