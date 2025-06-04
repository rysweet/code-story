import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def celery_eager_env(monkeypatch):
    """
    Ensure Celery runs in eager mode with in-memory broker for all tests.

    This fixture sets environment variables and monkeypatches redis.Redis
    to prevent any real Redis connections. It must run before any Celery app
    or ingestion pipeline code is imported.
    """
    # Force Celery eager mode and in-memory broker/result backend
    os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
    os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "true"
    os.environ["CELERY_TASK_STORE_EAGER_RESULT"] = "true"
    os.environ["REDIS_URI"] = "memory://"
    os.environ["REDIS__URI"] = "memory://"

    # Monkeypatch redis.Redis to a dummy stub to prevent real connections
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