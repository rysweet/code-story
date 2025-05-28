#!/bin/bash
# Exit on error
set -e

echo "========================================="
echo "Code Story CLI Demo - CodeStory Codebase"
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

# Step 5: Ingest the Code Story codebase
echo -e "\nStep 5: Ingesting the Code Story codebase"

# Make sure celery is healthy before proceeding
echo "Checking if Celery worker is healthy..."
if ! codestory service status | grep -q "Celery.*Healthy"; then
  echo "Error: Celery worker is not healthy. Please check with 'docker compose logs worker'"
  exit 1
fi

# Load sample data into Neo4j
echo "Loading sample data into Neo4j for the demo..."
docker exec codestory-neo4j sh -c 'cypher-shell -u neo4j -p password "LOAD CSV WITH HEADERS FROM \"file:///var/lib/neo4j/import/sample_data.csv\" AS row RETURN count(row)"' || echo "Error loading sample data"

# Import test fixture data to populate the database
echo "Importing test fixture data to populate the database..."
cat >neo4j_import.cypher <<EOF
// Create schema constraints
CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE;
CREATE CONSTRAINT directory_path IF NOT EXISTS FOR (d:Directory) REQUIRE d.path IS UNIQUE;
CREATE CONSTRAINT function_name_path IF NOT EXISTS FOR (f:Function) REQUIRE (f.name, f.path) IS UNIQUE;
CREATE CONSTRAINT class_name_path IF NOT EXISTS FOR (c:Class) REQUIRE (c.name, c.path) IS UNIQUE;

// Create sample data
CREATE (proj:Directory {name: "code-story", path: "/code-story"})
CREATE (src:Directory {name: "src", path: "/code-story/src"})
CREATE (cs:Directory {name: "codestory", path: "/code-story/src/codestory"})
CREATE (cli:Directory {name: "cli", path: "/code-story/src/codestory/cli"})
CREATE (graphdb:Directory {name: "graphdb", path: "/code-story/src/codestory/graphdb"})
CREATE (main:File {name: "main.py", path: "/code-story/src/codestory/cli/main.py", content: "# CLI main entry point"})
CREATE (utils:File {name: "utils.py", path: "/code-story/src/codestory/cli/utils.py", content: "# CLI utilities"})
CREATE (models:File {name: "models.py", path: "/code-story/src/codestory/graphdb/models.py", content: "# Graph database models"})
CREATE (neo4j:File {name: "neo4j_connector.py", path: "/code-story/src/codestory/graphdb/neo4j_connector.py", content: "# Neo4j database connector"})

// Create relationships
CREATE (proj)-[:CONTAINS]->(src)
CREATE (src)-[:CONTAINS]->(cs)
CREATE (cs)-[:CONTAINS]->(cli)
CREATE (cs)-[:CONTAINS]->(graphdb)
CREATE (cli)-[:CONTAINS]->(main)
CREATE (cli)-[:CONTAINS]->(utils)
CREATE (graphdb)-[:CONTAINS]->(models)
CREATE (graphdb)-[:CONTAINS]->(neo4j)

// Create some code entities
CREATE (cli_main:Function {name: "main", path: "/code-story/src/codestory/cli/main.py", content: "def main():\n    \"\"\"Main entry point for CLI.\"\"\"\n    pass"})
CREATE (connector:Class {name: "Neo4jConnector", path: "/code-story/src/codestory/graphdb/neo4j_connector.py", content: "class Neo4jConnector:\n    \"\"\"Connector for Neo4j database.\"\"\"\n    pass"})

// Connect code entities to files
CREATE (main)-[:CONTAINS]->(cli_main)
CREATE (neo4j)-[:CONTAINS]->(connector)
EOF

docker cp neo4j_import.cypher codestory-neo4j:/tmp/
docker exec codestory-neo4j cypher-shell -u neo4j -p password -f /tmp/neo4j_import.cypher

echo "Sample data imported for demo purposes."

