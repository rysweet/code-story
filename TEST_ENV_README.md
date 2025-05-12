# Test Environment Setup

This document describes how to set up and run the tests for the Code Story project.

## Prerequisites

The following services are required to run the integration tests:

1. **Neo4j** - A graph database
2. **Redis** - A in-memory data structure store
3. **Python 3.12+** - With all dependencies installed

## Environment Setup

### 1. Start Test Services

Start the Neo4j and Redis test instances:

```bash
docker-compose -f docker-compose.test.yml up -d
```

This will start:

#### Neo4j:
- HTTP on port 7475 (http://localhost:7475)
- Bolt on port 7688 (bolt://localhost:7688)
- Username: neo4j
- Password: password
- Database: codestory-test

#### Redis:
- Port 6380 (redis://localhost:6380)
- Dedicated test instance to avoid interfering with your development Redis

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

By default, all integration tests that use Neo4j and Celery now run automatically, as these are considered core components of the system. Only OpenAI-dependent tests are skipped by default to avoid requiring external API keys.

If needed, you can skip specific test categories with these flags:

- `--skip-neo4j` - Skip tests that require Neo4j
- `--skip-celery` - Skip tests that require Celery
- `--skip-openai` - Skip tests that require OpenAI API access (default behavior)
- `--run-openai` - Enable tests that require OpenAI API access (deprecated but still supported)

Example:

```bash
# Run all integration tests (except OpenAI)
python -m pytest tests/integration/

# Run all integration tests including OpenAI
python -m pytest tests/integration/ --run-openai

# Run tests but skip Neo4j-dependent ones
python -m pytest tests/integration/ --skip-neo4j

# Run specific integration test for the summarizer
python -m pytest tests/integration/test_ingestion_pipeline/test_summarizer_integration.py
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

## Test Categories

The project has several test categories, each with specific requirements:

1. **Unit Tests** - No external dependencies, always run
2. **Neo4j Tests** - Require Neo4j database, run by default
3. **Celery Tests** - Require Redis/Celery, run by default
4. **OpenAI Tests** - Require OpenAI API access, skipped by default

Integration tests may have multiple markers. For example, a test might require both Neo4j and Celery.

To see which tests are skipped and why:

```bash
# Run with verbose flag to see skip reasons
python -m pytest -v tests/integration/
```

Tests marked with `@pytest.mark.skip` or `@pytest.mark.skipif` have specific conditions that must be met, independent of the command line options.