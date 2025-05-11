# Code Story Dev Container

This dev container provides a complete development environment for the Code Story project.

## Features

- Python development environment with all dependencies
- TypeScript/Node.js environment for GUI development
- Docker-in-Docker for container testing
- Azure CLI for cloud deployments
- GitHub CLI for repository management
- VS Code extensions for Python, TypeScript, Docker, Bicep, and more

## Getting Started

1. Open this repository in VS Code
2. Click "Reopen in Container" when prompted
3. Wait for the container to build and initialize
4. Start development\!

## Note

This devcontainer connects to the service container in the docker-compose setup,
giving you direct access to the Python environment with all dependencies installed.

Additional services (Neo4j, Redis, MCP, etc.) are available in separate containers
and accessible via the network.

