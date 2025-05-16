# CI Test Fixes

## Neo4j Port Configuration in Tests

This file documents an important fix for integration tests that might fail in CI environments due to Neo4j port configuration issues.

### Problem

In the local development environment with `docker-compose.test.yml`, Neo4j is mapped to port 7688:
```
  neo4j:
    ports:
      - "7688:7687"  # Bolt - using different port to avoid conflicts
```

However, in CI environments, Neo4j is often available on the standard port 7687. 

Many test files had hardcoded `bolt://localhost:7688` connection strings, which caused tests to fail in CI environments where Neo4j was running on port 7687.

### Solution

The `ci_test_fix.py` script was created to:

1. Update `conftest.py` to detect CI environments and use the appropriate port
2. Replace hardcoded port references in all test files

The key changes include:

```python
# Determine the correct Neo4j port to use
ci_env = os.environ.get("CI") == "true"
neo4j_port = "7687" if ci_env else "7688"
    
# Set the environment variables
neo4j_uri = f"bolt://localhost:{neo4j_port}"
os.environ["NEO4J_URI"] = neo4j_uri
os.environ["NEO4J__URI"] = neo4j_uri
```

### How to Apply the Fix

When CI test failures occur due to Neo4j connectivity, you can run:

```bash
python ci_test_fix.py
```

This script will update all necessary test files to use the correct Neo4j port based on the environment.

### Affected Files

- `tests/integration/conftest.py` - Primary connection handling
- All test files with Neo4j connections
- Script files that interact with Neo4j

### Recommendations

When writing new tests that connect to Neo4j:

1. **Never hardcode port numbers** - Use environment variables or the fixtures provided in `conftest.py`
2. Always check if running in CI environment with `os.environ.get("CI") == "true"`
3. Use the fixtures `neo4j_env` and `neo4j_connector` from `conftest.py` whenever possible