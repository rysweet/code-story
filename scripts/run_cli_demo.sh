#!/bin/bash
# Exit on error
set -e

echo "========================================="
echo "Code Story CLI Demo"
echo "========================================="

# Ensure we're in the project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Step 1: Verify CLI installation
echo "Step 1: Verifying CLI installation"
codestory --version || python -m codestory.cli.main --version

# Step 2: Setup and check configuration
echo -e "\nStep 2: Setting up and checking configuration"

# Create .env file for the demo if needed
echo -e "Checking configuration setup..."
TEMPLATE_ENV=".env.template"
ENV_FILE=".env"

if [ -f "$TEMPLATE_ENV" ]; then
  # Show the required configuration
  echo -e "A working configuration requires these essential settings:"
  echo -e "  NEO4J__URI=bolt://localhost:7687 (or bolt://neo4j:7687 for Docker)"
  echo -e "  NEO4J__USERNAME=neo4j"
  echo -e "  NEO4J__PASSWORD=password"
  echo -e "  REDIS__URI=redis://localhost:6379 (or redis://redis:6379 for Docker)"
  echo -e "  SERVICE__HOST=localhost (or 0.0.0.0 for Docker)"
  echo -e "  SERVICE__PORT=8000"
  
  # Copy template if needed
  if [ ! -f "$ENV_FILE" ]; then
    echo -e "\nCreating .env file from template..."
    # Extract just the required settings from the template
    sed -n '/^# REQUIRED SETTINGS/,/^# OPTIONAL SETTINGS/p' "$TEMPLATE_ENV" | \
    grep -v '^#===' | \
    grep -v "^# OPTIONAL" > "$ENV_FILE"
    
    # For Docker environment, uncomment Docker settings
    if [ "$USE_DOCKER" = "true" ] || [ -f "docker-compose.yml" ]; then
      echo -e "Configuring for Docker environment..."
      sed -i.bak 's/^# NEO4J__URI=bolt:\/\/neo4j:7687/NEO4J__URI=bolt:\/\/neo4j:7687/' "$ENV_FILE"
      sed -i.bak 's/^NEO4J__URI=bolt:\/\/localhost:7687/# NEO4J__URI=bolt:\/\/localhost:7687/' "$ENV_FILE"
      sed -i.bak 's/^# REDIS__URI=redis:\/\/redis:6379/REDIS__URI=redis:\/\/redis:6379/' "$ENV_FILE"
      sed -i.bak 's/^REDIS__URI=redis:\/\/localhost:6379/# REDIS__URI=redis:\/\/localhost:6379/' "$ENV_FILE"
      sed -i.bak 's/^# SERVICE__HOST=0.0.0.0/SERVICE__HOST=0.0.0.0/' "$ENV_FILE"
      sed -i.bak 's/^SERVICE__HOST=localhost/# SERVICE__HOST=localhost/' "$ENV_FILE"
      rm -f "$ENV_FILE.bak"
    fi
    
    echo -e "✅ Created $ENV_FILE with required configuration"
  else
    echo -e "✅ Using existing $ENV_FILE file"
  fi
else
  echo -e "⚠️ Template file not found. Using existing configuration."
fi

# Show how to access configuration settings
echo -e "\nTo view or modify configuration, you can use:"
echo "  codestory config show          # View all settings"
echo "  codestory config set key=value # Update a setting"
echo "  vim .env                       # Edit bootstrap settings directly"

# Check the configuration
echo -e "\nChecking current configuration:"
if codestory config show 2>/dev/null; then
  echo "✅ Configuration is valid"
else
  echo "⚠️ Service not running or configuration not yet available - this is expected"
fi

# Step 3: Start the service and ensure it's running properly
echo -e "\nStep 3: Starting the service"

# Force a full restart of the service to ensure clean state
echo "Stopping any running services..."
docker compose down -v || true
sleep 2

echo "Starting services..."
codestory service start --detach
echo "Waiting for service to initialize..."

