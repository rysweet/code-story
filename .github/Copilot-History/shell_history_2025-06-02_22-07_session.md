# Shell Command History - 2025-06-02 Session

## Commands executed on 2025-06-02

```bash
pytest -q tests/unit/test_celery_adapter.py
```
# Run unit tests for celery adapter - all 4 tests passed successfully

```bash
pytest --collect-only tests/integration/ | grep -i health
```
# Find health-related integration tests
```bash
pytest -q tests/integration/test_service.py::test_legacy_health_check -v
```
# Failed due to AttributeError: 'str' object has no attribute 'get' - fixed in celery_adapter.py

```bash
pytest -q tests/integration/test_service.py::test_legacy_health_check -v
```
# Test passed after fixing celery_adapter.py and health.py to handle tuple format

```bash
pytest -q tests/unit/test_celery_adapter.py
```
# All unit tests pass

```bash
pytest -q tests/unit/test_graphdb/test_connector.py
```
# All connector tests pass

```bash
pytest -q tests/integration/test_service.py::test_v1_health_check -v
```
# Test passed after updating test expectations

```bash
pytest -q tests/integration/test_service.py -k "health" --tb=short
```
# Found 2 failing tests that need mocking fixes for degraded/unhealthy scenarios

