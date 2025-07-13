# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md

"""
This conftest.py is intentionally minimal.

All testcontainer and environment management for integration tests is now handled
exclusively by the unified session-scoped fixture in tests/conftest.py.

Do not add any container, service, or environment setup here. All such logic must
reside in the project root conftest.py to ensure standardization and reusability.

This file may contain only integration-specific pytest hooks or utilities that do
not manage containers or environment variables.
"""
