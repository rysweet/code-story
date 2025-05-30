# Development Container Configuration

This directory contains the configuration for GitHub Codespaces and VS Code Dev Containers.

## Overview

The devcontainer setup provides a complete development environment with:
- Python 3.12 runtime environment
- Pre-configured VS Code extensions for Python, TypeScript, and Azure development
- Docker-in-Docker support for running services
- GitHub CLI and Azure CLI tools
- Automatic project setup via `setup.sh`

## Files

- `devcontainer.json` - Main container configuration
- `setup.sh` - Post-creation setup script
- `README.md` - This documentation

## Codespaces Integration

This configuration is designed to work seamlessly with GitHub Codespaces. Key features:

### Workspace Folder Handling
- Uses standard Codespaces workspace path: `/workspaces/${localWorkspaceFolderBasename}`
- No custom mounts required - relies on Codespaces' built-in workspace mounting
- Dynamic path resolution in setup scripts for flexibility

### Automatic Setup
The `setup.sh` script automatically:
1. Creates a Python virtual environment
2. Installs the project in development mode
3. Sets up development tools (black, ruff, mypy, pytest)
4. Creates default configuration files (.env, .codestory.toml)
5. Installs Node.js dependencies for GUI development
6. Sets appropriate permissions
7. Creates a convenience script (`start-dev.sh`)

### Port Forwarding
Configured to forward common development ports:
- 7474, 7687 - Neo4j database
- 8000, 8001 - API services
- 5173 - Vite development server
- 6379 - Redis

## Getting Started

### In GitHub Codespaces
1. Create a new Codespace from the repository
2. Wait for the container to build and setup to complete
3. Run `./start-dev.sh` to see available commands
4. Start development!

### In VS Code Dev Containers
1. Install the "Dev Containers" extension in VS Code
2. Open the project folder
3. Click "Reopen in Container" when prompted
4. Wait for the container to build and setup to complete

## Development Workflow

After the container starts:

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

## Troubleshooting

### Common Issues

1. **Workspace loading fails in Codespaces**
   - Ensure no conflicting devcontainer configurations exist
   - Check that workspace paths use standard Codespaces variables
   - Verify no custom mounts are interfering with Codespaces mounting

2. **Python virtual environment issues**
   - The setup script creates `.venv` in the workspace root
   - VS Code is configured to use `/workspaces/${localWorkspaceFolderBasename}/.venv/bin/python`
   - If issues persist, recreate the environment: `rm -rf .venv && python3 -m venv .venv`

3. **Docker-in-Docker not working**
   - Restart the container if Docker daemon isn't running
   - Check with `docker info` to verify Docker is available
   - The setup includes automatic user group configuration

4. **Permission issues**
   - The setup script sets appropriate ownership for the vscode user
   - Scripts in the `scripts/` directory are made executable automatically

### Manual Setup

If automatic setup fails, you can run components manually:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install project
pip install -e .

# Install development tools  
pip install black ruff mypy pytest

# Install Node.js dependencies
npm install
```

## Configuration Details

### Extensions Included
- **Python Development**: Python, Pylance, Black formatter, isort, Ruff, MyPy
- **Frontend Development**: Prettier, ESLint, Vue Language Features
- **DevOps**: Docker, Azure Bicep, YAML support
- **Git Tools**: GitLens, Git Graph, GitHub Actions
- **Utilities**: Code Spell Checker

### Features Enabled
- **Docker-in-Docker**: Version latest with non-root access
- **GitHub CLI**: Latest version for repository operations
- **Azure CLI**: Latest version for cloud deployments  
- **Node.js**: Version 18 for frontend development

## Updates and Maintenance

When updating the devcontainer configuration:

1. Test changes in both Codespaces and local Dev Containers
2. Ensure workspace paths use appropriate variables (`${localWorkspaceFolderBasename}`)
3. Verify all scripts use dynamic path resolution
4. Update this documentation as needed

The configuration prioritizes compatibility between Codespaces and local Dev Containers while maintaining a consistent development experience.

## Recent Fixes

- **Fixed workspace loading issues**: Removed custom mounts that interfered with Codespaces
- **Standardized paths**: Updated all configurations to use `/workspaces/${localWorkspaceFolderBasename}`
- **Dynamic path resolution**: Setup script now detects workspace location automatically
- **Simplified configuration**: Removed redundant Codespaces-specific configuration

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

