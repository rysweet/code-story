# Ingestion Pipeline Integration Tests

This directory contains integration tests for the ingestion pipeline. These tests verify that the pipeline can correctly process a repository and store its structure in the Neo4j database.

## Requirements

To run these tests, you need:

1. A running Neo4j database
2. A running Redis server
3. Celery workers for the ingestion pipeline

## Setup

### Neo4j

You can start a Neo4j test database using the provided script:

```bash
./scripts/setup_test_db.sh
```

This will start a Neo4j container with the required configuration. Alternatively, you can use your own Neo4j instance and set the following environment variables:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=your-password
export NEO4J_DATABASE=neo4j
```

### Redis

You can start a Redis server using Docker:

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

Set the Redis URI environment variable:

```bash
export REDIS_URI=redis://localhost:6380/0
```

### Celery Workers

Start a Celery worker for the ingestion pipeline:

```bash
cd /path/to/code-story
celery -A src.codestory.ingestion_pipeline.celery_app:app worker -l info -Q ingestion
```

## Running the Tests

To run the integration tests, use pytest with the following options:

```bash
# Run all Neo4j-related tests
python -m pytest tests/integration/test_ingestion_pipeline/ --run-neo4j

# Run tests that require both Neo4j and Celery
python -m pytest tests/integration/test_ingestion_pipeline/ --run-neo4j --run-celery

# Run a specific test
python -m pytest tests/integration/test_ingestion_pipeline/test_filesystem_integration.py::test_filesystem_step_run --run-neo4j
```

## Test Coverage

These tests cover:

1. **FileSystemStep Integration**: Tests that the FileSystemStep can process a repository, store its structure in Neo4j, and handle incremental updates.

2. **Pipeline Manager Integration**: Tests that the PipelineManager can orchestrate workflow steps, manage job status, and handle errors.

3. **Step Dependencies and Execution Order**: Tests that steps are executed in the correct order based on their dependency relationships.

The tests create a temporary repository structure and use it to verify that:

- Files and directories are correctly identified
- Directory hierarchy is preserved
- Ignored patterns are respected
- Incremental updates work correctly
- The pipeline can be stopped and restarted
- Steps are executed in the correct order based on their dependencies

## Testing Step Dependencies and Execution Order

The approach for testing step dependencies is to observe the execution order of steps during pipeline runs:

1. **Dependency Resolution**: When a step with dependencies is requested, all its dependencies should be executed first
   - Example: When `summarizer` is requested, `filesystem` and `blarify` should be executed first
   - Example: When `documentation_grapher` is requested, only `filesystem` should be executed first

2. **Execution Order**: Steps should be executed in an order that respects their dependencies
   - Example: `filesystem` should always execute before `blarify`
   - Example: `blarify` should always execute before `summarizer`

3. **Error Handling**: When a dependency fails, dependent steps should not be executed
   - Example: If `filesystem` fails, `blarify` and `summarizer` should not execute

The PipelineManager handles dependencies through the configuration in pipeline_config.yml. The steps are executed in sequential order as defined in the configuration file. Check test_pipeline_integration.py and test_full_pipeline_integration.py for examples of dependency testing.