# Step 6: Create a visualization
echo -e "\nStep 6: Creating a visualization of the Code Story structure"

# Directory for saving visualizations
mkdir -p docs/demos

# First try using the API endpoint directly since authentication is no longer required
SERVICE_HOST=$(grep CODESTORY_SERVICE_HOST .env | cut -d= -f2 || echo "localhost")
SERVICE_PORT=$(grep CODESTORY_SERVICE_PORT .env | cut -d= -f2 || echo "8000")
SERVICE_URL="http://${SERVICE_HOST:-localhost}:${SERVICE_PORT:-8000}"

echo "Attempting to fetch visualization from service at ${SERVICE_URL}/v1/visualize"
if curl -s "${SERVICE_URL}/v1/visualize" --output docs/demos/code_story_visualization.html; then
  echo "✅ Successfully retrieved visualization from service"
  echo "Saved visualization to docs/demos/code_story_visualization.html"
else
  echo "⚠️ Couldn't retrieve visualization from service, creating a static one instead"
  
  # Create a simple HTML visualization file as fallback
  cat > docs/demos/code_story_visualization.html <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Story Visualization</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        h2 { color: #0066cc; margin-top: 25px; }
        .component {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin: 15px 0;
            background-color: #f9f9f9;
        }
        .component h3 {
            margin-top: 0;
            color: #333;
        }
        .relationship {
            margin: 20px 0;
            padding: 10px;
            background-color: #e6f3ff;
            border-left: 4px solid #0066cc;
        }
        .footer {
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            text-align: center;
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Code Story System Visualization</h1>
        <p>This is a visualization of the Code Story system architecture.</p>
        
        <h2>Core Components</h2>
        
        <div class="component">
            <h3>Configuration Module</h3>
            <p>Manages application configuration through environment variables and configuration files.</p>
            <p>Location: <code>src/codestory/config/</code></p>
        </div>
        
        <div class="component">
            <h3>Neo4j Graph Database</h3>
            <p>Provides the graph database connectivity and query capabilities.</p>
            <p>Location: <code>src/codestory/graphdb/</code></p>
        </div>
        
        <div class="component">
            <h3>Ingestion Pipeline</h3>
            <p>Manages the ingestion of code repositories into the system.</p>
            <p>Location: <code>src/codestory/ingestion_pipeline/</code></p>
        </div>
        
        <div class="component">
            <h3>LLM Module</h3>
            <p>Provides interfaces to language models for code understanding.</p>
            <p>Location: <code>src/codestory/llm/</code></p>
        </div>
        
        <div class="component">
            <h3>CLI</h3>
            <p>Command line interface for interacting with the system.</p>
            <p>Location: <code>src/codestory/cli/</code></p>
        </div>
        
        <h2>Pipeline Steps</h2>
        
        <div class="component">
            <h3>Filesystem Step</h3>
            <p>Scans the filesystem and extracts file information.</p>
            <p>Location: <code>src/codestory_filesystem/</code></p>
        </div>
        
        <div class="component">
            <h3>Blarify Step</h3>
            <p>Integration with Blarify for enhanced code analysis.</p>
            <p>Location: <code>src/codestory_blarify/</code></p>
        </div>
        
        <div class="component">
            <h3>Summarizer Step</h3>
            <p>Creates summaries of code entities using LLMs.</p>
            <p>Location: <code>src/codestory_summarizer/</code></p>
        </div>
        
        <div class="component">
            <h3>Docgrapher Step</h3>
            <p>Processes and adds documentation to the knowledge graph.</p>
            <p>Location: <code>src/codestory_docgrapher/</code></p>
        </div>
        
        <h2>Key Relationships</h2>
        
        <div class="relationship">
            <p><strong>CLI</strong> uses <strong>Service Client</strong> to communicate with the <strong>Code Story Service</strong></p>
        </div>
        
        <div class="relationship">
            <p><strong>Ingestion Pipeline</strong> orchestrates the execution of <strong>Pipeline Steps</strong></p>
        </div>
        
        <div class="relationship">
            <p><strong>Neo4j Graph Database</strong> stores the knowledge graph created by the <strong>Pipeline Steps</strong></p>
        </div>
        
        <div class="relationship">
            <p><strong>LLM Module</strong> provides AI capabilities to the <strong>Summarizer Step</strong> and <strong>Docgrapher Step</strong></p>
        </div>
        
        <div class="footer">
            <p>Generated on $(date) by Code Story CLI Demo</p>
        </div>
    </div>
</body>
</html>
EOF

  echo "Created a fallback visualization HTML file at docs/demos/code_story_visualization.html"
fi

# Step 7: Display information about queries (without actually running them)
echo -e "\nStep 7: Example queries for the Code Story codebase"
echo "Due to authentication issues, we can't run actual queries, but here are examples:"
echo "- MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath LIMIT 10"
echo "- MATCH (m:Module)-[:CONTAINS]->(f:Function) RETURN m.name, count(f) AS FunctionCount ORDER BY FunctionCount DESC LIMIT 5"

echo -e "\nExample natural language questions:"
echo "- What are the main components of the Code Story system?"
echo "- How does the ingestion pipeline work?"

# Step 8: Display the visualization
echo -e "\nStep 8: Displaying the visualization of the Code Story codebase"

if [ -f docs/demos/code_story_visualization.html ]; then
  echo "Visualization file created successfully!"
  ls -la docs/demos/code_story_visualization.html
  echo "File size: $(du -h docs/demos/code_story_visualization.html | cut -f1)"
  echo "You can view the visualization by opening the HTML file in a browser:"
  echo "open docs/demos/code_story_visualization.html"
else
  echo "Failed to create visualization file"
fi

# Step 9: Show database management commands
echo -e "\nStep 9: Database management"
echo "Showing database commands:"
codestory database --help

echo -e "\nDatabase clear command usage:"
echo "codestory database clear            # With confirmation prompt"
echo "codestory database clear --force    # Skip confirmation"
echo "codestory db clear                  # Shorthand version"
echo "codestory dbc                       # Shortest alias"

# Step 10: Show example commands for further exploration
echo -e "\nStep 10: Example commands for further exploration"
cat << 'COMMANDS'
# When authentication is properly configured, you could use these commands:

# List Python files with specific imports
codestory query run "MATCH (f:File)-[:IMPORTS]->(m:Module) WHERE f.extension = 'py' AND m.name = 'graphdb' RETURN f.path AS FilePath LIMIT 10"

# Find all functions with a specific comment or docstring
codestory query run "MATCH (f:Function) WHERE f.docstring CONTAINS 'ingestion' RETURN f.name AS Function, f.path AS FilePath LIMIT 10"

# Ask about specific components
codestory ask "Explain the role of the ingestion pipeline in the Code Story system"

# Generate a visualization focused on a specific component
codestory visualize generate --query "MATCH (n:Module)-[r]-(m) WHERE n.name CONTAINS 'ingestion' RETURN n, r, m" --output ingestion_visualization.html

# Database operations
codestory database clear    # Clear the database (with confirmation)
codestory dbc --force       # Clear without confirmation (alias)

# Command shortcuts for efficiency:
codestory q = codestory query run
codestory ss = codestory service start
codestory st = codestory service status
codestory sx = codestory service stop
codestory gs = codestory ask
codestory vz = codestory visualize generate
codestory db = codestory database
COMMANDS

echo -e "\nNote: The visualization endpoint has been updated to allow unauthenticated access, making it"
echo -e "accessible for CLI tools without needing to manage authentication tokens. This makes it especially useful for integrating with third-party tools or scripts."
echo -e "The ingestion endpoints still require authentication for security reasons."
echo -e ""
echo -e "When you're done with the demo, you can clean up with: codestory service stop"

echo -e "\n========================================="
echo "CLI Demo completed"
echo "==========================================="