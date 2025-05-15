"""Entry point for running the Celery worker."""

import logging
import os
import sys

# Import the Celery app
from .celery_app import app
from ..config.settings import get_settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

def main():
    """Run the Celery worker with the appropriate configuration."""
    try:
        # Log configuration
        logger.info(f"Starting Celery worker with broker: {settings.redis.uri}")
        logger.info(f"Worker concurrency: {settings.service.worker_concurrency}")
        
        # Set worker arguments
        args = [
            'worker',
            '--loglevel=INFO',
            f'--concurrency={settings.service.worker_concurrency}',
            '--queues=ingestion',
            '--hostname=worker@%h',
        ]
        
        # Check if running as root in a container (common in Docker)
        if os.environ.get('C_FORCE_ROOT'):
            logger.warning("Running as root - this is not recommended in production!")
            # No additional action needed as C_FORCE_ROOT environment variable is all Celery needs
        
        # Run the worker
        logger.info("Starting worker with arguments: %s", " ".join(args))
        sys.argv = ['celery'] + args
        app.start()
        
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()