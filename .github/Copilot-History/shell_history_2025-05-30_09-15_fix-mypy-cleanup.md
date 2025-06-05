# Shell History - 2025-05-30_09-15_fix-mypy-cleanup

## 2025-05-30

```bash
poetry run mypy --show-error-codes --pretty -p codestory_mcp.utils.serializers > mypy_serializers.txt
```
# Initial MyPy check revealed 6 errors in serializers.py including frozenset indexing, null pointer issues, and type mismatches

```bash
poetry run mypy --show-error-codes --pretty -p codestory_mcp.utils.serializers > mypy_serializers.txt
```
# Second MyPy check after applying complete type annotations - now shows 0 errors (exit code 0)

```bash
poetry run mypy --show-error-codes --pretty -p codestory_service.api.graph > mypy_api_graph.txt
```
# Phase 11 MyPy check on api.graph module - initially found 1 arg-type error on NodeFilter

```bash
poetry run mypy --show-error-codes --pretty -p codestory_service.api.graph > mypy_api_graph.txt
```
# Second MyPy check after fixing NodeFilter type issue - now shows "Success: no issues found in 1 source file"

```bash
python scripts/auto_annotate_return_types.py
```
# Auto-annotation script executed: processed 227 Python files, modified 52 files, annotated 201 functions with -> None

```bash
poetry run mypy --show-error-codes --pretty src/codestory src/codestory_blarify src/codestory_docgrapher src/codestory_filesystem src/codestory_mcp src/codestory_service src/codestory_summarizer tests > mypy_after_auto.txt 2>&1
```
# Comprehensive MyPy check after auto-annotation to measure impact on error count
## 2025-06-05

```bash
docker compose -f docker-compose.yml down -v --remove-orphans
```
# Stopped and removed all containers, volumes, and networks defined in the repo's docker-compose file to ensure a clean environment before test troubleshooting.
```bash
docker ps -aq --filter name=codestory | xargs -r docker rm -f
```
# Removed any stray Docker containers with names matching "codestory" to ensure no project-related containers remain running outside of docker-compose management.