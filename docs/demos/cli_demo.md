# CLI Demo

This demonstration shows how to use the Code Story command line interface to ingest, analyze, and visualize code repositories.

## Installation

First, let's install the Code Story CLI:

```bash
# Clone the repository
git clone https://github.com/rysweet/code-story.git
cd code-story

# Install the package
pip install -e .
```

After installation, verify the CLI is working:

```bash
codestory --version
```

Expected output:
```
codestory, version 0.1.0
```

## Configuration

The CLI uses environment variables and a configuration file. The default configuration file is `.codestory.toml` in your project directory.

For connecting to Neo4j (which runs in Docker), ensure your configuration file has the correct URI:

```toml
[neo4j]
uri = "bolt://localhost:7689"
username = "neo4j"
database = "neo4j"
```

You can check your current configuration settings:

```bash
codestory config show
```

Note: This requires the service to be running.

## Service Management

Before using the CLI for ingestion or queries, you need to start the Code Story services:

```bash
# Start the services in the background and wait for initialization
codestory service start --detach --wait

# Or, to start interactively
codestory service start

# Restart services
codestory service restart
```

This command uses Docker Compose to start the required services, including Neo4j, Redis, and Celery workers. You can verify the service status:

```bash
codestory service status
```

Example output:
```
                                 Service Status                                 
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component       ┃ Status   ┃ Details                                         ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Service Overall │ Healthy  │ 2025-05-13T15:43:42Z                            │
│ Neo4j           │ Healthy  │ Connected to bolt://localhost:7687              │
│ Celery          │ Healthy  │ Workers: 2, Tasks: 12                           │
│ Redis           │ Healthy  │ Connection: redis://localhost:6379/0            │
│ Openai          │ Healthy  │ OpenAI API connection successful                │
└─────────────────┴──────────┴─────────────────────────────────────────────────┘
Service is running. Version: 0.1.0, Uptime: 324 seconds
```

## Available Commands

The CLI offers several commands to interact with the Code Story system:

### Help and Information

```bash
# Show all available commands
codestory --help
```

Output:
```
Usage: codestory [OPTIONS] COMMAND [ARGS]...

  [bold]Code Story[/bold] - A tool for exploring and documenting codebases.

Options:
  --version           Show the version and exit.
  --service-url TEXT  URL of the Code Story service.
  --api-key TEXT      API key for authentication.
  --help              Show this message and exit.

Commands:
  ask        Ask a natural language question about the codebase.
  cfg        Manage Code Story configuration.
  cfs        Show current configuration.
  config     Manage Code Story configuration.
  gs         Ask a natural language question about the codebase.
  ij         List all ingestion jobs.
  in         Ingest a repository into Code Story.
  ingest     Ingest a repository into Code Story.
  is         Stop an ingestion job.
  q          Execute a Cypher query or MCP tool call.
  query      Execute queries and explore the Code Story graph.
  service    Manage the Code Story service.
  ss         Start the Code Story service.
  st         Show the status of the Code Story service.
  sx         Stop the Code Story service.
  ui         Open the Code Story GUI in a browser.
  visualize  Generate and manage visualizations of the Code Story graph.
  vz         Generate a visualization of the Code Story graph.
```

You can get detailed help for any command:

```bash
# Get help for a specific command
codestory visualize help
```

Output from `visualize help`:
```
# Code Story Graph Visualization

The visualization feature allows you to create interactive, browser-based visualizations
of your code graph. These visualizations help you understand the structure and relationships
in your codebase.

## Visualization Types

- **Force** (default): A force-directed graph where nodes repel each other and edges act like springs.
  Best for showing relationships between components.

- **Hierarchy**: A tree-like visualization showing inheritance and containment relationships.
  Useful for understanding class hierarchies and module organization.

- **Radial**: A circular layout with the most connected nodes in the center.
  Good for identifying central components in your codebase.

- **Sankey**: A flow diagram showing dependencies between components.
  Helpful for understanding data flow and module dependencies.

## Usage Tips

- In the visualization, you can:
  - Zoom in/out with the mouse wheel
  - Click and drag nodes to reposition them
  - Hover over nodes to see details
  - Click on nodes to highlight connections
  - Search for specific nodes using the search box

- For large codebases, use filters to focus on specific parts of the graph

- The dark theme works best for presentations, while the light theme is better for documentation
```

### Ingestion Commands

