import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from codestory_service.application.ingestion_service import IngestionService
from codestory_service.domain.ingestion import JobStatus
from codestory_service.infrastructure.celery_adapter import CeleryAdapter
from codestory_service.main import app

client = TestClient(app)

@pytest.fixture
def celery_adapter() -> Any:
    return CeleryAdapter()

@pytest.fixture
def ingestion_service(celery_adapter: Any) -> Any:
    return IngestionService(celery_adapter)

def start_test_job() -> Any:
    payload = {'source': '.', 'steps': ['filesystem'], 'options': {'timeout': 60}}
    response = client.post('/v1/ingest', json=payload)
    assert response.status_code == 200
    job_id = response.json()['job_id']
    return job_id

def test_cancel_running_job(ingestion_service: Any) -> None:
    job_id = start_test_job()
    time.sleep(2)
    cancel_response = client.post(f'/v1/ingest/{job_id}/cancel')
    assert cancel_response.status_code == 200
    for _ in range(10):
        status = client.get(f'/v1/ingest/{job_id}').json()['status']
        if status == JobStatus.CANCELLED:
            break
        time.sleep(1)
    assert status == JobStatus.CANCELLED

def test_cancel_pending_job(ingestion_service: Any) -> None:
    job_id = start_test_job()
    cancel_response = client.post(f'/v1/ingest/{job_id}/cancel')
    assert cancel_response.status_code == 200
    for _ in range(10):
        status = client.get(f'/v1/ingest/{job_id}').json()['status']
        if status == JobStatus.CANCELLED:
            break
        time.sleep(1)
    assert status == JobStatus.CANCELLED

def test_cancel_completed_job(ingestion_service: Any) -> None:
    job_id = start_test_job()
    for _ in range(30):
        status = client.get(f'/v1/ingest/{job_id}').json()['status']
        if status == JobStatus.COMPLETED:
            break
        time.sleep(1)
    cancel_response = client.post(f'/v1/ingest/{job_id}/cancel')
    assert cancel_response.status_code == 200
    status = client.get(f'/v1/ingest/{job_id}').json()['status']
    assert status == JobStatus.COMPLETED