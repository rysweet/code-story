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
RUN poetry install --no-interaction --no-ansi --no-root --only main --extras azure

# Copy project
COPY . /app/

# Install project
RUN poetry install --no-interaction --no-ansi --only main --extras azure

# Development stage
FROM builder as development

# Install dev dependencies
RUN poetry install --no-interaction --no-ansi --with dev

# Expose port
EXPOSE 8000

# Run the service with hot-reload
CMD ["uvicorn", "src.codestory_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM python:3.12-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.* \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Explicitly install Azure packages
RUN pip install azure-identity azure-keyvault-secrets

# Create a non-root user to run the application
RUN groupadd -r codestory && useradd -r -g codestory codestory

# Copy built Python packages and code from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src /app/src
COPY --from=builder /app/prompts /app/prompts

# Set proper ownership and permissions
RUN chown -R codestory:codestory /app && \
    chmod -R 750 /app

# Add security labels
LABEL org.opencontainers.image.security.capabilities="CHOWN,DAC_OVERRIDE,SETGID,SETUID"
LABEL org.opencontainers.image.security.seccomp=unconfined

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Switch to non-root user
USER codestory

# Run the service
CMD ["uvicorn", "src.codestory_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Worker stage
FROM production as worker

# Run the Celery worker
CMD ["celery", "-A", "src.codestory.ingestion_pipeline.celery_app", "worker", "--loglevel=info"]