When the service is running, you can ingest a code repository with:

```bash
# Start ingestion for the current directory with real-time progress tracking
codestory ingest start .

# Start ingestion without progress display
codestory ingest start . --no-progress
```

The CLI uses Redis for real-time progress tracking, with a fallback to API polling if Redis is unavailable:

```
Connected to Redis for real-time progress updates
Ingestion job started with ID: 01234567-89ab-cdef-0123-456789abcdef

Overall Progress: [===========>          ] 72%  Running
filesystem:     [===================>    ] 95%  Running
summarizer:     [===============>        ] 65%  Running
docgrapher:     [>                       ]  5%  Pending
```

Check ingestion status:

```bash
codestory ingest status
```

List all ingestion jobs:

```bash
codestory ingest jobs
```

Stop an ingestion job:

```bash
codestory ingest stop JOB_ID
```

### Query Commands

Once code has been ingested, you can run queries:

```bash
# Run a Cypher query
codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath LIMIT 10"

# Ask natural language questions
codestory ask "What are the main components of the system?"
```

### Visualization Commands

Generate visualizations of your code graph:

```bash
# Generate a visualization
codestory visualize generate --output visualization.html

# Open a visualization
codestory visualize open visualization.html
```

### Command Shortcuts

Code Story provides convenient aliases for frequently used commands:

```
ask        -> gs (Get Summary)
config     -> cfg
ingest     -> in
ingest jobs -> ij
ingest stop -> is
query      -> q
service start -> ss
service status -> st
service stop  -> sx
visualize  -> vz
```

## End-to-End Demo Script

The repository includes a comprehensive end-to-end demo script at `scripts/run_cli_demo.sh` that demonstrates the complete CLI workflow:

```bash
# Run the CLI demo script
./scripts/run_cli_demo.sh
```

The demo script performs the following steps:
1. Verifies CLI installation and configuration
2. Starts the service using Docker Compose
3. Prepares a sample project for ingestion
4. Ingests the sample code with real-time progress tracking
5. Demonstrates querying the graph with Cypher and natural language
6. Generates an HTML visualization of the code
7. Shows example commands for further exploration
8. Cleans up resources

You can examine the script source to understand the full capabilities of the CLI.

## Visualization Example

When you run a visualization using the `codestory visualize generate` command, you'll get an interactive HTML file that looks like this:

![Code Story Visualization Example](./assets/visualization.html)

## Going Further

For more details on using the CLI, refer to the [CLI documentation](../user_guides/cli_guide.md).

## Troubleshooting

If you encounter issues with the CLI:

1. Ensure Docker is running and the necessary containers are up
2. Check your `.codestory.toml` configuration (especially Neo4j connection settings)
3. Verify the service status with `codestory service status`
4. If services aren't starting properly, check Docker logs with `docker-compose logs`

### Common Issues

1. **Service Connection Failed**: If you see "Connection refused" errors, ensure the service is running with `codestory service start` and wait a few seconds for it to initialize.

   If the service continues to fail to start:
   ```bash
   # Stop any running containers
   docker-compose down
   
   # Start just Neo4j and Redis individually
   docker-compose up -d neo4j redis
   
   # Build the service image
   docker-compose build service
   
   # Start the service
   docker-compose up -d service
   
   # Check if all containers are running
   docker ps
   
   # Check logs if still having issues
   docker-compose logs service
   ```

2. **Neo4j Connection Issues**: The Neo4j database runs in Docker and is exposed on port 7689 (remapped from the internal 7687). Make sure your `.codestory.toml` has the correct URI: `bolt://localhost:7689`.

   Verify Neo4j is running and accessible:
   ```bash
   # Check if Neo4j is running
   docker ps | grep neo4j
   
   # Check Neo4j logs
   docker-compose logs neo4j
   ```

3. **Redis Connection Issues**: If there are issues with Redis port conflicts, edit `docker-compose.yml` to use a different port (e.g., 6389 instead of 6379) and update `.codestory.toml` accordingly.

4. **Database Empty**: If queries return no results, you might need to run ingestion first with `codestory ingest start .`

5. **Authentication Problems**: For using Azure OpenAI or other authenticated services, ensure your environment variables are properly set in your `.env` file.

6. **Port Conflicts**: If you see errors about ports already being allocated, you may have other services using those ports. Either stop those services or modify the port mappings in `docker-compose.yml`.