FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install poetry and project dependencies
RUN pip install --upgrade pip wheel poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --with dev

# Install Celery
RUN pip install celery

# Default command: start Celery worker for the project
CMD ["celery", "-A", "codestory.ingestion_pipeline.celery_app", "worker", "--loglevel=info"]