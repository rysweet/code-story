# Prompt History - Fix Dependency Trigger Logic

## Prompt 1 (2025-06-17 07:41)

**Prompt**: Fix `tests/integration/test_ingestion_pipeline/test_step_dependencies.py::test_job_dependency_orchestration` failure where Job B stays in the **waiting** queue after Job A (its dependency) completes. Root cause is likely in `IngestionService._check_and_trigger_dependents`, which should dequeue / start dependent jobs but currently leaves them flagged "waiting".

**Response**: 
- Identified the issue in `_check_and_trigger_dependents` method in [`src/codestory_service/application/ingestion_service.py`](src/codestory_service/application/ingestion_service.py:371)
- The method correctly deletes the waiting key but incorrectly calls `start_ingestion()` again which creates a new job
- Need to fix the logic to transition the existing waiting job to started/queued state instead
- Will update the method to properly enqueue the job using existing helpers