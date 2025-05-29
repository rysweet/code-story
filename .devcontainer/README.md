# Code Story Dev Container

This dev container provides a complete development environment for the Code Story project optimized for GitHub Codespaces and VS Code Remote Containers.

## Features

- Python 3.12 development environment with virtual environment setup
- TypeScript/Node.js environment for GUI development  
- Docker-in-Docker for container operations
- Azure CLI for cloud deployments
- GitHub CLI for repository management
- VS Code extensions for Python, TypeScript, Docker, Bicep, and more
- Automatic project setup with dependencies

## Getting Started

1. Open this repository in VS Code or GitHub Codespaces
2. Click "Reopen in Container" when prompted (or use "Open in Codespaces" for GitHub Codespaces)
3. Wait for the container to build and initialize
4. The setup script will automatically:
   - Create a Python virtual environment
   - Install the project and dependencies
   - Install development tools (black, ruff, mypy, pytest)
   - Install Node.js dependencies
   - Create default configuration files
   - Set up convenience scripts
5. Start development!

## Development Workflow

After the container starts, you can use the convenience script:

```bash
# See available commands and start instructions
./start-dev.sh

# Activate the virtual environment (if not already active)
source .venv/bin/activate

# Start the Docker services (Neo4j, Redis, etc.)
docker-compose up -d

# Run tests
pytest

# Use the CLI
python -m codestory.cli.main --help

# GUI development
npm run dev
```

## Services

The development environment can run alongside application services via Docker Compose:

- **Neo4j**: Graph database (ports 7474, 7687)
- **Redis**: Cache and message broker (port 6379)  
- **Service**: Main API service (port 8000)
- **Worker**: Celery worker for background tasks
- **GUI**: Vue.js frontend (port 5173)

## File Structure

- `/workspace`: Project root (mounted from host)
- `/workspace/.venv`: Python virtual environment
- Configuration files are automatically created from templates
- `start-dev.sh`: Convenience script with common commands

## Docker-in-Docker Support

The devcontainer includes Docker-in-Docker support for:
- Building and running Docker containers
- Using Docker Compose for local development
- Container testing and debugging

## Troubleshooting

If you encounter issues:

1. **Docker commands fail**: 
   - Try restarting Docker: `sudo service docker start`
   - Check Docker-in-Docker setup: `docker info`
   
2. **Port conflicts**: 
   - Use the port forwarding built into the devcontainer
   - Check if services are already running with `docker ps`
   
3. **Permission issues**: 
   - The container runs as user `vscode` with appropriate permissions
   - If needed, run `sudo chown -R vscode:vscode /workspace`
   
4. **Service connectivity**: 
   - Use `localhost` for connections from within the devcontainer
   - Use service names when connecting between Docker containers
   
5. **Virtual environment issues**:
   - Reactivate with `source .venv/bin/activate`
   - Recreate if needed: `rm -rf .venv && python -m venv .venv`

## GitHub Codespaces Specific Notes

When using GitHub Codespaces:
- All ports are automatically forwarded and accessible via HTTPS
- Docker-in-Docker works out of the box
- Git credentials are automatically configured
- Extensions are automatically installed
- The environment is ready to use immediately after setup completes

