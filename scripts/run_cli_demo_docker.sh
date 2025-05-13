#!/bin/bash
set -e

# CLI Demo Script using Docker Compose
echo "================================================"
echo "Code Story CLI Demo (Docker Compose Version)"
echo "================================================"

# Ensure we're in the project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Step 1: Start the services
echo "1. Starting Code Story services..."
docker-compose down -v
docker-compose up -d

# Wait for service to be ready
echo "   Waiting for services to be ready..."
MAX_RETRIES=30
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health >/dev/null || curl -s http://localhost:8000/v1/health >/dev/null; then
        echo "   ✅ Services are running!"
        break
    fi
    echo "   Waiting for services to start... ($(($COUNT+1))/$MAX_RETRIES)"
    sleep 5
    COUNT=$((COUNT+1))
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Services failed to start in time"
    docker-compose logs service
    docker-compose logs worker
    exit 1
fi

# Step 2: Run the CLI demo
echo
echo "2. Using the CLI to interact with the service..."
echo

# Create a sample project for ingestion
DEMO_DIR="/tmp/codestory_cli_demo"
mkdir -p "$DEMO_DIR"
cat > "$DEMO_DIR/hello.py" <<EOF
def greeting(name):
    """Return a personalized greeting."""
    return f"Hello, {name}!"

def main():
    """Main function that demonstrates the greeting."""
    names = ["Alice", "Bob", "Charlie"]
    for name in names:
        print(greeting(name))

if __name__ == "__main__":
    main()
EOF

cat > "$DEMO_DIR/README.md" <<EOF
# Demo App

This is a simple demo app that demonstrates greeting functionality.

## Usage

Run the app with:

\`\`\`
python hello.py
\`\`\`
EOF

echo "ℹ️ Created sample project at $DEMO_DIR"
echo

# Create CLI config for local Docker services
cat > "$PROJECT_ROOT/.codestory.cli.toml" <<EOF
[general]
app_name = "code-story"
version = "0.1.0"
environment = "development"

[neo4j]
uri = "bolt://localhost:7689"
username = "neo4j" 
password = "password"
database = "neo4j"

[service]
host = "localhost"
port = 8000

[redis]
uri = "redis://localhost:6389"
EOF

# Demonstrate CLI commands
echo "ℹ️ CLI Commands: Checking service status..."
CODESTORY_CONFIG_FILE="$PROJECT_ROOT/.codestory.cli.toml" python -m codestory.cli.main service status

echo -e "\nℹ️ CLI Commands: Ingesting code..."
CODESTORY_CONFIG_FILE="$PROJECT_ROOT/.codestory.cli.toml" python -m codestory.cli.main ingest "$DEMO_DIR" --name "CLI Demo Project" --wait

echo -e "\nℹ️ CLI Commands: Querying the graph..."
CODESTORY_CONFIG_FILE="$PROJECT_ROOT/.codestory.cli.toml" python -m codestory.cli.main query "What does the greeting function do?"

echo -e "\nℹ️ CLI Commands: Visualizing the ingested code..."
CODESTORY_CONFIG_FILE="$PROJECT_ROOT/.codestory.cli.toml" python -m codestory.cli.main visualize

echo -e "\n3. Demo completed! You can continue exploring using the CLI."
echo "   To stop the services, run: docker-compose down"