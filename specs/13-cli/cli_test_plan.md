# CLI Test Plan

This document outlines the comprehensive testing strategy for the Code Story CLI.

## 1. Unit Tests

### 1.1 Command Registration Tests
- Test that all commands are properly registered
- Test that command aliases work correctly
- Test that help text is displayed correctly for each command

### 1.2 Command Argument Parsing Tests
- Test required arguments are enforced
- Test optional arguments have correct defaults
- Test validation of argument formats (paths, URLs, run IDs)
- Test handling of invalid arguments

### 1.3 Client API Tests
- Test ServiceClient initialization
- Test request construction
- Test response parsing
- Test error handling
- Test authentication mechanism

### 1.4 Output Formatting Tests
- Test Rich table formatting
- Test progress bar display
- Test error message formatting
- Test JSON formatting option

### 1.5 Configuration Handling Tests
- Test reading configuration
- Test validation of configuration updates
- Test writing configuration changes

## 2. Integration Tests

### 2.1 Service Management Tests
- Test `service start` when service is not running
- Test `service start` when service is already running
- Test `service stop` when service is running
- Test `service stop` when service is not running
- Test automatic service start when running other commands
- Test handling of service connection errors
- Test service status display

### 2.2 Ingestion Tests
- Test `ingest` with local directory path
- Test `ingest` with Git repository URL
- Test `ingest` progress reporting
- Test `ingest jobs` listing all jobs
- Test `ingest stop` stopping a running job
- Test `status` for completed job
- Test `status` for running job
- Test `status` for failed job
- Test handling of invalid job IDs

### 2.3 Query Tests
- Test `query` with simple Cypher
- Test `query` with complex Cypher
- Test `query` with MCP tool call
- Test `query` result formatting
- Test `ask` with natural language query
- Test handling of invalid queries
- Test query pagination
- Test query timeout handling

### 2.4 Configuration Tests
- Test `config show` displays current config
- Test `config show --sensitive` includes sensitive values
- Test `config KEY=VALUE` updates single value
- Test `config` with multiple KEY=VALUE pairs
- Test interactive configuration editor

### 2.5 Visualization Tests
- Test `visualize` generates valid HTML
- Test visualization with small graph
- Test visualization with large graph
- Test visualization with no data
- Test visualization styling and interactivity

### 2.6 UI Tests
- Test `ui` opens browser with correct URL
- Test handling when browser cannot be opened

### 2.7 Error Handling Tests
- Test handling of network errors
- Test handling of service unavailability
- Test handling of authentication failures
- Test handling of timeout errors
- Test handling of unexpected server errors

## 3. Mocking Strategy

For unit tests, we'll mock:
- HTTP responses from the Code Story service
- Redis pub/sub for progress updates
- Browser opening functionality
- File system operations

For integration tests, we'll:
- Use a real Code Story service instance
- Create a test database with known test data
- Capture and verify CLI output
- Verify side effects (e.g., configuration changes)

## 4. Test Fixtures

- `mock_service_client`: Mocked ServiceClient for unit tests
- `test_repo`: Sample repository for ingestion tests
- `test_config`: Test configuration with known values
- `test_graph`: Neo4j database with test graph data
- `cli_runner`: Custom test runner to capture CLI output

## 5. Test Execution

Tests will be executed in the following order:
1. Unit tests in isolation
2. Integration tests with mocked services
3. Integration tests with real services

Each test should be independent and should clean up after itself to avoid affecting other tests.