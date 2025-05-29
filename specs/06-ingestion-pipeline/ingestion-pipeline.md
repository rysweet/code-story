# 6.0 Ingestion Pipeline

**Previous:** [AI Client](../05-ai-client/ai-client.md) | **Next:** [Blarify Workflow Step](../07-blarify-step/blarify-step.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)

**Used by:**
- [Code Story Service](../11-code-story-service/code-story-service.md)

**Uses:**
- [Blarify Workflow Step](../07-blarify-step/blarify-step.md)
- [FileSystem Workflow Step](../08-filesystem-step/filesystem-step.md)
- [Summarizer Workflow Step](../09-summarizer-step/summarizer-step.md)
- [Documentation Grapher Step](../10-docgrapher-step/docgrapher-step.md)

## 6.1 Purpose

**Ingestion Pipeline** is a library that can be embedded into the a service such as the code-story service that runs all of the steps in the ingestion workflow. Each step is a plug‑in. System can be extended by adding new plugins.  Each step in the workflow is an independent module that is not part of the ingestion pipeline. The order of execution is governed by a configuration file. Ingestion module workflow steps are python modules that implement the `PipelineStep` interface. The pipeline is a Celery task queue and workers for running the ingestion pipeline. The pipeline will run in a container locally or in Azure Container Apps.

## 6.2 Responsibilities

- When a new ingestion job is started, the pipeline will run all of the steps in the ingestion workflow in the order specified in the configuration file.
- The Ingestion Pipeline library will have methods for starting, stopping, and managing the status of ingestion jobs.
- The Ingestion Pipeline will consist of multiple workflow steps that can be added or modified as needed.
- The Ingestion Pipeline will have a configuration file that specifies the order of execution of the workflow steps.
- When workflows fail, the pipeline will be able to retry the failed steps or the entire workflow.
- Workflow steps can optionally have an "Ingestion Update" mode that will update the graph with the results of the step without running the entire pipeline.
- Each workflow step will log its execution status and any errors encountered during processing.

## 6.3 Architecture and Code Structure

---

## 6.3a Async Task Management & Control

### Overview

The ingestion pipeline supports advanced async task management features to enable robust, scalable, and user-controllable workflows. These include:

- Task cancellation and termination
- Priority queueing
- Resource management and throttling
- Task dependency tracking and ordering
- Task monitoring and progress reporting
- Retry and failure recovery
- Task scheduling and delayed execution
- Performance monitoring

### Features & Design

- **Task Cancellation:**
  Users can cancel running or pending ingestion tasks via API/CLI. The pipeline uses Celery's `revoke` API with `terminate=True` and ensures workflow steps check for revocation for graceful shutdown.

- **Priority Queues:**
  Multiple Celery queues (e.g., high, default, low) are supported. Task priority is accepted via API/CLI and routed to the appropriate queue. Worker configuration ensures high-priority tasks are processed first.

- **Resource Management:**
  Worker concurrency and resource tags are configurable. Optionally, a resource manager (e.g., Redis-based tokens) can be used to throttle resource usage. Resource usage and limits are exposed via API.

#### Resource Management & Throttling (Implementation Details)

- The ingestion pipeline enforces resource throttling using a Redis-backed token bucket.
- The maximum number of concurrent ingestion steps is configurable via `resource_max_tokens` in settings.
- Before each step runs, a token is acquired from Redis; if no tokens are available, the step is blocked or fails with a throttling error.
- After the step completes (success or failure), the token is released.
- The current number of available tokens and the configured maximum are exposed via the API endpoint:
  `GET /v1/ingest/resource_status`
- This endpoint returns a JSON object:
  `{ "available_tokens": <int>, "max_tokens": <int> }`
- Integration tests verify that resource limits are enforced and reported correctly.
- This mechanism prevents overloading the system and allows for dynamic adjustment of resource usage.

- **Dependency Tracking:**
  Task chains/groups/chords are used to express dependencies between workflow steps. The API can accept dependency information, ensuring correct execution order.

- **Monitoring & Progress:**
  Task status and progress are reported via Celery's result backend and `update_state`. Real-time updates are streamed to clients via WebSocket and API endpoints.

- **Retry & Failure Recovery:**
  Retry policies (max retries, backoff) are configurable per step. Retry/failure info is exposed via API, and tests cover failure/retry scenarios.

- **Scheduling:**
  Tasks can be scheduled for future execution using Celery's `eta`/`countdown` parameters, with API/CLI support for delayed jobs.

- **Performance Monitoring:**
  Task execution metrics (duration, resource usage) are collected and exposed via API and/or Prometheus.

### Implementation Notes

