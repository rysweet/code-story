#!/bin/bash
echo "Starting Code Story development environment..."

# Check if Docker is available
if ! docker info > /dev/null 2>&1; then
    echo "Warning: Docker is not available. You may need to restart the container or check Docker-in-Docker setup."
    echo "Try running: sudo service docker start"
fi

echo "Environment setup complete!"
echo ""
echo "To start the full environment with Docker Compose:"
echo "  docker-compose up -d"
echo ""
echo "To run tests:"
echo "  source .venv/bin/activate && pytest"
echo ""
echo "To use the CLI:"
echo "  source .venv/bin/activate && python -m codestory.cli.main --help"
echo ""
echo "For GUI development:"
echo "  npm run dev"
