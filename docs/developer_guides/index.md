# Developer Guides

These guides are intended for developers who want to contribute to Code Story, extend its functionality, or integrate it with other systems.

## Development Environment

- [Environment Setup](environment_setup.md) - Setting up a development environment
- [Testing](testing.md) - Running tests and writing new ones

## Extending Code Story

Code Story is designed to be extensible. These guides explain how to extend different aspects of the system:

- [Creating Pipeline Steps](extending/pipeline_steps.md) - Adding new ingestion pipeline steps
- [Adding MCP Tools](extending/mcp_tools.md) - Creating new tools for the MCP adapter
- [Adding API Endpoints](extending/api_endpoints.md) - Extending the REST API

## Architecture Deep Dives

For a deeper understanding of the system's architecture and design decisions:

- [Azure OpenAI Client](azure_openai_client.md) - Details on the Azure OpenAI integration
- [Ingestion Pipeline](ingestion_pipeline.md) - In-depth guide to the ingestion pipeline
- [MCP Adapter](mcp_adapter.md) - Technical details of the MCP implementation
- [Summarizer Step](summarizer_step.md) - Deep dive into the summarization process

## Infrastructure

- [Deployment Testing](deployment_testing.md) - Testing deployment configurations
- [Disaster Recovery](disaster_recovery.md) - Backup and recovery procedures

## Code Conventions

Code Story follows a set of conventions for code organization and style:

### Python Conventions

- Follow PEP 8 style guide with Ruff enforcement
- Use Google-style docstrings
- Type annotations for all functions and methods
- Dependency injection for testability
- Abstract base classes for interfaces

### TypeScript/React Conventions

- Use functional components with hooks
- Redux for state management
- TypeScript interfaces for all props and state
- Jest and React Testing Library for tests

### Testing Conventions

- Unit tests for all components
- Integration tests for key functionality
- Test doubles (mocks, stubs) for external dependencies
- Pytest for Python tests
- Jest for JavaScript/TypeScript tests

## Contribution Workflow

If you want to contribute to Code Story:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests for your changes
5. Run the test suite
6. Submit a pull request

For detailed contribution guidelines, see the [Contributing](../contributing.md) page.