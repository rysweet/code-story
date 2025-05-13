#!/bin/bash
# Exit on error
set -e

echo "========================================="
echo "Running Code Story CLI Demo"
echo "========================================="

# Step 1: Verify CLI installation
echo "Step 1: Verifying CLI installation"
codestory --version

# Step 2: Check current configuration
echo -e "\nStep 2: Checking current configuration"
if codestory config show; then
  echo "Configuration is valid"
else
  echo "Service not running - this is expected"
fi

# Step 3: Start the service and ensure it's running properly
echo -e "\nStep 3: Starting the service"

# Force a full restart of the service
echo "Stopping any running services..."
docker compose down -v || true
sleep 5

echo "Starting services..."
codestory service start --detach
echo "Waiting for service to initialize..."

# Wait for the service to be fully running
max_attempts=20
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

# Step 4: Check service status
echo -e "\nStep 4: Checking service status"
codestory service status || echo "Service status check failed - this is expected if service isn't fully running"

# Step 5: Explore commands
echo -e "\nStep 5: Exploring available commands"
codestory --help

# Step 6: Check visualization help
echo -e "\nStep 6: Checking visualization help"
codestory visualize help

# Step 7: Create directory for visualization output
echo -e "\nStep 7: Preparing for visualization"
mkdir -p docs/demos
echo "We will generate the visualization after data ingestion."

# Step 8: Ingest code repository
echo -e "\nStep 8: Ingesting code repository"

# Try multiple times if needed - sometimes first attempt fails during demo
for i in {1..3}; do
  echo "Ingestion attempt $i..."
  if codestory ingest start . --no-progress; then
    echo "Ingestion started successfully!"
    sleep 5
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

# Check ingestion status
echo -e "\nStep 9: Checking ingestion status"
job_id=$(codestory ingest jobs | grep -o '[0-9a-f]\{8\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{12\}' | head -1)
if [ -n "$job_id" ]; then
  echo "Found job ID: $job_id"
  codestory ingest status $job_id
  
  # Wait for ingestion to complete or for a reasonable time
  echo "Waiting for ingestion to make progress (up to 60 seconds)..."
  for i in {1..12}; do
    sleep 5
    status=$(codestory ingest status $job_id | grep -o 'Status.*' | head -1)
    progress=$(codestory ingest status $job_id | grep -o 'Progress.*%' | head -1)
    echo "$status - $progress"
    
    # If completed or failed, break
    if [[ $status == *"Completed"* || $status == *"Failed"* ]]; then
      break
    fi
  done
  
  echo -e "\nStep 10: Running a query"
  codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath LIMIT 10" || echo "Query failed - may need more time for data to be available"
  
  echo -e "\nStep 11: Asking a question about the code"
  codestory ask "What are the main components of the Code Story system?" || echo "Question failed - may need more time for data to be indexed"
else
  echo "No job ID found. Ingestion may not have started properly."
fi

# Step 12: Generate visualization again now that we have data
echo -e "\nStep 12: Generating visualization with ingested data"
codestory visualize generate --output docs/demos/visualization.html || echo "Visualization generation failed"
if [ -f docs/demos/visualization.html ]; then
  echo "Visualization generated successfully with ingested data!"
  ls -la docs/demos/visualization.html
  echo "File size: $(du -h docs/demos/visualization.html | cut -f1)"
  file_size=$(stat -f%z docs/demos/visualization.html)
  if [ "$file_size" -gt 1000 ]; then
    echo "Visualization seems valid (file size > 1KB)"
  else
    echo "Warning: Visualization file seems too small, may not contain graph data"
  fi
else
  echo "Failed to generate visualization"
fi

# Step 13: Show example commands for reference
echo -e "\nStep 13: Example commands for reference"
cat << 'COMMANDS'
# List all Python files
codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath LIMIT 10"

# Ask about the code structure
codestory ask "What are the main components of the Code Story system?"

# Generate a visualization
codestory visualize generate --output visualization.html

# Open a visualization
codestory visualize open visualization.html

# Command aliases for efficiency:
codestory q = codestory query run
codestory ss = codestory service start
codestory st = codestory service status
codestory sx = codestory service stop
codestory gs = codestory ask
codestory vz = codestory visualize generate
COMMANDS

# Step 14: Clean up
echo -e "\nStep 14: Cleaning up"
echo "Attempting to clear the database..."
codestory query run "MATCH (n) DETACH DELETE n" || echo "Database clear failed - this is expected if service isn't running"

echo "Stopping the service..."
codestory service stop || echo "Service stop failed"

echo -e "\n========================================="
echo "CLI Demo completed"
echo "========================================="
