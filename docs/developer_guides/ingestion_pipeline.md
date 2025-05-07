# Ingestion Pipeline

The Ingestion Pipeline is a core component of Code Story that orchestrates the processing of code repositories. It runs multiple workflow steps that analyze the codebase, generate summaries, and build a knowledge graph in Neo4j.

## Architecture

The pipeline uses a plugin-based architecture with Celery for distributed task processing:

1. **Pipeline Manager**: The central orchestration component that coordinates the execution of workflow steps.
2. **Workflow Steps**: Pluggable components that perform specific processing tasks.
3. **Celery Integration**: Distributed task queue for parallel and asynchronous processing.
4. **Plugin Discovery**: Uses entry points to dynamically discover and load workflow steps.

## Core Components

### PipelineManager

The `PipelineManager` class is the main entry point for working with the ingestion pipeline. It provides methods to:

- Start new ingestion jobs
- Check job status
- Stop or cancel running jobs
- Run individual workflow steps

```python
from codestory.ingestion_pipeline import PipelineManager

# Create a manager with the default config
manager = PipelineManager()

# Start an ingestion job
job_id = manager.start_job("/path/to/repo")

# Check job status
status = manager.status(job_id)
print(f"Job status: {status['status']}")

# Stop a job if needed
manager.stop(job_id)
```

### PipelineStep Interface

All workflow steps must implement the `PipelineStep` interface, which defines the following methods:

```python
class MyCustomStep(PipelineStep):
    def run(self, repository_path, **config):
        # Process the repository
        return job_id

    def status(self, job_id):
        # Return job status
        return {"status": StepStatus.RUNNING, "progress": 50.0}

    def stop(self, job_id):
        # Stop the job
        return {"status": StepStatus.STOPPED}

    def cancel(self, job_id):
        # Cancel the job
        return {"status": StepStatus.CANCELLED}

    def ingestion_update(self, repository_path, **config):
        # Update the graph without running the full pipeline
        return job_id
```

### Configuration

The pipeline is configured using a YAML file, typically named `pipeline_config.yml`. This file defines:

- The workflow steps to run and their order
- Per-step configuration parameters
- Retry settings for failures

Example configuration:

```yaml
steps:
  - name: filesystem
    concurrency: 1
    ignore_patterns:
      - "node_modules/"
      - ".git/"

  - name: blarify
    concurrency: 1
    docker_image: "codestory/blarify:latest"
    timeout: 300

retry:
  max_retries: 3
  back_off_seconds: 10
```

## Adding a Custom Workflow Step

To create a new workflow step, follow these steps:

1. Create a new package with a module that implements the `PipelineStep` interface
2. Register the step using the entry point system in `pyproject.toml`
3. Add the step to the pipeline configuration

Example entry point registration:

```toml
[tool.poetry.plugins."codestory.pipeline.steps"]
my_custom_step = "codestory_mycustom.step:MyCustomStep"
```

## Running Tasks with Celery

The pipeline uses Celery to distribute processing across workers. To run the pipeline:

1. Start Redis (used as the message broker and result backend)
2. Start one or more Celery workers
3. Use the `PipelineManager` to start ingestion jobs

Example of starting a Celery worker:

```bash
celery -A src.codestory.ingestion_pipeline.celery_app:app worker -l info -Q ingestion
```

## Monitoring and Observability

The pipeline provides several metrics for monitoring:

- Number of ingestion jobs by status
- Number of workflow steps by status
- Duration of workflow steps
- Number of active ingestion jobs

These metrics are exposed via Prometheus and can be visualized in a dashboard.

## Testing

To test the ingestion pipeline, use the provided test script:

```bash
python scripts/test_ingestion_pipeline.py /path/to/repo
```

This script demonstrates how to use the pipeline and provides detailed progress information during processing.