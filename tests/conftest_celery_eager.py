import os

# Set Celery to eager mode and use in-memory broker/result backend before any project code is imported
os.environ.update({
    "CODESTORY_CELERY_EAGER": "true",
    "CELERY_TASK_ALWAYS_EAGER": "true",
    "CELERY_BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
    "CODESTORY_BROKER_URL": "memory://",
    "CODESTORY_RESULT_BACKEND": "cache+memory://",
})

import importlib
import sys

# Force reload of celery_app to pick up new env vars before any manager/tasks import
importlib.reload(importlib.import_module("codestory.ingestion_pipeline.celery_app"))

import pytest

@pytest.fixture(scope="session", autouse=True)
def celery_eager_env(monkeypatch):
    """
    Monkeypatch redis.Redis to a dummy stub to prevent real connections during tests.
    """
    try:
        import redis
        class DummyRedis:
            def __init__(self, *a, **kw): pass
            def __getattr__(self, name):
                def dummy(*a, **kw): return None
                return dummy
        monkeypatch.setattr(redis, "Redis", DummyRedis)
    except ImportError:
        pass  # If redis is not installed, nothing to patch