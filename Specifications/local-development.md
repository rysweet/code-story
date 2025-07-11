# Code Story: Local Development Guide

This guide outlines the recommended approach for local development using the simplified architecture, focusing on developer productivity and minimal resource usage.

## Development Environment Setup

### Prerequisites

- Python 3.12+
- SQLite 3.35+ (included with Python)
- Git
- Node.js 18+ (for GUI development)

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/code-story.git
   cd code-story
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"  # Install with development dependencies
   ```

4. **Create local configuration**:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your settings
   ```

## Local Development Workflow

### Running in Development Mode

The simplified architecture provides a single-command development mode:

```bash
python -m codestory.dev --config config.yaml
```

This will:
- Start the API service on http://localhost:8000
- Initialize the local database
- Set up file watchers for auto-reload
- Provide development-specific endpoints

### Component Development

#### Core Engine

To run just the core engine:

```bash
python -m codestory.core --config config.yaml
```

This mode is useful for debugging core functionality without the API service.

#### Pipeline Steps

To test a specific pipeline step:

```bash
python -m codestory.pipeline.test_step --step filesystem --repo /path/to/repo
```

#### API Service

To run the API service with hot reloading:

```bash
python -m codestory.api --reload --config config.yaml
```

#### GUI Development

To run the GUI development server:

```bash
cd src/codestory_gui
npm install  # First time only
npm run dev
```

This will start the React development server with hot module replacement.

## Testing

### Running Tests

The simplified architecture makes testing more straightforward:

```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/unit/test_storage
pytest tests/integration/test_pipeline

# Run with coverage
pytest --cov=codestory
```

### Test Database

Tests will automatically use an in-memory SQLite database by default, making them fast and isolated.

For integration tests that require a persistent database:

```bash
pytest tests/integration --test-db=sqlite:///:file:test.db:?mode=memory&cache=shared
```

## Debugging

### Debugging the API Service

To debug the API service:

```bash
python -m debugpy --listen 5678 --wait-for-client -m codestory.api
```

Then connect with your IDE's debugger to port 5678.

### Debugging Pipeline Steps

To debug a pipeline step:

```bash
python -m debugpy --listen 5678 --wait-for-client -m codestory.pipeline.debug_step --step summarizer
```

### Logging

Configure logging in your `config.yaml`:

```yaml
logging:
  level: DEBUG
  format: detailed  # or 'simple', 'json'
  file: logs/codestory.log  # Optional, logs to console if not specified
```

## Common Development Tasks

### Adding a New Pipeline Step

1. Create a new module in `src/codestory_mystep/`
2. Implement the `PipelineStep` interface
3. Register the step in `src/codestory_mystep/__init__.py`
4. Add tests in `tests/unit/test_mystep/`
5. Update configuration to include the new step

### Modifying the Graph Schema

1. Update the schema definition in `src/codestory/storage/schema.py`
2. Run the schema migration tool:
   ```bash
   python -m codestory.storage.migrate
   ```
3. Update any affected queries in the codebase

### Adding a New API Endpoint

1. Add the endpoint definition in `src/codestory/api/routes/`
2. Implement the handler function
3. Add tests in `tests/unit/test_api/`
4. Update the API documentation

## Performance Profiling

The simplified architecture includes built-in profiling tools:

```bash
# Profile API performance
python -m codestory.api --profile

# Profile pipeline step
python -m codestory.pipeline.profile_step --step blarify --repo /path/to/repo
```

Profiling results will be saved to the `profiles/` directory.

## Docker Development (Optional)

For developers who prefer containers, a simplified Docker setup is provided:

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up

# Build and start specific service
docker-compose -f docker-compose.dev.yml up api
```

This uses a minimal Docker configuration optimized for development.

## Neo4j Development (Optional)

For developers who need Neo4j functionality:

```bash
# Start Neo4j container
docker-compose -f docker-compose.neo4j.yml up -d

# Configure Code Story to use Neo4j
cp config.neo4j.yaml config.yaml
```

Then run the application as usual.

## Code Style and Linting

The project uses ruff for linting and formatting:

```bash
# Check code style
ruff check .

# Fix code style issues
ruff check --fix .
```

## Development Guidelines

### Module Separation

- Respect the module boundaries defined in the architecture
- Use dependency injection to maintain loose coupling
- Don't import directly from other modules except through public interfaces

### Error Handling

- Use appropriate exception types
- Provide meaningful error messages
- Handle errors at the appropriate level

### Configuration

- Add new configuration options to the schema
- Provide sensible defaults
- Document configuration options

### Testing

- Write unit tests for all new functionality
- Add integration tests for component interactions
- Use fixtures to simplify test setup

## Conclusion

This local development guide provides a streamlined approach for working with the simplified Code Story architecture. By following these guidelines, developers can enjoy a more productive and resource-efficient development experience without the overhead of the full microservices architecture.

The simplified architecture prioritizes developer productivity while maintaining the extensibility and modularity of the original design, making it ideal for local development on a single machine.
