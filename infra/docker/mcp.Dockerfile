FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${PATH}:/root/.local/bin"

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Configure poetry to not use virtualenvs inside Docker
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Copy project
COPY . /app/

# Install project
RUN poetry install --no-interaction --no-ansi --only main

# Expose port
EXPOSE 8001

# Run the MCP service
CMD ["uvicorn", "src.codestory.mcp.main:app", "--host", "0.0.0.0", "--port", "8001"]