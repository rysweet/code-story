# CLI Demo Task Breakdown - Detailed Execution Plan

This document provides specific commands, expected outputs, and troubleshooting steps for each task in the CLI demo testing plan.

## Phase 1: Infrastructure Setup

### Task 1.1: Environment Verification

#### Commands to Execute:
```bash
# Verify Docker installation
docker --version
docker compose version
docker ps

# Verify project structure
ls -la docker-compose.yml Dockerfile.service Dockerfile.worker
ls -la .env.template

# Check if Code Story is installed
which codestory || echo "CLI not in PATH"
python -c "import codestory; print('Package installed')" 2>/dev/null || echo "Package not installed"
```

#### Expected Results:
- Docker version 20.0+ and compose version 2.0+
- All Docker configuration files present
- Template environment file exists
- Either CLI in PATH or Python package available

#### Common Issues:
- **Docker not running**: `sudo systemctl start docker` or start Docker Desktop
- **Missing files**: Clone repository or check working directory
- **Package not installed**: Run `pip install -e .` from project root

### Task 1.2: Configuration Setup

#### Commands to Execute:
```bash
# Create configuration from template
cp .env.template .env

# Check required environment variables
grep -E "^(NEO4J|REDIS|SERVICE)__" .env.template

# Validate configuration format
cat .env | grep -v "^#" | grep "="

# For Docker environment (recommended)
sed -i 's/^# NEO4J__URI=bolt:\/\/neo4j:7687/NEO4J__URI=bolt:\/\/neo4j:7687/' .env
sed -i 's/^NEO4J__URI=bolt:\/\/localhost:7687/# NEO4J__URI=bolt:\/\/localhost:7687/' .env
sed -i 's/^# REDIS__URI=redis:\/\/redis:6379/REDIS__URI=redis:\/\/redis:6379/' .env
sed -i 's/^REDIS__URI=redis:\/\/localhost:6379/# REDIS__URI=redis:\/\/localhost:6379/' .env
```

#### Expected Results:
- `.env` file created with proper settings
- Neo4j URI pointing to `bolt://neo4j:7687` for Docker
- Redis URI pointing to `redis://redis:6379` for Docker
- All required variables uncommented

#### Common Issues:
- **Template not found**: Ensure you're in project root directory
- **Permission denied**: Check file permissions: `chmod 644 .env`

## Phase 2: Service Infrastructure

### Task 2.1: Docker Container Health

#### Commands to Execute:
```bash
# Stop any existing containers
docker compose down -v

# Start core infrastructure services
docker compose up -d neo4j redis

# Wait for services to initialize
sleep 10

# Check container status
docker compose ps
docker compose logs neo4j --tail 10
docker compose logs redis --tail 10

# Test Neo4j connectivity
docker exec codestory-neo4j cypher-shell -u neo4j -p password "RETURN 'Connected' as status"

# Test Redis connectivity
docker exec codestory-redis redis-cli ping
```

#### Expected Results:
- Neo4j and Redis containers in "running" state
- Neo4j logs show "Started" message
- Redis logs show "Ready to accept connections"
- Cypher query returns "Connected"
- Redis ping returns "PONG"

#### Common Issues:
- **Port conflicts**: Change ports in [`docker-compose.yml`](docker-compose.yml)
- **Neo4j startup slow**: Wait longer, check with `docker compose logs neo4j`
- **Redis connection refused**: Ensure Redis container is healthy

### Task 2.2: Service Container Health

#### Commands to Execute:
```bash
# Build and start main service
docker compose build service
docker compose up -d service

# Build and start worker
docker compose build worker  
docker compose up -d worker

# Check all containers
docker compose ps

# Verify service logs
docker compose logs service --tail 20
docker compose logs worker --tail 20
```

#### Expected Results:
- All containers show "running" status
- Service logs show FastAPI startup on port 8000
- Worker logs show Celery worker ready
- No error messages in logs