- All features are reflected in the pipeline configuration, API, and plugin step interfaces.
- See section 6.5 for updated API and step requirements.
- See section 6.8 for updated user stories and acceptance criteria.

#### Task Cancellation API and Implementation

- **API Endpoint:**  
  The ingestion pipeline exposes a cancellation endpoint:  
  `POST /v1/ingest/{job_id}/cancel`  
  This endpoint cancels a running or pending ingestion job by revoking the associated Celery task with `terminate=True`.

- **Graceful Cancellation:**  
  The pipeline orchestration and step tasks periodically check for task revocation using Celery's `is_revoked()` API. If a task is revoked, it exits early and updates the job status to `CANCELLED`. This ensures that both pending and running jobs can be cancelled cleanly.

- **Testing:**  
  Integration tests cover:
  - Cancelling a running job and verifying it transitions to `CANCELLED`
  - Cancelling a pending job and verifying it transitions to `CANCELLED`
  - Attempting to cancel a completed job (should remain `COMPLETED`)

- **User Story:**  
  As a user, I can cancel ingestion jobs via API/CLI and expect the pipeline to stop promptly and report the cancellation status.
---

The Ingestion Pipeline orchestrates standalone “step” modules—discovered via entry points—and uses Redis-backed Celery for task management. Steps live in separate plugin packages, allowing extensibility without modifying the core pipeline.

1. **Pipeline Manager**  
   - **Location**: `src/codestory/ingestion_pipeline/manager.py`  
   - **Responsibilities**:  
     - Load `pipeline_config.yml` (at project root) defining the ordered list of step names and per-step options (concurrency, retries).  
     - Discover registered steps via the `codestory.pipeline.steps` entry-point group declared by each plugin.  
     - Invoke each step’s Celery task, passing the repository path and config.  
     - Aggregate step statuses and expose overall pipeline status to the Code Story Service.

2. **Plugin Discovery & Step Modules**  
   - **Entry-Point Registration** (in each plugin’s `pyproject.toml`):  
     ```toml
     [project.entry-points."codestory.pipeline.steps"]
     blarify = "codestory_blarify.step:BlarifyStep"
     filesystem = "codestory_filesystem.step:FileSystemStep"
     summarizer = "codestory_summarizer.step:SummarizerStep"
     documentation_grapher = "codestory_docgrapher.step:DocumentationGrapherStep"
     ```  
   - **Plugin Packages** (examples):  
     - `src/codestory_blarify/step.py`  
     - `src/codestory_filesystem/step.py`  
     - `src/codestory_summarizer/step.py`  
     - `src/codestory_docgrapher/step.py`

3. **Redis-Backed Celery Integration**  
   - **Docker Compose** (`docker-compose.yaml` snippet):  
     ```yaml
     services:
       redis:
         image: redis:7-alpine
         ports:
           - "6379:6379"
     ```  
   - **Celery App** (`src/codestory/ingestion_pipeline/celery_app.py`):  
     ```python
     from celery import Celery

     app = Celery(
         'ingestion_pipeline',
         broker='redis://redis:6379/0',
         backend='redis://redis:6379/1',
     )
     app.autodiscover_tasks()  # Discovers tasks in all installed apps
     ```  
   - **Task Definition** (example in plugin):  
     ```python
     from ingestion_pipeline.celery_app import app
     from codestory_blarify.step import BlarifyStep

     @app.task(name="codestory.pipeline.steps.blarify.run", bind=True)
     def run(self, repository_path, config):
         return BlarifyStep().run(repository_path, **config)
     ```

4. **Configuration File**  
   - `pipeline_config.yml`:
   ```yaml
   steps:
     - name: blarify
       concurrency: 1
     - name: filesystem
       concurrency: 1
     - name: summarizer
       concurrency: 5
     - name: documentation_grapher
       concurrency: 2
   retry:
     max_retries: 3
     back_off_seconds: 10
   ```

5. **Directory Layout**  
   ```text
   src/
   ├── codestory/ingestion_pipeline/
   │   ├── manager.py           # Orchestration logic
   │   ├── celery_app.py        # Celery instance & Redis settings
   │   └── utils.py             # Shared helpers (logging, metrics)
   ├── codestory_blarify/       # Blarify plugin package
   │   └── step.py              # BlarifyStep implementation
   ├── codestory_filesystem/    # FileSystem plugin package
   │   └── step.py              # FileSystemStep implementation
   ├── codestory_summarizer/    # Summarizer plugin package
   │   └── step.py              # SummarizerStep implementation
   └── codestory_docgrapher/    # DocumentationGrapher plugin package
       └── step.py              # DocumentationGrapherStep implementation
   ```
	
