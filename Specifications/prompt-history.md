# Prompt History

## Prompt 97 (May 29, 2025)

**Prompt**: Proceed with Milestone 6 from the async task-management plan: **Retry & Failure Recovery**.

Scope
1. Configure Celery retry/back-off policies per step; allow max retries and back-off in `pipeline_config.yml`.
2. Update task code to call `self.retry()` on transient errors; ensure idempotency.
3. Persist retry/failure info and expose via status API (`/v1/ingest/{job_id}`) and WebSocket events.
4. Add CLI/GUI visibility for retry counts and last-error message.
5. Tests (unit + integration): simulate transient failures, verify automatic retry and eventual success/failure reporting.
6. Specs/docs: update sections on retry/failure handling.
7. Run all checks/tests before each commit.

ONLY implement this milestone; do not start the next one yet.  
Finish with attempt_completion summarizing the changes and next steps.

**Response**:
- Updated `pipeline_config.yml` to support per-step and global retry/back-off config
- Updated config loader and manager to propagate retry/back-off settings to each step
- Refactored Celery step task to use per-step retry/back-off, call `self.retry()` on transient errors, and persist `retry_count`/`last_error`
- Extended status API, WebSocket, CLI, and GUI models to expose retry/failure info per step
- Added integration test to simulate transient failures and verify retry/failure reporting
- Updated ingestion pipeline spec addendum to document retry/failure handling and visibility
- Fixed all linter and type errors; ran all checks and tests to validate implementation

## Prompt 98 (May 29, 2025)

**Prompt**: Proceed with the remaining milestones in a single continuous effort to fully resolve issue #42:

Milestone 7 – **Scheduling / Delayed Execution**  
1. Add scheduling support (`eta` / `countdown`) to ingestion API & CLI.  
2. Persist schedule metadata; enqueue delayed jobs.  
3. Tests: verify delayed execution works.  
4. Update specs/docs.

Milestone 8 – **Performance Monitoring & Metrics**  
1. Collect task metrics (duration, CPU%, memory MB).  
2. Expose metrics via API `/v1/ingest/resource_status` and Prometheus `/metrics`.  
3. Tests: verify metrics collection & exposure.  
4. Update specs/docs; ensure acceptance criteria met.

Run all checks/tests after each change. When both milestones are complete, use attempt_completion summarizing full issue resolution.

**Response**:
- Updated prompt history to log the new user request as Prompt 98 before any code or documentation changes
- Planned stepwise implementation for Milestone 7 (Scheduling/Delayed Execution) and Milestone 8 (Performance Monitoring & Metrics)
- Will update shell history after each command and run all checks/tests after each change
- Will update specs and documentation as part of each milestone
- Will use attempt_completion to summarize full issue resolution after both milestones are complete
## Prompt 99 (May 29, 2025)

**Prompt**: Continue implementation to fully resolve issue #42.

Remaining milestones to implement and validate:

Milestone 7 – Scheduling / Delayed Execution  
1. Add scheduling support (`eta` / `countdown`) to ingestion API & CLI.  
2. Persist schedule metadata; enqueue delayed jobs only at the scheduled time.  
3. Tests (unit + integration): verify delayed execution works end-to-end.  
4. Update specs/docs.

Milestone 8 – Performance Monitoring & Metrics  
1. Collect task metrics (duration, CPU %, memory MB).  
2. Expose metrics via API `/v1/ingest/resource_status` and Prometheus `/metrics`.  
3. Tests: verify metrics collection & exposure.  
4. Update specs/docs; ensure acceptance criteria met.

Run all checks and tests before each commit.  
When both milestones are complete, use `attempt_completion` summarizing full issue resolution.

**Response**:
- Updated prompt history to log the new user request as Prompt 99 before any code or documentation changes
- Planned stepwise implementation for Milestone 7 (Scheduling/Delayed Execution) and Milestone 8 (Performance Monitoring & Metrics)
- Will update shell history after each command and run all checks/tests after each change
- Will update specs and documentation as part of each milestone
- Will use attempt_completion to summarize full issue resolution after both milestones are complete