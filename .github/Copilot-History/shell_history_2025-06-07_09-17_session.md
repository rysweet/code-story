## 2025-06-07
```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml down -v --remove-orphans --timeout 1
# Cleanup docker containers to ensure clean environment before running tests
```bash
uv run pytest -q tests/unit
# Ran all unit tests; all passed
```
```bash
uv run pytest tests/integration/test_cli/test_config_integration.py::TestConfigCommands::test_config_show -x -s
# Ran minimal integration test to reproduce service container health-check failure and capture logs
```
```bash
docker build -f Dockerfile.service -t codestory-service:test .
# Rebuilt service image after settings precedence patch

docker build -f Dockerfile.worker -t codestory-celery-worker:test .
# Rebuilt worker image after settings precedence patch and Dockerfile fix
```