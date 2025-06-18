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
import os
logger.info(f"[celery_app] settings.redis.uri: {getattr(settings, 'redis', None) and settings.redis.uri}")
logger.info(f"[celery_app] os.environ.get('REDIS_URL'): {os.environ.get('REDIS_URL')}")


def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Returns:
        Celery: Configured Celery application
    """
    # Check if we're in eager mode (integration tests)
    eager_mode = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true")
    
    if eager_mode:
        # Use memory backends for integration tests
        broker_url = "memory://"
        backend_url = "cache+memory://"
        logger.info("Celery configured for eager mode with memory backends")
    else:
        # Use Redis for production
        broker_url = settings.redis.uri
        backend_url = settings.redis.uri
        logger.info(f"Celery configured with Redis: {settings.redis.uri}")
    
    # Create Celery app with appropriate backends
    app = Celery(
        "ingestion_pipeline",
        broker=broker_url,
        backend=backend_url,
    )

    # Configure eager mode if enabled
    if eager_mode:
        app.conf.task_always_eager = True
        app.conf.task_eager_propagates = True
        app.conf.task_store_eager_result = True
        logger.info("Celery configured for eager execution")

    # Define priority queues
    from kombu import Queue

    app.conf.task_queues = (
        Queue("high"),
        Queue("default"),
        Queue("ingestion"),
        Queue("low"),
    )

    # Configure task routes (route step tasks to "ingestion" queue)
    app.conf.task_routes = {
        "codestory.ingestion_pipeline.tasks.*": {"queue": "default"},
        "codestory_*.step.*": {"queue": "ingestion"},
        "codestory.pipeline.steps.*": {
            "queue": "default"
        },  # Match the task name in the decorator
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
    app.autodiscover_tasks(
        [
            "codestory_blarify",
            "codestory_filesystem",
            "codestory_summarizer",
            "codestory_docgrapher",
            "codestory.ingestion_pipeline",
        ]
    )
    
    # Manually import step task modules to ensure registration
    try:
        import codestory_filesystem.step
        import codestory_blarify.step
        import codestory_summarizer.step
        import codestory_docgrapher.step
        logger.info("Successfully imported step task modules")
    except ImportError as e:
        logger.warning(f"Failed to import some step task modules: {e}")

    # Log configuration
    logger.info(f"Celery app created with broker: {settings.redis.uri}")

    return app


# Create the celery app instance
app = create_celery_app()
