# CLI Demo

This demonstration shows how to use the Code Story command line interface to ingest, analyze, and visualize code repositories.

## Installation

First, let's install the Code Story CLI:

```bash
# Install from PyPI
pip install code-story-cli

# Alternatively, install from the repository
git clone https://github.com/rysweet/code-story.git
cd code-story
pip install -e .
```

After installation, verify the CLI is working:

```bash
codestory --version
```

Expected output:
```
Code Story CLI v0.1.0
```

## Configuration

Before using Code Story, you need to set up a configuration file:

```bash
# Generate a default configuration file
codestory config init

# Edit the configuration file with your Neo4j connection details
codestory config edit
```

Alternatively, you can set up environment variables:

```bash
# Setup environment variables for Neo4j
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
export NEO4J_DATABASE="codestory"

# Setup OpenAI API key for code analysis
export OPENAI_API_KEY="your-openai-api-key"
```

Verify your configuration:

```bash
codestory config show
```

## Code Ingestion

Now, let's ingest a code repository. We'll use the Code Story codebase itself for this demo:

```bash
# Clone the repository if you haven't already
git clone https://github.com/rysweet/code-story.git
cd code-story

# Start the ingestion process
codestory ingest start --path .
```

This command starts the ingestion pipeline, which:
1. Scans the filesystem
2. Processes code files
3. Analyzes code structure
4. Generates summaries
5. Creates a knowledge graph

You can check the progress of the ingestion:

```bash
codestory ingest status
```

Expected output:
```
Ingestion job abc123 is processing:
- Filesystem scan: 100% complete
- Code analysis: 85% complete
- Summary generation: 70% complete
- Knowledge graph creation: 65% complete
Overall progress: 80%
```

Wait for the ingestion to complete. For large repositories, this might take some time.

## Code Analysis

Once ingestion is complete, you can analyze the code using the CLI:

### Running Queries

Let's run some queries to explore the code:

```bash
# List all Python files in the repository
codestory query run "MATCH (f:File) WHERE f.extension = 'py' RETURN f.path AS FilePath ORDER BY FilePath LIMIT 10"
```

Expected output:
```
+-------------------------------------------------------------+
| FilePath                                                     |
+-------------------------------------------------------------+
| /src/codestory/__init__.py                                   |
| /src/codestory/cli/__init__.py                               |
| /src/codestory/cli/client/__init__.py                        |
| /src/codestory/cli/client/progress_client.py                 |
| /src/codestory/cli/client/service_client.py                  |
| /src/codestory/cli/commands/__init__.py                      |
| /src/codestory/cli/commands/ask.py                           |
| /src/codestory/cli/commands/config.py                        |
| /src/codestory/cli/commands/ingest.py                        |
| /src/codestory/cli/commands/query.py                         |
+-------------------------------------------------------------+
```

### Natural Language Queries

You can also ask questions in natural language:

```bash
# Ask about the code structure
codestory ask "What are the main components of the Code Story system?"
```

Expected output:
```
The main components of the Code Story system are:

1. Ingestion Pipeline - Responsible for processing code repositories and building the knowledge graph
2. Graph Database - Stores the code structure and relationships
3. Service API - Provides HTTP endpoints for interacting with the system
4. CLI - Command line interface for users
5. GUI - Graphical user interface for visualization
6. MCP Adapter - Machine Callable Package adapter for integration with AI agents

These components work together to analyze, index, and provide insights about codebases.
```

## Graph Visualization

Code Story CLI also provides visualization capabilities:

```bash
# Generate a visualization of the project structure
codestory visualize --path ./visualization.html
```

This generates an interactive HTML visualization of the code structure.

To view the visualization:

```bash
# Open the visualization in your browser
open ./visualization.html
```

## Cleaning Up

To clean up after this demo:

```bash
# Stop any running services
codestory service stop

# Clear the database if needed
codestory query run "MATCH (n) DETACH DELETE n"
```

## Going Further

Now that you've seen the basic functionality of the Code Story CLI, you can explore more advanced features:

- Check out the [CLI documentation](../user_guides/cli_guide.md) for more commands
- Try ingesting different repositories
- Experiment with complex queries
- Integrate with your workflow