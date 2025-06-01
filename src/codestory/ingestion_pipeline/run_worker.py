"""Entry point for running the Celery worker."""
import logging
import os
import sys
from typing import Any

from ..config.settings import get_settings
from .celery_app import app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
settings = get_settings()

def main() -> None:
    """Run the Celery worker with the appropriate configuration."""
    try:
        logger.info(f'Starting Celery worker with broker: {settings.redis.uri}')
        logger.info(f'Worker concurrency: {settings.service.worker_concurrency}')
        args = ['worker', '--loglevel=INFO', f'--concurrency={settings.service.worker_concurrency}', '--queues=ingestion', '--hostname=worker@%h']
        if os.environ.get('C_FORCE_ROOT'):
            logger.warning('Running as root - this is not recommended in production!')
        logger.info('Starting worker with arguments: %s', ' '.join(args))
        sys.argv = ['celery', *args]
        app.start()
    except Exception as e:
        logger.error(f'Failed to start Celery worker: {e}')
        sys.exit(1)
if __name__ == '__main__':
    main()