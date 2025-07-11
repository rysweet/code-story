## 2025-07-11

```sh
uv run pytest tests/integration/test_ingestion_pipeline/test_filesystem_direct.py::test_filesystem_direct -v
# Ran the integration test to verify if import-time Celery and environment propagation issues in the ingestion pipeline are resolved.