#### Common Issues:
- **Build failures**: Check Dockerfile syntax, ensure dependencies available
- **Service won't start**: Check .env configuration, verify Neo4j/Redis connectivity
- **Worker startup issues**: Verify Celery configuration and Redis connection

### Task 2.3: Service Health Verification

#### Commands to Execute:
```bash
# Test service endpoint
curl -f http://localhost:8000/health

# Test service with timeout
curl -f --connect-timeout 10 http://localhost:8000/health

# Check if all endpoints are available
curl -f http://localhost:8000/docs 2>/dev/null && echo "API docs available"
```

#### Expected Results:
- Health endpoint returns 200 status
- Health response contains service status information
- API documentation accessible (indicates service fully loaded)

#### Common Issues:
- **Connection refused**: Service not started or wrong port
- **Timeout**: Service starting slowly, wait longer
- **500 errors**: Check service logs for internal errors

## Phase 3: CLI Installation & Basic Commands

### Task 3.1: CLI Installation Verification

#### Commands to Execute:
```bash
# Test direct CLI command
codestory --version

# Test Python module fallback
python -m codestory.cli.main --version

# Test package installation
pip show codestory 2>/dev/null || echo "Package not installed via pip"

# Test development installation
python -c "import sys; print('\n'.join(sys.path))" | grep -i codestory || echo "Not in development mode"
```

#### Expected Results:
- Either method returns version string like "codestory, version 0.1.0"
- Consistent version between both methods
- Package shows as installed or development path visible

#### Common Issues:
- **Command not found**: CLI not in PATH, use Python module method
- **Import errors**: Install dependencies: `pip install -e .`
- **Version mismatch**: Reinstall package: `pip install -e . --force-reinstall`

### Task 3.2: Help System

#### Commands to Execute:
```bash
# Test main help
codestory --help

# Test subcommand help
codestory service --help
codestory ingest --help
codestory query --help
codestory visualize --help

# Test special help content
codestory visualize help
```

#### Expected Results:
- Main help shows command list and options
- Subcommand help shows specific options
- Visualize help shows detailed usage guide
- No error messages or missing content

#### Common Issues:
- **Truncated output**: Terminal width issue, try `codestory --help | less`
- **Missing help**: Package installation incomplete

### Task 3.3: Service Management Commands

#### Commands to Execute:
```bash
# Test service start (should already be running)
codestory service start --detach

# Wait for services to be ready
max_attempts=30
for i in $(seq 1 $max_attempts); do
  if codestory service status 2>/dev/null; then
    echo "Service ready after $i attempts"
    break
  fi
  echo "Waiting... ($i/$max_attempts)"
  sleep 5
done

# Test service status
codestory service status

# Test service restart
codestory service restart
```

#### Expected Results:
- Service start command completes without errors
- Service status shows all components healthy
- Status table includes Neo4j, Celery, Redis, OpenAI status
- Restart command works without issues

#### Common Issues:
- **Service not ready**: Wait longer, services take time to initialize
- **Connection errors**: Check Docker containers are running
- **Status shows unhealthy**: Check individual service logs

### Task 3.4: Configuration Commands

#### Commands to Execute:
```bash
# Test configuration display
codestory config show

# Test configuration shortcuts
codestory cfs
codestory cfg show

# Test configuration modification (optional)
# codestory config set test_key=test_value
```

#### Expected Results:
- Configuration displayed in readable format
- All shortcuts work identically
- Current configuration matches .env file settings

#### Common Issues:
- **Service not running**: Start service first
- **Permission errors**: Check .env file permissions
- **Missing config**: Verify .env file exists and is valid

## Phase 4: Ingestion Pipeline

### Task 4.1: Sample Project Creation

#### Commands to Execute:
```bash
# Create sample project directory
DEMO_DIR="/tmp/codestory_cli_demo"
mkdir -p "$DEMO_DIR"

# Create Python file
cat > "$DEMO_DIR/hello.py" <<'EOF'
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

# Create README file
cat > "$DEMO_DIR/README.md" <<'EOF'
# Demo App

This is a simple demo app that demonstrates greeting functionality.

## Usage

Run the app with:

```bash
python hello.py
```
EOF

# Verify files created
ls -la "$DEMO_DIR"
cat "$DEMO_DIR/hello.py"
```

