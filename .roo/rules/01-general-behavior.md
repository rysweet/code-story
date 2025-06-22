# General Behavior Guidelines

## Content Policies

- Follow Microsoft content policies
- Avoid content that violates copyrights
- If asked to generate harmful, hateful, racist, sexist, lewd, violent, or completely irrelevant content, only respond with "Sorry, I can't assist with that."
- Keep answers short and impersonal

## Project Context

- This project uses a spec-driven modular approach
- We may be working with a large codebase that was mostly developed with AI
- The codebase may contain errors and anti-patterns
- Prioritize the instructions in these rule files over existing codebase patterns
- Keep the plan status up to date by updating `/Specifications/status.md`

## Integration Test Requirements

- Always run tests with `uv run pytest ...` to ensure the correct environment and dependency management.
- All integration tests must be fully self-contained: they must use shared code in fixtures to manage bringing up and cleaning up their dependencies (e.g., Neo4j, Redis, etc.).
- Integration tests must not rely on any preconditions (such as services already running, specific ports being available, or data being present).
- Integration tests must not interfere with one another; each test must isolate its resources and clean up after itself.
- Do not assume default ports for services; all configuration must be driven by test configuration, not hardcoded values.
- Do not use mocks in integration tests; all dependencies must be real and managed by fixtures.
- Do not skip tests; all tests must be run and must pass.
- Do not artificially cause tests to pass or ignore the functionality being tested; tests must validate real, working features.
- Do not unnecessarily run the full test suite; run integration tests one at a time and fix failures methodically until all are passing.
