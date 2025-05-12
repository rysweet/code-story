# CI/CD Troubleshooting Guide

This guide helps developers troubleshoot common issues with the CI/CD pipeline for the Code Story project.

## Common Python Test Issues

### Missing Dependencies

One of the most common issues in CI is missing dependencies. Here are some tips:

1. **Azure Extras**: Make sure to install the Azure extras when using Poetry:
   ```bash
   poetry install --extras azure
   ```

2. **Email Validator**: The project requires `email-validator` for certain functionality:
   ```bash
   pip install email-validator  # If not using Poetry
   # OR
   poetry add email-validator  # If using Poetry
   ```

3. **Transitive Dependencies**: Sometimes dependencies of dependencies aren't properly resolved. In these cases, explicitly install the missing module:
   ```bash
   pip install <missing-module>
   ```

### Celery Task Issues

1. **Anti-pattern**: Never use `.get()` inside a Celery task. This can cause deadlocks and timeouts, especially in CI environments with limited resources.

2. **Timeouts**: Set reasonable timeouts for all Celery operations, particularly in test environments:
   ```python
   # Good practice
   result = task.get(timeout=30)
   ```

3. **Service Dependencies**: Ensure Redis and other services are properly configured and running before tests that depend on them.

## Common GUI Test Issues

### JSDOM Environment Problems

1. **Environment Configuration**: Always specify the JSDOM environment when running Vitest:
   ```bash
   npm test -- --environment jsdom
   ```

2. **Document Not Defined**: If you encounter "document is not defined" errors, ensure:
   - Your test setup correctly initializes the JSDOM environment
   - You're using the proper imports from testing libraries
   - The test command includes `--environment jsdom`

3. **Mock Browser APIs**: For tests that use browser APIs, mock them in your setup file:
   ```typescript
   // Example for mocking window.matchMedia
   Object.defineProperty(window, 'matchMedia', {
     writable: true,
     value: vi.fn().mockImplementation(/* mock implementation */)
   });
   ```

### Package.json Configuration

Make sure your package.json correctly specifies the test environment:

```json
"scripts": {
  "test": "vitest run --environment jsdom",
  "test:watch": "vitest --environment jsdom"
}
```

## CI Pipeline Structure

Our CI pipeline consists of the following jobs:

1. **Lint**: Runs linting on both Python and JavaScript/TypeScript code
2. **Python Tests**: Runs unit tests for Python code with Neo4j and Redis services
3. **GUI Tests**: Runs tests for the React-based GUI

## Workflow YAML Configuration

When troubleshooting CI issues, check the `.github/workflows/ci.yml` file for:

1. **Service Configuration**: Ensure Redis, Neo4j, and other services have the correct ports and credentials
2. **Environment Variables**: Verify all required environment variables are set correctly
3. **Installation Steps**: Check that all dependencies are properly installed
4. **Test Commands**: Ensure the correct test commands are being run

## Adding New Dependencies

When adding new dependencies to the project:

1. Update `pyproject.toml` or `package.json` as appropriate
2. Ensure the CI workflow file installs the new dependencies
3. Consider whether the dependency should be in a specific extras group

## Testing Locally Before Pushing

Before pushing changes that might affect CI:

1. Run the full test suite locally
2. Try running tests in a clean environment (like Docker) to mimic CI
3. Check for any environment-specific code that might behave differently in CI

## Debugging CI Failures

When CI fails:

1. Check the full logs to find the exact error
2. Try to reproduce the issue locally
3. Add additional debugging output if needed
4. Make isolated fixes for specific issues rather than many changes at once