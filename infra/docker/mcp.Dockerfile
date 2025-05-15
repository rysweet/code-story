# Build stage
FROM python:3.12-slim as builder

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

# Development stage
FROM builder as development

# Install dev dependencies
RUN poetry install --no-interaction --no-ansi --with dev

# Expose port
EXPOSE 8001

# Run the MCP API with auto-reload
CMD ["uvicorn", "src.codestory_mcp.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# Production stage
FROM python:3.12-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.* \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the application
RUN groupadd -r mcp && useradd -r -g mcp mcp

# Copy built Python packages and code from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src/codestory_mcp /app/src/codestory_mcp

# Set proper ownership and permissions
RUN chown -R mcp:mcp /app && \
    chmod -R 750 /app

# Add security labels
LABEL org.opencontainers.image.security.capabilities="CHOWN,DAC_OVERRIDE,SETGID,SETUID"
LABEL org.opencontainers.image.security.seccomp=unconfined

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/v1/health || exit 1

# Expose port
EXPOSE 8001

# Switch to non-root user
USER mcp

# Run the MCP API
CMD ["uvicorn", "src.codestory_mcp.main:app", "--host", "0.0.0.0", "--port", "8001"]