6.	Error Handling & Observability
	•	Celery’s retry and back-off configured via pipeline_config.yml.
	•	Each step logs to the centralized logger (OpenTelemetry → Prometheus).
	•	A health-check endpoint (/v1/ingest/health) in the Code Story Service verifies Redis connectivity and worker status.


## 6.4 Ingestion Pipeline Workflow Steps

The following steps are the default workflow of the ingestion pipeline but are separate modules, not part of the Ingestion Pipeline module. 

   - *BlarifyStep* runs [Blarify](https://github.com/blarApp/blarify) to parse the codebase and store the raw AST in the **Graph Service**.
   - *Summariser* computes a DAG of code dependencies and walks from leaf nodes to the top and computes summaries for each module using the Azure AI model endpoints and stores them in the **Graph Service**.
   - *FileSystemStep* creates a graph of the filesystem layout of the codebase and links it to the AST nodes.
   - *DocumentationGrapher* creates a knowledge graph of the documentation and links it to the relevant AST, Filesystem, and Summary nodes.

## 6.5 Workflow Steps API

Each workflow step must implement the following operations, inherited from the `PipelineStep` interface:

- `run(repository, **options)`: Run the workflow step with the specified configuration and input data (location of the repo, neo4j connection information, etc.). Supports options for priority, scheduling, dependencies, and resource tags. Returns a job identifier.
- `status(job_id)`: Check the status of the workflow step. Returns the current status (e.g., running (% complete), completed, failed), progress, and resource usage.
- `stop(job_id)`: Stop the workflow step. Returns the current status.
- `cancel(job_id)`: Cancel the workflow step. Returns the current status. Steps must periodically check for revocation and terminate gracefully.
- `ingestion_update(repository)`: Update the graph with the results of the workflow step without running the entire pipeline. Returns a job_id.
- `dependencies(job_id)`: (Optional) Return a list of job_ids this step depends on.
- `retry(job_id)`: (Optional) Retry a failed or cancelled job.
- `schedule(repository, eta/countdown, **options)`: (Optional) Schedule a step for future execution.

All steps must support progress reporting via `update_state` and log resource usage for monitoring.


## 6.6 Code Example of calling the Ingestion Pipeline

```python
import time
from codestory.ingestion_pipeline.manager import PipelineManager

def run_ingestion():
    # 1. Path to the repository you want to ingest
    repo_path = "/path/to/your/codebase"

    # 2. Initialize the PipelineManager with the config file
    manager = PipelineManager(config_path="pipeline_config.yml")

    # 3. Kick off a new ingestion job
    job_id = manager.start_job(repository_path=repo_path)
    print(f"Started ingestion job: {job_id}")

    # 4. Poll the job status until it completes or fails
    while True:
        status = manager.status(job_id)
        print(f"[{job_id}] Status: {status}")
        if status in ("COMPLETED", "FAILED"):
            break
        time.sleep(5)

    # 5. Check final outcome
    if status == "COMPLETED":
        print("✅ Ingestion pipeline completed successfully.")
    else:
        print("❌ Ingestion pipeline failed. Check logs for details.")

if __name__ == "__main__":
    run_ingestion()
```
The above code shows how to use the Ingestion Pipeline to run the ingestion process. The `PipelineManager` class is used to start a new ingestion job, check the status of the job, and stop or cancel the job if needed. The `pipeline_config.yml` file is used to configure the order of execution of the workflow steps and their parameters.

## 6.7 Repository Mounting

When running the ingestion pipeline in Docker, repositories must be properly mounted to the Docker containers. This section describes the repository mounting process.

### 6.7.1 Automatic Repository Mounting

The CLI provides fully automated repository mounting:

```bash
# Simply run the ingestion command - everything else is automatic
codestory ingest start /path/to/your/repository
```

The CLI performs the following steps:
1. Detects if connected to a containerized service
2. Checks if the repository is already properly mounted
3. Automatically mounts the repository if needed
4. Restarts containers with proper volume mounts if required
5. Maps local paths to container paths for proper access
6. Starts the ingestion process

### 6.7.2 Repository Mount Architecture

Repository mounting involves several components:

1. **Docker Volume Mapping**: Each repository is mounted with a specific path mapping:
   ```
   /path/on/host/repository -> /repositories/repository-name
   ```

2. **Mount Detection**:
   - The CLI checks if repositories exist in containers via `docker exec`
   - Verification ensures paths are accessible to service and worker containers

3. **Docker Compose Configuration**:
   ```yaml
   services:
     worker:
       volumes:
         - ${REPOSITORY_SOURCE}:${REPOSITORY_DEST}
     service:
       volumes:
         - ${REPOSITORY_SOURCE}:${REPOSITORY_DEST}
   ```

4. **Auto-Mount Script**:
   - Creates docker-compose.override.yml for custom mounts
   - Sets up environment variables for Docker Compose
   - Handles container restart when necessary
   - Verifies successful mounting before proceeding

5. **CLI Integration**:
   - The CLI detects Docker deployments automatically
   - Maps paths between host and container transparently
   - Supports command-line options for custom mounting behavior

### 6.7.3 Repository Mount Operations

The auto_mount.py script provides these operations:
- `setup_repository_mount(repo_path)`: Mounts a repository and configures containers
- `is_repo_mounted(repo_path)`: Checks if a repository is properly mounted
- `wait_for_service()`: Waits for containers to become healthy
- `create_repo_config(repo_path)`: Creates repository configuration files

The CLI ingest command supports these options:
- `--auto-mount`: Explicitly enable automatic mounting (on by default)
- `--no-auto-mount`: Disable automatic repository mounting
- `--path-prefix`: Specify custom container mount path
- `--container`: Force container path mapping

### 6.7.4 Parameter Filtering

To avoid parameter conflicts between different pipeline steps, the CeleryAdapter and ingestion pipeline implement parameter filtering:

1. **Step-Specific Parameter Handling**:
   - Different steps may require different parameters
   - Parameter filtering prevents "unexpected keyword argument" errors
   - Each step receives only the parameters it can handle

2. **Implementation Details**:
   - The CeleryAdapter filters parameters based on step type:
     ```python
     # Filter options for Blarify step
     if step_name == "blarify":
         # Blarify step doesn't use certain parameters
         filtered_options = {k: v for k, v in options.items() 
                           if k not in ['concurrency']}
         step_config.update(filtered_options)
     ```

3. **Parameter Categories**:
   - **Common Parameters**: Used by all steps (e.g., `job_id`, `repository_path`)
   - **Step-Specific Parameters**: Used only by certain steps
   - **Safe Parameters**: A set of parameters that work across multiple steps

4. **Benefits**:
   - Prevents runtime errors due to parameter mismatches
   - Allows consistent configuration across different deployment environments
   - Simplifies adding new parameters to specific steps without breaking others

## 6.8 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want the ingestion pipeline to execute workflow steps in a configurable order so that I can easily manage and modify the ingestion process. | • Workflow steps execute in the order specified by the configuration file.<br>• Changing the configuration file updates the execution order without code changes. |
| As a developer, I want to be able to start, stop, cancel, and monitor ingestion jobs so that I can control and track the ingestion process effectively. | • Methods exist to start, stop, cancel, and check the status of ingestion jobs.<br>• Job statuses and progress are accurately reported and logged.<br>• Users can cancel long-running tasks via API/CLI. |
| As a developer, I want the ingestion pipeline to support adding new workflow steps as plugins so that I can extend the system functionality without modifying core pipeline code. | • New workflow steps can be added as plugins without altering existing pipeline code.<br>• Newly added plugins are recognized and executed by the pipeline. |
| As a developer, I want the ingestion pipeline to retry failed workflow steps or entire workflows so that transient errors do not require manual intervention. | • Failed workflow steps can be retried individually.<br>• Entire workflows can be retried from the beginning.<br>• Retry attempts are logged clearly.<br>• Retry/failure info is exposed via API. |
| As a developer, I want workflow steps to optionally support an "Ingestion Update" mode so that I can update the graph incrementally without rerunning the entire pipeline. | • Workflow steps can be executed individually in "Ingestion Update" mode.<br>• Graph updates occur correctly without executing unrelated steps. |
| As a developer, I want to schedule ingestion jobs and set task priorities so that I can optimize resource usage and workflow timing. | • API/CLI supports scheduling jobs for future execution.<br>• Priority parameter is accepted and high-priority tasks are processed first.<br>• Resource usage is controlled and monitored. |
| As a developer, I want to define dependencies between workflow steps so that tasks execute in the correct order. | • Task dependencies are respected in execution order.<br>• API accepts dependency information.<br>• Dependent tasks wait for prerequisites to complete. |
| As a developer, I want detailed logging and monitoring of workflow step execution, progress, and performance so that I can easily diagnose and resolve issues. | • Execution status, progress, resource usage, and errors for each workflow step are logged and exposed via API/WebSocket.<br>• Performance metrics are collected and available for monitoring. |
| As a user, I want repositories to be automatically mounted when using Docker so that I don't need to manually configure volume mounts. | • CLI automatically detects when repository mounting is needed.<br>• Repositories are mounted correctly in Docker containers.<br>• Users don't need to manually edit docker-compose files. |
| As a developer, I want clear errors when repository mounting fails so that I can easily diagnose and fix mounting issues. | • Clear error messages explain mounting problems.<br>• Specific troubleshooting steps are provided.<br>• Detailed diagnostic information is available when needed. |

---

