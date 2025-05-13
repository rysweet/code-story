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

# Step 2: Check current configuration
echo -e "\nStep 2: Checking current configuration"
if codestory config show 2>/dev/null; then
  echo "Configuration is valid"
else
  echo "Service not running or configuration not yet available - this is expected"
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
      echo "WARNING: Service did not start properly after $max_attempts attempts."
      echo "Continuing with the demo, but some steps may fail."
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

# Step 8: Ingest code repository
echo -e "\nStep 8: Ingesting sample project"

# Try multiple times if needed - sometimes first attempt fails
for i in {1..3}; do
  echo "Ingestion attempt $i..."
  if codestory ingest "$DEMO_DIR" --name "CLI Demo Project" --wait; then
    echo "Ingestion started and completed successfully!"
    sleep 2
    break
  else
    echo "Ingestion attempt $i failed. Retrying..."
    # If we've tried 3 times, exit with error
    if [ $i -eq 3 ]; then
      echo "Error: Could not start ingestion after 3 attempts."
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