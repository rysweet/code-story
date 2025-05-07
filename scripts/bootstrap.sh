#!/bin/bash
set -e

echo "🚀 Bootstrapping Code Story Project"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p .devcontainer .github/workflows \
    docs/{api,architecture,user_guides,developer_guides} \
    gui/{src,public} \
    infra/{docker,scripts,azure} \
    prompts scripts \
    src/codestory/{config,graphdb,llm,ingestion_pipeline,cli} \
    src/codestory_service \
    src/codestory_blarify \
    src/codestory_filesystem \
    src/codestory_summarizer \
    src/codestory_docgrapher \
    tests/{unit,integration}

# Create Python package with Poetry
echo "🐍 Setting up Python package..."
if command -v poetry >/dev/null 2>&1; then
  echo "Poetry is installed, continuing..."
else
  echo "Poetry not found, installing..."
  curl -sSL https://install.python-poetry.org | python3 -
fi

# Initialize Poetry project
echo "📦 Initializing Poetry project..."
poetry init --name codestory --python ">=3.12,<4.0" --no-interaction

# Add dependencies
echo "📚 Adding Python dependencies..."
poetry add pydantic rich "typer[all]" fastapi uvicorn celery redis neo4j openai tenacity prometheus-client structlog opentelemetry-sdk
poetry add --group dev pytest pytest-asyncio pytest-cov testcontainers ruff mypy httpx pytest-mock

# Initialize Node.js project
echo "📦 Initializing Node.js project..."
npm init -y

# Add Node.js dependencies
echo "📚 Adding Node.js dependencies..."
npm install @mantine/core @mantine/hooks @reduxjs/toolkit @vasturiano/3d-force-graph react react-dom three
npm install --save-dev @types/react @types/react-dom @types/three @typescript-eslint/eslint-plugin @typescript-eslint/parser @vitejs/plugin-react eslint eslint-plugin-react-hooks eslint-plugin-react-refresh prettier typescript vite

# Create configuration templates
echo "⚙️ Creating configuration files..."
cat > .env-template << EOL
# API Keys
OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_KEY=your-azure-api-key-here
AZURE_OPENAI_ENDPOINT=your-azure-endpoint-here

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# Redis Configuration
REDIS_URI=redis://localhost:6379

# Azure KeyVault (Optional)
AZURE_KEYVAULT_NAME=your-keyvault-name-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here
AZURE_TENANT_ID=your-tenant-id-here

# Service Configuration
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
LOG_LEVEL=INFO
ENABLE_TELEMETRY=true
ENVIRONMENT=development
EOL

# Make script executable
chmod +x scripts/bootstrap.sh

echo "✅ Project scaffolding complete!"
echo "Next steps:"
echo "1. Edit .env-template and create .env file"
echo "2. Create configuration module with precedence rules"
echo "3. Run 'docker compose up -d' to start all services"