#### Expected Results:
- Directory created successfully
- Both files contain expected content
- Files have correct permissions

### Task 4.2: Celery Worker Health Verification

#### Commands to Execute:
```bash
# Check worker status
codestory service status | grep -i celery

# Check worker logs
docker compose logs worker --tail 10

# Test worker connectivity
docker exec codestory-worker celery -A src.codestory.ingestion_pipeline.celery_app inspect ping
```

#### Expected Results:
- Service status shows "Celery: Healthy"
- Worker logs show successful startup
- Ping command returns worker response

#### Common Issues:
- **Worker not healthy**: Check Redis connection, restart worker
- **Import errors**: Verify Python path and dependencies in worker container

### Task 4.3: Repository Ingestion

#### Commands to Execute:
```bash
# Test ingestion with progress
codestory ingest start "$DEMO_DIR"

# Test ingestion without progress (alternative)
# codestory ingest start "$DEMO_DIR" --no-progress

# Monitor ingestion progress
codestory ingest jobs
codestory ingest status
```

#### Expected Results:
- Ingestion starts successfully
- Progress updates appear (if using Redis progress tracking)
- Job shows in job list
- Ingestion completes without errors

#### Common Issues:
- **Ingestion fails to start**: Check Celery worker health
- **Progress not showing**: Redis connection issue, fallback to polling
- **Job stuck**: Check worker logs for errors

### Task 4.4: Ingestion Job Management

#### Commands to Execute:
```bash
# List all jobs
codestory ingest jobs
codestory ij  # shortcut

# Check specific job status
codestory ingest status

# If needed, stop a job
# JOB_ID=$(codestory ingest jobs | grep -o '[0-9a-f-]*' | head -1)
# codestory ingest stop $JOB_ID
```

#### Expected Results:
- Jobs listed with IDs and status
- Status command shows current job progress
- Stop command works if executed

#### Common Issues:
- **No jobs found**: Ingestion may not have started successfully
- **Job status unclear**: Check service logs for more details

## Phase 5: Core Query Features

### Task 5.1: Cypher Queries

#### Commands to Execute:
```bash
# Basic file query
codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath LIMIT 5"

# Count files
codestory query run "MATCH (f:File) RETURN count(f) AS FileCount"

# Query with shortcuts
codestory q "MATCH (f:File) RETURN f.name AS FileName LIMIT 3"

# Function query (if available)
codestory query run "MATCH (func:Function) RETURN func.name AS FunctionName LIMIT 5"
```

#### Expected Results:
- Queries return results without errors
- Python files from demo project appear in results
- File count matches expected number
- Functions like "greeting" and "main" appear if parsed

#### Common Issues:
- **No results**: Ingestion may not be complete or failed
- **Query syntax errors**: Check Cypher syntax
- **Connection timeout**: Service may be overloaded

### Task 5.2: Natural Language Queries

#### Commands to Execute:
```bash
# Ask about functionality
codestory ask "What does the greeting function do?"

# Ask about project structure
codestory ask "What Python files are in this project?"

# Test shortcuts
codestory gs "Describe the main function"

# Ask about relationships
codestory ask "What functions are defined in hello.py?"
```

#### Expected Results:
- AI generates relevant responses about the code
- Responses reference actual code content
- Questions about specific functions return accurate information

#### Common Issues:
- **OpenAI errors**: Check API key configuration
- **Generic responses**: May indicate ingestion didn't capture code details
- **No response**: Service connection or AI service issues

## Phase 6: Visualization Features

### Task 6.1: Visualization Generation

