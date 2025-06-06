# Code Story Documentation

```{toctree}
:maxdepth: 1
:hidden:
:caption: User Guides

user_guides/index
user_guides/installation
user_guides/cli_guide
user_guides/gui_guide
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Architecture

architecture/index
architecture/components
architecture/data_flow
architecture/design_decisions
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: API Reference

api/index
api/config
api/graphdb
api/ingestion_pipeline
api/code_story_service
api/mcp_adapter
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Developer Guides

developer_guides/index
developer_guides/environment_setup
developer_guides/extending/pipeline_steps
developer_guides/extending/mcp_tools
developer_guides/extending/api_endpoints
developer_guides/testing
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Deployment

deployment/index
deployment/local
deployment/azure
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Demos

demos/index
demos/cli_demo
demos/gui_demo
demos/mcp_demo
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Contributing

contributing
```

## Overview

Code Story is a system to convert codebases into richly-linked knowledge graphs with natural-language summaries.

It ingests codebases, analyzes their structure, and produces a knowledge graph where code entities are linked based on their relationships. Each entity is augmented with natural language summaries generated by AI.

## Key Features

- **Multi-language support** for codebase analysis
- **Plugin-based ingestion pipeline** for extensibility
- **Neo4j graph database** with semantic indexing and vector search
- **Interactive 3D visualization** of code relationships
- **Natural language summaries** of code entities and relationships
- **API** for integration with IDEs and other tools
- **Model Context Protocol (MCP)** support for AI agent integration

## Quick Start

```bash
# Clone the repository
git clone https://github.com/rysweet/code-story.git
cd code-story

# Create a .env file from the template
cp .env-template .env
# Edit .env with your settings

# Start the services with the provided script
./infra/scripts/start.sh

# Access the GUI at http://localhost:5173
```

## Components

Code Story is built as a microservices architecture with the following components:

- **Configuration Module**: Layered configuration system
- **Graph Database**: Neo4j connector with semantic indexing
- **AI Client**: OpenAI API client with caching and retry logic
- **Ingestion Pipeline**: Plugin-based system for processing code
- **API Service**: FastAPI service exposing graph operations
- **Worker**: Celery worker for async processing
- **MCP Service**: Model Context Protocol server
- **GUI**: React/Redux web interface with 3D visualization

## Getting Help

If you need help or have questions, please:

1. Check the [User Guides](user_guides/index.md) for detailed usage instructions
2. Browse the [API Reference](api/index.md) for detailed information on APIs
3. Explore the [Architecture](architecture/index.md) documentation for system details
4. For developers, see the [Developer Guides](developer_guides/index.md) for extending Code Story