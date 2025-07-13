# Unified Test Infrastructure Rules

## 1. Mandatory Use of Unified Session-Scoped Fixture

- **All integration and end-to-end (E2E) tests MUST use the unified session-scoped fixture provided in the test infrastructure.**
- The fixture is responsible for:
  - Starting and stopping all required services/containers.
  - Allocating dynamic ports and setting environment variables for the test session.
  - Ensuring test isolation and cleanup.

## 2. Prohibition of Direct Container/Environment Management

- **Individual test modules, classes, or functions MUST NOT directly manage containers, services, or environment setup/teardown.**
- All such setup MUST be performed exclusively by the unified fixture.
- Any code that starts, stops, or configures services outside the fixture is strictly forbidden.

## 3. Dynamic Port and Environment Variable Management

- **All service ports MUST be dynamically allocated by the fixture.**
- **All environment variables required for tests MUST be set by the fixture and injected into the test context.**
- Hardcoded ports, static environment variable values, or assumptions about service availability are prohibited.

## 4. Prohibition of Hardcoded Ports, External Dependencies, and Mocks

- **Hardcoded service ports are strictly forbidden in all integration and E2E tests.**
- **Integration tests MUST NOT depend on external services or resources.**
- **Mocks, stubs, or fakes for real service dependencies are NOT permitted in integration/E2E tests.** All dependencies must be real and managed by the fixture.

## 5. Cross-Linking Requirements

- **All new test modules MUST include references (as comments at the top of the file) to:**
  - The relevant specification(s) (e.g., `specs/06-ingestion-pipeline/ingestion-pipeline.md`)
  - This code rule file (`.roo/rules-code/08-unified-test-infra.md`)
  - Any other relevant code rules

## 6. Test Infrastructure Change Policy

- **Any changes to the unified test infrastructure (fixtures, setup logic, etc.) MUST be reflected in:**
  - The relevant specifications
  - This and any other affected code rule files
- The change process must include updating cross-links and documentation.

## 7. Example: Correct Usage of Unified Fixture

```python
# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

def test_graphdb_integration(unified_test_env):
    """
    Integration test using the unified session-scoped fixture.

    The fixture 'unified_test_env' provides:
      - Service endpoints via environment variables
      - Dynamic port allocation
      - Automatic setup/teardown of all required services
    """
    neo4j_url = unified_test_env["NEO4J_URL"]
    # Use the provided URL/port, do not hardcode or assume defaults
    result = run_some_query(neo4j_url)
    assert result.success
```

## 8. Enforcement

- Any test code or infrastructure violating these rules is subject to immediate rejection and must be refactored to comply.
- All code reviews and automated checks must enforce these requirements.

---
**References:**
- [Main Specification](../specs/Main.md)
- [Testing Requirements](./04-testing-requirements.md)
- [Project Methodology](./02-project-methodology.md)