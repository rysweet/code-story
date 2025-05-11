# CLI Integration Tests

This directory contains integration tests for the Code Story CLI. These tests verify that the CLI can properly communicate with a running Code Story service.

## Running the tests

To run these tests, you need a running Code Story service. The tests will check if the service is available at the default port (or the port specified in your configuration).

```bash
# Start the service in one terminal
python -m codestory_service.main

# Run the tests in another terminal
python -m pytest tests/integration/test_cli/
```

If the service is not running, the tests will be skipped with an appropriate message.

## Test structure

The tests are organized by command group:

- `test_service_integration.py`: Tests for the service management commands
- `test_ingest_integration.py`: Tests for the ingestion commands
- `test_query_integration.py`: Tests for the query and ask commands
- `test_config_integration.py`: Tests for the configuration commands

## Using markers

Tests are marked with `@pytest.mark.require_service` to indicate they require a running service. You can run only these tests with:

```bash
python -m pytest -m require_service
```

Or skip them with:

```bash
python -m pytest -m "not require_service"
```

Additionally, tests are marked with `@pytest.mark.integration` to indicate they are integration tests.

## Test fixtures

The main fixtures provided for these tests are:

- `running_service`: Ensures a running service is available and provides its URL and port
- `test_repository`: Creates a temporary repository structure for ingestion tests
- `cli_runner`: A Click test runner for invoking CLI commands

## Adding new tests

When adding new tests:

1. Use the `@pytest.mark.require_service` marker for tests that need a service
2. Use the `running_service` fixture to get service information
3. Use the `cli_runner` to invoke CLI commands
4. Check both the return code (`result.exit_code`) and the output content (`result.output`)