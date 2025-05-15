# Installation Guide

This guide will walk you through the process of installing and setting up Code Story in different environments.

## Prerequisites

Before installing Code Story, ensure you have the following prerequisites installed on your system:

- Python 3.12 or higher
- Node.js 18 or higher
- Docker and Docker Compose
- Poetry 1.8 or higher
- Git

## Local Development Setup

For a local development setup, follow these steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/rysweet/code-story.git
   cd code-story
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   # Install Python dependencies
   poetry install

   # Install Node.js dependencies
   npm install
   ```

3. Create a `.env` file from the template:

   ```bash
   cp .env-template .env
   ```

4. Edit the `.env` file with your configuration:

   ```
   # Neo4j Configuration
   NEO4J_URI=neo4j://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password

   # Redis Configuration
   REDIS_URI=redis://localhost:6379

   # OpenAI Configuration
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_ORGANIZATION=your-organization-id  # Optional

   # Azure OpenAI Configuration (if using Azure)
   AZURE_OPENAI_API_KEY=your-azure-openai-key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   AZURE_OPENAI_API_VERSION=2023-05-15
   ```

5. Start the services using Docker Compose:

   ```bash
   docker-compose up -d neo4j redis
   ```

6. Start the development servers:

   ```bash
   # Start the Code Story service (in one terminal)
   poetry run uvicorn src.codestory_service.main:app --reload

   # Start the GUI development server (in another terminal)
   npm run dev
   ```

7. Access the GUI at [http://localhost:5173](http://localhost:5173)

## Docker Compose Setup

For a more production-like environment using Docker Compose:

1. Clone the repository:

   ```bash
   git clone https://github.com/rysweet/code-story.git
   cd code-story
   ```

2. Create a `.env` file from the template:

   ```bash
   cp .env-template .env
   ```

3. Edit the `.env` file with your configuration (see above).

4. Start the services using the provided script:

   ```bash
   ./infra/scripts/start.sh
   ```

5. Access the GUI at [http://localhost:5173](http://localhost:5173)

## Production Deployment

For a production deployment, use the production Docker Compose file:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

In production mode, the GUI is served by Nginx on port 80, and all services run in production mode with optimized configurations.

## Azure Deployment Options

### Option 1: Using Bicep Directly

Deploy Code Story to Azure Container Apps using the provided Bicep templates:

1. Login to Azure:

   ```bash
   az login
   ```

2. Deploy the infrastructure:

   ```bash
   ./infra/scripts/deploy_azure.sh -e dev -g code-story-dev
   ```

3. Build and push Docker images to the Azure Container Registry:

   ```bash
   ./infra/scripts/build_push_acr.sh -r <registry-name> -e dev
   ```

### Option 2: Using Azure Developer CLI (azd)

For a simplified deployment experience, you can use the Azure Developer CLI:

1. Install the Azure Developer CLI:

   ```bash
   curl -fsSL https://aka.ms/install-azd.sh | bash
   ```

2. Login to Azure:

   ```bash
   azd auth login
   ```

3. Initialize a new environment:

   ```bash
   azd init --template .
   ```

4. Configure the environment:

   ```bash
   azd env set NEO4J_PASSWORD <your-neo4j-password>
   azd env set OPENAI_API_KEY <your-openai-api-key>
   ```

5. Deploy the application:

   ```bash
   azd up
   ```

The Azure deployment creates:

- Container Apps for Service, Worker, MCP, and GUI
- Managed Neo4j database
- Redis Cache
- Key Vault for secrets
- Log Analytics and Application Insights
- Container Registry

## Troubleshooting

### Connection Issues

If you're having trouble connecting to Neo4j or Redis:

1. Ensure the containers are running:

   ```bash
   docker ps | grep "neo4j\|redis"
   ```

2. Check the container logs:

   ```bash
   docker logs code-story-neo4j
   docker logs code-story-redis
   ```

3. Verify the connection URIs in your `.env` file.

### OpenAI API Issues

If you're experiencing issues with the OpenAI API:

1. Verify your API key is correct.
2. Check if you have sufficient API credits.
3. Ensure you're using a supported model.

### Docker Issues

If you're having Docker-related issues:

1. Ensure Docker is running:

   ```bash
   docker info
   ```

2. Try resetting the containers:

   ```bash
   ./infra/scripts/stop.sh
   ./infra/scripts/start.sh
   ```

3. Check disk space if Docker is failing to start containers:

   ```bash
   df -h
   ```

### Azure Deployment Issues

For Azure deployment issues:

1. Verify your Azure CLI is authenticated:

   ```bash
   az account show
   ```

2. Check deployment logs:

   ```bash
   azd logs
   ```

3. Verify resource group deployment status:

   ```bash
   az deployment group list -g <resource-group> -o table
   ```

If you encounter issues not covered here, please check the [troubleshooting guide](troubleshooting.md) or open an issue on GitHub.