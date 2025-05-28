# Coding Guidelines

## General Standards

- Use the latest stable versions of each language and framework where possible
- Follow the conventions for each language WRT code formatting, linting, and testing
- Where possible use tools for linting and formatting checks
- Ensure that all tests are run and pass before merging any changes
- Use pre-commit hooks to ensure that all code is linted and formatted before committing
- Use continuous integration tools to automate testing and ensure code quality

## Modularity

- Maintain clear separation between different concerns (e.g., knowledge ingestion, code ingestion, analysis)
- Create dedicated modules for distinct functionality
- Use composition over inheritance where appropriate
- Design for extensibility with interfaces and dependency injection
- Follow the module structure established in the codebase (shared, code_analysis, etc.)

## Code Reuse

- Before creating new code, investigate existing code for reusable components
- Extract shared code into dedicated utility modules
- Avoid duplicating functionality across different modules
- Prefer composition and delegation over inheritance for code reuse
- Create reusable abstractions for common patterns
- Utilize the shared module for cross-cutting concerns

## Design Patterns

- Use the Strategy pattern for varying behaviors
- Apply the Factory pattern for object creation where appropriate
- Implement interfaces (abstract base classes) for polymorphic behavior
- Use composition to combine behaviors flexibly
- Follow established patterns in the codebase for consistency

## Function/Method Design

- Keep functions and methods short (generally under 50 lines)
- Each function should have a single responsibility
- Extract complex logic into smaller, well-named helper functions
- Limit function parameters (generally 5 or fewer)
- Use descriptive naming that indicates purpose

## Error Handling

- Handle errors explicitly at appropriate levels
- Use specific exception types rather than generic exceptions
- Document expected exceptions in function docstrings
- Log errors with appropriate context before re-raising