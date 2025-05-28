"""Celery worker configuration for code ingestion tasks."""

from celery import Celery  # type: ignore[import-untyped]

from codestory.config.settings import get_settings

settings = get_settings()

# Configure Celery
app = Celery(
    "codestory",
    broker=settings.redis.uri,
    backend=settings.redis.uri,
)

# Configure task routes
app.conf.task_routes = {
    "codestory.ingestion_pipeline.tasks.*": {"queue": "ingestion"},
}

# Set concurrency from settings
app.conf.worker_concurrency = settings.service.worker_concurrency

# Configure serialization
app.conf.accept_content = ["json"]
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"

# Additional settings
app.conf.task_track_started = True
app.conf.task_time_limit = 3600  # 1 hour
app.conf.worker_prefetch_multiplier = 1  # One task per worker at a time
