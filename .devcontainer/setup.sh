#!/bin/bash
set -e

echo "Setting up Code Story development environment for Codespaces..."

# Ensure we're in the workspace directory
cd /workspace

# Create virtual environment
if [ ! -d "/workspace/.venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv /workspace/.venv
fi

# Activate virtual environment
source /workspace/.venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install the project in development mode
echo "Installing Code Story project..."
pip install -e .

# Install development tools
echo "Installing development tools..."
pip install black ruff mypy pytest

# Install Docker CLI if not present (should be available via Docker-in-Docker feature)
if ! command -v docker &> /dev/null; then
    echo "Docker CLI not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Add user to docker group for Docker-in-Docker
if ! groups vscode | grep -q docker; then
    echo "Adding vscode user to docker group..."
    sudo usermod -aG docker vscode
fi

# Create default configuration files if they don't exist
if [ ! -f "/workspace/.env" ]; then
    echo "Creating default .env file..."
    if [ -f "/workspace/.env.template" ]; then
        cp /workspace/.env.template /workspace/.env
        echo "Default .env file created from template."
    else
        echo "No .env.template found, creating minimal .env..."
        cat > /workspace/.env << EOF
# Core settings
APP_NAME=code-story
VERSION=0.1.0
LOG_LEVEL=INFO

# Authentication
AUTH_ENABLED=false

# Neo4j settings (for Docker Compose)
NEO4J__URI=bolt://localhost:7687
NEO4J__USERNAME=neo4j
NEO4J__PASSWORD=password

# Redis settings (for Docker Compose)
REDIS__URI=redis://localhost:6379

# OpenAI settings
OPENAI__ENDPOINT=https://api.openai.com/v1
OPENAI__API_KEY=your-api-key-here
OPENAI__EMBEDDING_MODEL=text-embedding-3-small
EOF
    fi
fi

if [ ! -f "/workspace/.codestory.toml" ]; then
    echo "Creating default configuration file..."
    if [ -f "/workspace/.codestory.default.toml" ]; then
        cp /workspace/.codestory.default.toml /workspace/.codestory.toml
        echo "Default configuration created from template."
    else
        echo "No default template found, creating minimal configuration..."
        cat > /workspace/.codestory.toml << EOF
[general]
app_name = "code-story"
version = "0.1.0"
environment = "development"
log_level = "INFO"
auth_enabled = false

[neo4j]
uri = "bolt://localhost:7687"
username = "neo4j"
password = "password"
database = "neo4j"
connection_timeout = 30
max_connection_pool_size = 50
connection_acquisition_timeout = 60

[redis]
uri = "redis://localhost:6379"

[openai]
endpoint = "https://api.openai.com/v1"
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o"
reasoning_model = "gpt-4o"
max_retries = 3
retry_backoff_factor = 2.0
temperature = 0.1
EOF
    fi
fi

# Install Node.js dependencies for GUI development
if [ -f "/workspace/package.json" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

# Set correct permissions
sudo chown -R vscode:vscode /workspace/.venv 2>/dev/null || true
sudo chmod +x /workspace/scripts/*.sh 2>/dev/null || true

# Create a script to easily start the development environment
cat > /workspace/start-dev.sh << 'EOF'
#!/bin/bash
echo "Starting Code Story development environment..."

# Check if Docker is available
if ! docker info > /dev/null 2>&1; then
    echo "Warning: Docker is not available. You may need to restart the container or check Docker-in-Docker setup."
    echo "Try running: sudo service docker start"
fi

echo "Environment setup complete!"
echo ""
echo "To start the full environment with Docker Compose:"
echo "  docker-compose up -d"
echo ""
echo "To run tests:"
echo "  source .venv/bin/activate && pytest"
echo ""
echo "To use the CLI:"
echo "  source .venv/bin/activate && python -m codestory.cli.main --help"
echo ""
echo "For GUI development:"
echo "  npm run dev"
EOF

chmod +x /workspace/start-dev.sh

echo "Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Run './start-dev.sh' to see available commands"
echo "2. Activate the virtual environment: source .venv/bin/activate"
echo "3. Start Docker services: docker-compose up -d"
echo "4. Run tests: pytest"
echo ""
echo "The environment is ready for development!"
