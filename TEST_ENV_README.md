# Test Environment Setup

This document describes how to set up and run the tests for the Code Story project.

## Prerequisites

The following services are required to run the integration tests:

1. **Neo4j** - A graph database
2. **Redis** - A in-memory data structure store
3. **Python 3.12+** - With all dependencies installed

## Environment Setup

### 1. Start Neo4j Test Instance

To start the Neo4j test database:

```bash
docker-compose -f docker-compose.test.yml up -d neo4j
```

This will start a Neo4j instance with:
- HTTP on port 7475 (http://localhost:7475)
- Bolt on port 7688 (bolt://localhost:7688)
- Username: neo4j
- Password: password
- Database: codestory-test

### 2. Python Environment Setup

Ensure you have installed all Python dependencies:

```bash
pip install -e .
pip install -e ".[dev]"
```

## Running Tests

### Unit Tests

Run unit tests with:

```bash
python -m pytest tests/unit/
```

### Integration Tests

Integration tests require additional flags to enable specific test components:

- `--run-neo4j` - Enable tests that require Neo4j
- `--run-celery` - Enable tests that require Celery
- `--run-openai` - Enable tests that require OpenAI API access

Example:

```bash
# Run all integration tests with Neo4j and Celery support
python -m pytest tests/integration/ --run-neo4j --run-celery

# Run specific integration test for the summarizer
python -m pytest tests/integration/test_ingestion_pipeline/test_summarizer_integration.py --run-neo4j --run-celery
```

## Troubleshooting

### Neo4j Connection Issues

If you encounter Neo4j connection issues:

1. Verify the Neo4j container is running:
   ```bash
   docker ps | grep neo4j
   ```

2. Check Neo4j logs:
   ```bash
   docker logs codestory-neo4j-test
   ```

3. Test connection with the Python client:
   ```python
   from codestory.graphdb.neo4j_connector import Neo4jConnector
   conn = Neo4jConnector(
       uri='bolt://localhost:7688',
       username='neo4j',
       password='password',
       database='codestory-test'
   )
   print(conn.execute_query('MATCH (n) RETURN count(n) as count'))
   conn.close()
   ```

### Celery Task Issues

For Celery-related issues:

1. Check that tests are running with `--run-celery` flag
2. Set these environment variables for Celery:
   ```bash
   export REDIS_URI=redis://localhost:6379/0
   ```

## Skipped Tests

Many integration tests are skipped by default to avoid requiring external services for regular test runs. Always check the test markers to understand why a test is skipped and which flags are required to enable it.