# Wait for the service to be fully running
max_attempts=30
for i in $(seq 1 $max_attempts); do
  echo "Checking service status (attempt $i of $max_attempts)..."
  if codestory service status 2>/dev/null; then
    echo "Service is running!"
    break
  else
    echo "Service not ready yet. Waiting..."
    sleep 5
    if [ $i -eq $max_attempts ]; then
      echo "ERROR: Service did not start properly after $max_attempts attempts."
      echo "Please check the service logs with 'docker compose logs' and ensure all components are running."
      exit 1
    fi
  fi
done

# Step 4: Check service status with more details
echo -e "\nStep 4: Checking service status"
codestory service status || echo "Service status check failed - this is expected if service isn't fully running"

# Step 5: Explore commands
echo -e "\nStep 5: Exploring available commands"
codestory --help

# Step 6: Check visualization help
echo -e "\nStep 6: Checking visualization help"
codestory visualize help

# Step 7: Create a sample project for demonstration
echo -e "\nStep 7: Preparing a sample project for ingestion"
DEMO_DIR="/tmp/codestory_cli_demo"
mkdir -p "$DEMO_DIR"

# Create a simple Python file
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

# Create a README file
cat > "$DEMO_DIR/README.md" <<EOF
# Demo App

This is a simple demo app that demonstrates greeting functionality.

## Usage

Run the app with:

\`\`\`
python hello.py
\`\`\`
EOF

echo "Created sample project at $DEMO_DIR"

# Make sure celery is healthy before proceeding
echo "Checking if Celery worker is healthy..."
if ! codestory service status | grep -q "Celery.*Healthy"; then
  echo "Error: Celery worker is not healthy. Please check with 'docker compose logs worker'"
  exit 1
fi

# Step 8: Ingest code repository
echo -e "\nStep 8: Ingesting sample project"

# Try multiple times if needed - sometimes first attempt fails
for i in {1..3}; do
  echo "Ingestion attempt $i..."
  if codestory ingest start "$DEMO_DIR" --wait; then
    echo "Ingestion started and completed successfully!"
    sleep 2
    break
  else
    echo "Ingestion attempt $i failed. Retrying..."
    # If we've tried 3 times, exit with error
    if [ $i -eq 3 ]; then
      echo "Error: Could not start ingestion after 3 attempts."
      echo "Please check if the Celery worker is running with 'docker compose logs worker'"
      exit 1
    fi
    sleep 5
  fi
done

# Step 9: Running queries on the ingested code
echo -e "\nStep 9: Running queries on the ingested code"
echo "Executing a Cypher query to find Python files:"
codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath" || echo "Query failed - may need more time for data to be available"

echo -e "\nStep 10: Asking a natural language question about the code:"
codestory ask "What does the greeting function do in the hello.py file?" || echo "Question failed - may need more time for data to be indexed"

# Step 11: Generate visualization with ingested data
echo -e "\nStep 11: Generating visualization with ingested data"
mkdir -p docs/demos
codestory visualize generate --output docs/demos/visualization.html || echo "Visualization generation failed"

if [ -f docs/demos/visualization.html ]; then
  echo "Visualization generated successfully!"
  ls -la docs/demos/visualization.html
  echo "File size: $(du -h docs/demos/visualization.html | cut -f1)"
else
  echo "Failed to generate visualization"
fi

# Step 12: Show example commands for further exploration
echo -e "\nStep 12: Example commands for further exploration"
cat << 'COMMANDS'
# List all Python files
codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath"

# Ask about specific functions
codestory ask "What does the greeting function do in hello.py?"

# Generate a visualization
codestory visualize generate --output visualization.html

# Open a visualization
codestory visualize open visualization.html

# Command shortcuts for efficiency:
codestory q = codestory query run
codestory ss = codestory service start
codestory st = codestory service status
codestory sx = codestory service stop
codestory gs = codestory ask
codestory vz = codestory visualize generate
COMMANDS

# Step 13: Clean up
echo -e "\nStep 13: Cleaning up"
echo "Attempting to clear the database..."
codestory query run "MATCH (n) DETACH DELETE n" || echo "Database clear failed - this is expected if service isn't running"

echo "Stopping the service..."
codestory service stop || echo "Service stop failed"

echo -e "\n========================================="
echo "CLI Demo completed"
echo "========================================="