"""Celery application configuration for the ingestion pipeline.

This module sets up the Celery application used by the ingestion pipeline
for task management and distributed processing.
"""

import logging

from celery import Celery

from ..config.settings import get_settings

# --- DEBUG: Print environment and Redis URI at Celery worker startup ---
import os
print("[celery_app] ENVIRONMENT VARIABLES AT STARTUP:", flush=True)
for k, v in sorted(os.environ.items()):
    print(f"{k}={v}", flush=True)
try:
    settings = get_settings()
    print(f"[celery_app] get_settings().redis.uri: {settings.redis.uri}", flush=True)
except Exception as e:
    print(f"[celery_app] Error loading settings: {e}", flush=True)
# ----------------------------------------------------------------------

# Set up logging
logger = logging.getLogger(__name__)

import os

print(f"[celery_app] CELERY_TASK_ALWAYS_EAGER={os.environ.get('CELERY_TASK_ALWAYS_EAGER')}", flush=True)
try:
    from celery import Celery as _Celery
    _app = _Celery("debug")
    print(f"[celery_app] app.conf.task_always_eager={getattr(_app.conf, 'task_always_eager', None)}", flush=True)
except Exception as e:
    print(f"[celery_app] Error creating debug Celery app: {e}", flush=True)

def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Returns:
        Celery: Configured Celery application
    """
    # Always get settings at the start
    settings = get_settings()
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
    logger.info(
        f"Celery app instantiated with broker_url: {broker_url}, "
        f"backend_url: {backend_url}, "
        f"eager_mode: {eager_mode}"
    )

    return app


# Lazy singleton for celery app instance
_celery_app_instance = None

def get_celery_app() -> Celery:
   global _celery_app_instance
   if _celery_app_instance is None:
       _celery_app_instance = create_celery_app()
   return _celery_app_instance

# --------------------------------------------------------------------------- #
# Export a default Celery application instance for CLI discovery.
# This allows the command:
#   python -m celery -A codestory.ingestion_pipeline.celery_app:app worker ...
# to locate the application. Without this alias, workers cannot start, which
# breaks backend service startup and integration tests.
# --------------------------------------------------------------------------- #

# Create a lazy proxy that only instantiates the Celery app when accessed
class _LazyApp:
    """Lazy proxy for Celery app to avoid import-time instantiation."""
    def __init__(self):
        self._app = None
    
    def __getattr__(self, name):
        if self._app is None:
            self._app = get_celery_app()
        return getattr(self._app, name)
    
    def __call__(self, *args, **kwargs):
        if self._app is None:
            self._app = get_celery_app()
        return self._app(*args, **kwargs)

# NOTE: get_celery_app() is cheap due to the singleton guard above.
app = _LazyApp()

__all__ = ["get_celery_app", "app"]

# --- DEBUG: Print registered Celery tasks at startup (when app is accessed) ---
# Note: This will now only execute when the app is actually used, not at import time
