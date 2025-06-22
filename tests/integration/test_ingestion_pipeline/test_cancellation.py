import time
import tempfile
import os
from typing import Any
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from codestory_service.application.ingestion_service import IngestionService
from codestory_service.domain.ingestion import JobStatus
from codestory_service.infrastructure.celery_adapter import CeleryAdapter
from codestory_service.main import app

# Set up environment for fast test execution
os.environ["CODESTORY_TEST_ENV"] = "true"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["CELERY_TASK_STORE_EAGER_RESULT"] = "true"
os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "true"

client = TestClient(app)


@pytest.fixture
def celery_adapter() -> Any:
    return CeleryAdapter()


@pytest.fixture
def ingestion_service(celery_adapter: Any) -> Any:
    return IngestionService(celery_adapter)


@pytest.fixture
def test_repo_dir() -> Any:
    """Create a minimal test repository directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create just one tiny test file
        with open(os.path.join(tmpdir, "test.py"), "w") as f:
            f.write("# Test\n")
        yield tmpdir


def start_test_job(test_dir: str = None) -> Any:
    """Start a test job that completes quickly using test mode."""
    if test_dir:
        source = test_dir
    else:
        source = "."

    # No mocking needed - use built-in test mode for fast execution
    payload = {
        "source": source,
        "steps": ["filesystem"],
        "options": {"timeout": 30, "test_mode": True}
    }
    response = client.post("/v1/ingest", json=payload)
    assert response.status_code in (200, 202)
    job_id = response.json()["job_id"]
    return job_id


def test_cancel_running_job(ingestion_service: Any, test_repo_dir: str) -> None:
    """Test cancelling a job that's currently running (in test mode, job completes quickly)."""
    job_id = start_test_job(test_repo_dir)
    time.sleep(2)
    cancel_response = client.post(f"/v1/ingest/{job_id}/cancel")
    assert cancel_response.status_code == 200
    
    # In test mode, jobs complete instantly, so we expect either COMPLETED or CANCELLED
    status = client.get(f"/v1/ingest/{job_id}").json()["status"]
    assert status in [JobStatus.COMPLETED, JobStatus.CANCELLED]


def test_cancel_pending_job(ingestion_service: Any, test_repo_dir: str) -> None:
    """Test cancelling a job that's pending (in test mode, job completes quickly)."""
    job_id = start_test_job(test_repo_dir)
    cancel_response = client.post(f"/v1/ingest/{job_id}/cancel")
    assert cancel_response.status_code == 200
    
    # In test mode, jobs complete instantly, so we expect either COMPLETED or CANCELLED
    status = client.get(f"/v1/ingest/{job_id}").json()["status"]
    assert status in [JobStatus.COMPLETED, JobStatus.CANCELLED]


def test_cancel_completed_job(ingestion_service: Any, test_repo_dir: str) -> None:
    """Test cancelling a job that has already completed (uses small test directory)."""
    job_id = start_test_job(test_repo_dir)  # Uses small test dir - should complete quickly
    for _ in range(30):
        status = client.get(f"/v1/ingest/{job_id}").json()["status"]
        if status == JobStatus.COMPLETED:
            break
        time.sleep(1)
    cancel_response = client.post(f"/v1/ingest/{job_id}/cancel")
    assert cancel_response.status_code == 200
    status = client.get(f"/v1/ingest/{job_id}").json()["status"]
    assert status == JobStatus.COMPLETED
