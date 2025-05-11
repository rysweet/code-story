# Azure Developer CLI (azd) Configuration

This directory contains the configuration files for deploying Code Story using the Azure Developer CLI (azd).

## Prerequisites

- [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- [Docker](https://docs.docker.com/get-docker/)
- Azure subscription

## Setup

1. Install the Azure Developer CLI:
   ```bash
   curl -fsSL https://aka.ms/install-azd.sh | bash
   # Or on Windows, use the Windows installer
   ```

2. Login to Azure:
   ```bash
   azd auth login
   ```

## Deployment

### Initialize a new environment

```bash
# Create a new environment
azd init --template .
```

### Configure the environment

```bash
# Set required variables
azd env set NEO4J_PASSWORD <your-neo4j-password>

# Optional: Set OpenAI API keys
azd env set OPENAI_API_KEY <your-openai-api-key>
azd env set AZURE_OPENAI_API_KEY <your-azure-openai-api-key>

# Optional: Set authentication parameters
azd env set AUTH_ENABLED true
azd env set MCP_CLIENT_ID <your-entra-client-id>
azd env set MCP_CLIENT_SECRET <your-entra-client-secret>
```

### Deploy to Azure

```bash
# Deploy everything (provision infrastructure and deploy code)
azd up
```

This will:
1. Provision all required infrastructure in Azure
2. Build Docker images for all services
3. Deploy images to Azure Container Registry
4. Deploy Container Apps pointing to these images
5. Configure networking, secrets, and environment variables

### Deploy just infrastructure or code

```bash
# Provision/update just the infrastructure
azd provision

# Deploy just the code (without changing infrastructure)
azd deploy
```

## Cleanup

To delete the entire environment:

```bash
azd down
```

## How it works

The azd deployment process:

1. `azure.yaml` - Defines services and their Docker build contexts
2. `infra/azd/main.bicep` - Main infrastructure entry point at subscription scope
3. `infra/azd/infrastructure.bicep` - Resources to deploy in resource group
4. `infra/azd/main.parameters.json` - Parameter template for deployment
5. `infra/azd/hooks/*.sh` - Pre/post hooks for deployment workflow

The actual infrastructure components are defined in `infra/azure/modules/` which are reused
by both the manual Bicep deployment and the azd deployment.