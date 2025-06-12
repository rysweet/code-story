## 2025-06-04
```bash
docker compose down --remove-orphans --volumes --timeout 0  # Clean up containers and volumes before tests
```bash
uv pip install -r requirements.txt  # Ensure dependencies in active uv venv
```

## 2025-06-06
```bash
docker compose -f docker-compose.test.yml down -v --remove-orphans || true  # Environment cleanup - remove test containers and volumes
```
```bash
uv run pytest -q -m "not integration"  # Unit tests all passing with no warnings
```
```bash
uv run pytest -q -m "not integration" -W error  # Unit tests confirmed warning-free
```
```bash
uv run pytest -q tests/integration/test_service.py  # Fixed 4 failing integration tests - all pass now
```
```bash
uv run pytest -q tests/integration/test_config_api.py  # Passes
```
```bash
uv run pytest -q tests/integration/test_graphdb/  # FIXED - conflicting Neo4j container setups resolved - all 8 tests pass
```
```bash
uv run pytest -q tests/integration/test_ingestion_pipeline/  # Many failures - Redis/Neo4j connection issues
```
```bash
docker container prune -f || true  # Environment cleanup - remove stopped containers
```
```bash
docker volume prune -f || true  # Environment cleanup - remove unused volumes (34GB reclaimed)
```
```bash
docker network prune -f || true  # Environment cleanup - remove unused networks
```