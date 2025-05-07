#!/bin/zsh
# Bootstrap script for Code Story project
# Sets up Python, JS/TS, and Docker dependencies

set -e

# Python setup
if [ -f pyproject.toml ]; then
    poetry install
fi

# JS/TS setup
if [ -f gui/package.json ]; then
    cd gui && pnpm install && cd ..
fi

# Copy env template
if [ -f .env-template ] && [ ! -f .env ]; then
    cp .env-template .env
fi

# Pre-commit hooks
if [ -f .pre-commit-config.yaml ]; then
    pre-commit install
fi

echo "Bootstrap complete."
