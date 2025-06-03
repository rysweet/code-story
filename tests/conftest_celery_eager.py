import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def celery_eager_env():
    """Set Celery to always-eager mode for all tests."""
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
    os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "true"