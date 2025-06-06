# Shell Command History - Integration Tests Session
Session ID: integration_tests
Started: 2025-06-05 21:50

## 2025-06-05

```bash
uv run pytest -vv tests/integration --maxfail=1
```
# Ran integration tests to capture the first failure after pydantic upgrade
# Exit code: 2
# Found multiple failures related to Docker container issues and Neo4j connectivity