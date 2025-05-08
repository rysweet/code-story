"""Celery application configuration for the ingestion pipeline.

This module sets up the Celery application used by the ingestion pipeline
for task management and distributed processing.
"""

import logging
from celery import Celery
from ..config.settings import get_settings

# Set up logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


def create_celery_app() -> Celery:
    """Create and configure the Celery application.
    
    Returns:
        Celery: Configured Celery application
    """
    # Create Celery app with Redis backend and broker
    app = Celery(
        'ingestion_pipeline',
        broker=settings.redis.uri,
        backend=settings.redis.uri,
    )
    
    # Configure task routes
    app.conf.task_routes = {
        "codestory.ingestion_pipeline.tasks.*": {"queue": "ingestion"},
        "codestory_*.step.*": {"queue": "ingestion"},
        "codestory.pipeline.steps.*": {"queue": "ingestion"},  # Match the task name in the decorator
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
    
    # Auto-discover tasks from all registered plugins
    app.autodiscover_tasks(["codestory_blarify", "codestory_filesystem", 
                            "codestory_summarizer", "codestory_docgrapher",
                            "codestory.ingestion_pipeline"])
    
    # Log configuration
    logger.info(f"Celery app created with broker: {settings.redis.uri}")
    
    return app


# Create the celery app instance
app = create_celery_app()