#### Commands to Execute:
```bash
# Create output directory
mkdir -p docs/demos

# Generate visualization
codestory visualize generate --output docs/demos/test_viz.html

# Test shortcut
codestory vz --output docs/demos/test_viz2.html

# Verify files created
ls -la docs/demos/test_viz*.html
```

#### Expected Results:
- HTML files created successfully
- Files contain valid HTML with visualization code
- File sizes reasonable (not empty, not excessively large)

#### Common Issues:
- **File not created**: Check output directory permissions
- **Empty file**: Query may have returned no data
- **Large file**: May indicate performance issue

### Task 6.2: Direct API Access

#### Commands to Execute:
```bash
# Test API endpoint directly
curl -f http://localhost:8000/v1/visualize --output docs/demos/api_viz.html

# Verify content
file docs/demos/api_viz.html
head -20 docs/demos/api_viz.html

# Check file size
ls -la docs/demos/api_viz.html
```

#### Expected Results:
- File downloads successfully
- File identified as HTML
- Content includes visualization elements
- File size similar to CLI-generated version

#### Common Issues:
- **Connection refused**: Service not running on expected port
- **404 error**: Endpoint not available or misconfigured
- **Empty response**: Database may be empty

## Phase 7: Database Management

### Task 7.1: Database Commands

#### Commands to Execute:
```bash
# Test database help
codestory database --help
codestory db --help  # shortcut

# Test clear command with dry run (don't actually clear)
echo "n" | codestory database clear

# In test environment only:
# codestory database clear --force
# codestory dbc --force  # shortcut
```

#### Expected Results:
- Help shows available database commands
- Clear command shows confirmation prompt
- Force option skips confirmation (use carefully)

#### Common Issues:
- **Permission denied**: Database operation may require special permissions
- **Operation failed**: Database may be in use

## Phase 8: End-to-End Demo Scripts

### Task 8.1: Sample Project Demo Script

#### Commands to Execute:
```bash
# Make script executable
chmod +x scripts/run_cli_demo.sh

# Run the complete demo
./scripts/run_cli_demo.sh

# Check exit code
echo "Demo script exit code: $?"
```

#### Expected Results:
- Script runs without errors
- All demo steps complete successfully
- Visualization file created
- Exit code 0 (success)

#### Common Issues:
- **Script fails early**: Check infrastructure setup
- **Permission denied**: Ensure script is executable
- **Partial completion**: Check logs for specific failure points

### Task 8.2: CodeStory Codebase Demo Script

#### Commands to Execute:
```bash
# Make script executable
chmod +x scripts/run_codestory_demo.sh

# Run the larger demo
./scripts/run_codestory_demo.sh

# Check results
ls -la docs/demos/code_story_visualization.html
```

#### Expected Results:
- Script completes successfully
- Larger visualization created
- Sample data loaded into database

#### Common Issues:
- **Longer runtime**: This demo processes more data
- **Memory usage**: May require more system resources

## Troubleshooting Commands

### General Debugging

```bash
# Check all container status
docker compose ps

# View recent logs from all services
docker compose logs --tail 50

# Check service health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Verify environment variables
env | grep -E "(NEO4J|REDIS|SERVICE|OPENAI)"

# Test database connectivity directly
docker exec codestory-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"

# Check CLI installation
pip show codestory
python -c "import codestory; print(codestory.__file__)"
```

### Common Recovery Procedures

```bash
# Complete restart
docker compose down -v
docker compose up -d

# Rebuild containers
docker compose build --no-cache
docker compose up -d

# Clear and restart database
docker compose down -v
docker volume rm codestory_neo4j_data codestory_redis_data 2>/dev/null || true
docker compose up -d

# Reinstall CLI
pip uninstall codestory -y
pip install -e .
```

## Success Validation Checklist

- [ ] All containers running and healthy
- [ ] CLI commands respond without errors
- [ ] Ingestion completes successfully
- [ ] Queries return expected results
- [ ] Visualizations generate properly
- [ ] Demo scripts run to completion
- [ ] Error messages are helpful and actionable
- [ ] Documentation matches actual behavior