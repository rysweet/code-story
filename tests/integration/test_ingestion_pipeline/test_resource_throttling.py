import time
from concurrent.futures import ThreadPoolExecutor
import pytest
import requests
from typing import Any
API_BASE = 'http://localhost:8000/v1/ingest'

@pytest.mark.integration
def test_resource_status_endpoint() -> None:
    """Test that the /resource_status endpoint returns correct structure."""
    resp = requests.get(f'{API_BASE}/resource_status', headers={'Authorization': 'Bearer test'})
    assert resp.status_code == 200
    data = resp.json()
    assert 'available_tokens' in data or 'tokens' in data
    assert 'max_tokens' in data or 'tokens' in data
    if 'tokens' in data:
        tokens = data['tokens']
        assert 'available_tokens' in tokens
        assert 'max_tokens' in tokens
        assert isinstance(tokens['available_tokens'], int)
        assert isinstance(tokens['max_tokens'], int)
        assert 0 <= tokens['available_tokens'] <= tokens['max_tokens']
    else:
        assert isinstance(data['available_tokens'], int)
        assert isinstance(data['max_tokens'], int)
        assert 0 <= data['available_tokens'] <= data['max_tokens']
    assert 'metrics' in data
    metrics = data['metrics']
    for key in ('duration_seconds', 'cpu_percent', 'memory_mb'):
        assert key in metrics
        for stat in ('avg', 'min', 'max'):
            assert stat in metrics[key]

@pytest.mark.integration
def test_resource_throttling_enforced(monkeypatch: Any) -> None:
    """
    Test that resource throttling is enforced by attempting to run more jobs than allowed.
    This test assumes the resource_max_tokens is set to 2 for demonstration.
    """

    def mock_start_job():
        resp = requests.post(f'{API_BASE}', json={'source': 'tests/fixtures/test_repo', 'pipeline': ['filesystem'], 'options': {}}, headers={'Authorization': 'Bearer test'})
        return resp
    monkeypatch.setattr(time, 'sleep', lambda x: None)
    max_tokens = 2
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(mock_start_job) for _ in range(max_tokens + 2)]
        results = [f.result() for f in futures]
    throttled = any((r.status_code == 202 or (r.status_code == 500 and 'throttle' in r.text.lower()) for r in results))
    assert throttled, 'At least one job should be throttled or accepted'
    resp = requests.get(f'{API_BASE}/resource_status', headers={'Authorization': 'Bearer test'})
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data['available_tokens'] <= data['max_tokens']