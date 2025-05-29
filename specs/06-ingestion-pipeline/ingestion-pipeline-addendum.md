# Addendum to Ingestion Pipeline Specification

## A.1 Repository Mounting Improvements

Based on our implementation experience, the following improvements have been made to the repository mounting subsystem:

### A.1.1 CLI Integration

The auto_mount.py script has been fully integrated into the CLI's ingest commands, eliminating the need for a separate script and providing a more seamless user experience:

1. **Direct Integration**: Repository mounting code is now built directly into the `codestory ingest` CLI commands.

2. **New Mount Command**: Added a dedicated command for mounting repositories without starting ingestion:
   ```bash
   codestory ingest mount /path/to/your/repository [options]
   ```

3. **Enhanced Options**:
   - `--force-remount`: Forces remounting even if repository appears to be mounted
   - `--debug`: Shows detailed debug information about the mounting process
   - `--no-auto-mount`: Disables automatic mounting when using the `ingest start` command

### A.1.2 Multiple Connection Strategy

A key improvement is implementing a fallback connection strategy for Neo4j that tries multiple connection configurations:

```python
# Different ways to connect to Neo4j
connection_params = [
    # Default from settings
    {
        "uri": settings.neo4j.uri,
        "username": settings.neo4j.username,
        "password": settings.neo4j.password.get_secret_value(),
        "database": settings.neo4j.database,
    },
    # Container hostname connection
    {
        "uri": "bolt://neo4j:7687",
        "username": "neo4j",
        "password": "password",
        "database": "neo4j",
    },
    # Localhost connection (for main instance)
    {
        "uri": "bolt://localhost:7689",  # Port from docker-compose.yml
        "username": "neo4j",
        "password": "password",
        "database": "neo4j",
    },
    # Localhost test connection
    {
        "uri": "bolt://localhost:7688",  # Port from docker-compose.test.yml
        "username": "neo4j",
        "password": "password",
        "database": "testdb",
    }
]
```

This multiple connection strategy ensures:
- Greater reliability when connecting between containers and from host
- Automatic adaptation to different environments (dev, test, production)
- Less configuration required from end users

### A.1.3 Idempotent Graph Operations with MERGE

Neo4j operations have been refactored to use MERGE instead of CREATE for idempotent node creation:

```python
# Use MERGE for directory nodes to handle existing nodes
dir_query = """
MERGE (d:Directory {path: $props.path})
SET d.name = $props.name
RETURN d
"""
```

Benefits include:
- Ability to run ingestion multiple times without errors
- Handling pre-existing nodes gracefully
- Simplified error handling logic
- Support for incremental updates

### A.1.4 Enhanced Repository Validation

Improved validation ensures repositories are properly mounted by verifying:
1. Container existence and health
2. Repository directory existence in container
3. Specific content verification (README.md, .git/config, etc.)
4. Better diagnostic information when mounting fails

### A.1.5 Architecture Updates

The repository mounting subsystem now follows this improved architecture:

1. **Component Roles**:
   - CLI (ingest.py): User interface and high-level orchestration
   - Mount functions: Core mounting logic for Docker volumes
   - Verification functions: Validation of successful mounting
   - Connector with multiple connection strategy: Database access

2. **Process Flow**:
   1. User runs `codestory ingest start /path/to/repo`
   2. CLI detects Docker environment
   3. System verifies if repository is already mounted
   4. If not mounted, creates docker-compose.override.yml
   5. Recreates necessary containers with proper mounts
   6. Verifies successful mounting with specific checks
   7. Creates repository configuration
   8. Proceeds with ingestion using the proper container path

This architecture ensures reliable repository mounting across different environments and deployment scenarios.

## A.2 Authentication Resilience Improvements

### A.2.1 OpenAI Adapter Resilience

The ingestion pipeline has been enhanced with improved Azure OpenAI authentication resilience to minimize disruptions due to authentication failures:

1. **Automatic Tenant ID Detection**:
   - Extracts tenant IDs from error messages using sophisticated pattern matching
   - Retrieves tenant ID from environment variables when available
   - Checks Azure CLI configuration as a fallback mechanism

2. **Authentication Renewal**:
   - Automatically attempts to renew Azure authentication tokens when expired
   - Uses Azure CLI with appropriate parameters to refresh credentials
   - Injects credentials into containers for consistent authentication

3. **Enhanced Error Handling**:
   - Provides detailed error diagnostics for authentication failures
   - Offers clear, actionable guidance for resolving authentication issues
   - Detects various authentication error patterns including:
     - DefaultAzureCredential failures
     - AAD token expiration
     - Azure CLI installation issues
     - API endpoint configuration problems

4. **Graceful Degradation**:
   - Service continues operating with degraded capabilities when authentication fails
   - Fallback to API key authentication when available
   - DummyOpenAIAdapter implementation for completely offline operation

### A.2.2 Authentication Architecture

The authentication resilience system follows this architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Authentication  │    │  OpenAIAdapter  │    │  LLM Client     │
│    Detection    │───▶│   Health Check  │───▶│  Configuration  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Tenant ID      │    │ Azure CLI Login │    │ Token Injection │
│   Extraction    │───▶│    Attempt      │───▶│  to Containers  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### A.2.3 Environment Variable Configuration

New environment variables control authentication behavior:

```bash
# Bypass strict authentication checking
CODESTORY_NO_MODEL_CHECK=true

# Fallback to API key when available
OPENAI__API_KEY=sk-your-key-here

# Specify tenant ID directly
AZURE_TENANT_ID=your-tenant-id

# Enable LLM client debug mode
CODESTORY_LLM_DEBUG=true
```

These improvements ensure the ingestion pipeline can continue operating even when facing authentication challenges, creating a more resilient system.
## A.3 Retry & Failure Recovery

### A.3.1 Configurable Retry and Back-off

- Each pipeline step can specify `max_retries` and `back_off_seconds` in `pipeline_config.yml`.
- If not set per-step, global defaults under the `retry` section are used.
- Example:
  ```yaml
  steps:
    - name: filesystem
      max_retries: 2
      back_off_seconds: 5
    - name: blarify
      max_retries: 4
      back_off_seconds: 15
  retry:
    max_retries: 3
    back_off_seconds: 10
  ```

### A.3.2 Transient Error Handling and Idempotency

- Steps are implemented to call `self.retry()` on transient errors (e.g., network, resource busy).
- Retries use the configured back-off and are capped at `max_retries`.
- All steps are designed to be idempotent to ensure safe retry.

### A.3.3 Status Reporting and Visibility

- Retry count and last error for each step are persisted and exposed via:
  - Status API: `/v1/ingest/{job_id}` includes `retry_count` and `last_error` per step.
  - WebSocket events: Real-time updates include retry/failure info.
  - CLI and GUI: Display retry counts and last error messages for each step.

### A.3.4 Test Coverage

- Integration tests simulate transient failures and verify:
  - Steps are retried up to the configured limit.
  - Status API and UI report correct retry/failure info.
  - Final job status reflects success or failure after retries.

### A.3.5 User Experience

- Users can monitor retry progress and error messages in real time.
- Failure recovery is automatic for transient issues, with clear reporting if a step ultimately fails.
## A.4 Scheduling & Delayed Execution

### A.4.1 API and CLI Support

- The ingestion API (`/v1/ingest`) and CLI (`codestory ingest start`) support scheduling jobs using:
  - `eta`: Absolute datetime (ISO 8601 string or Unix timestamp) at which to schedule the job.
  - `countdown`: Number of seconds to delay job execution from now.
- If both are provided, `eta` takes precedence.
- Example CLI usage:
  ```bash
  codestory ingest start /path/to/repo --eta "2025-05-29T12:00:00"  # Schedule for a specific time
  codestory ingest start /path/to/repo --countdown 60                # Delay by 60 seconds
  ```

### A.4.2 Schedule Metadata Persistence

- Schedule metadata (`eta`, `countdown`) is persisted with each job and visible in job status via:
  - Status API: `/v1/ingest/{job_id}` includes `eta` field.
  - CLI: `codestory ingest status JOB_ID` displays scheduled time if applicable.
- Jobs are enqueued for execution at the scheduled time and remain in "pending" or "scheduled" state until then.

### A.4.3 Test Coverage

- Integration tests verify:
  - Jobs started with `--countdown` or `--eta` remain pending until the scheduled time.
  - After the scheduled time, jobs transition to running/completed.
  - Schedule metadata is visible in job status.
- Example test: `test_ingest_start_with_eta` in `tests/integration/test_cli/test_ingest_integration.py`.
## A.5 Performance Monitoring & Metrics

### A.5.1 Metrics API

- The ingestion API exposes recent job and step metrics at:
  - `/v1/ingest/resource_status`
- The response includes:
  - `tokens`: Resource token usage and limits for throttling
  - `metrics`: Summary statistics for recent jobs and steps:
    - `duration_seconds`: { avg, min, max }
    - `cpu_percent`: { avg, min, max }
    - `memory_mb`: { avg, min, max }
- Example response:
  ```json
  {
    "tokens": {
      "available_tokens": 2,
      "max_tokens": 4
    },
    "metrics": {
      "job_count": 20,
      "duration_seconds": { "avg": 12.3, "min": 2.1, "max": 45.7 },
      "cpu_percent": { "avg": 23.5, "min": 10.2, "max": 55.1 },
      "memory_mb": { "avg": 120.4, "min": 80.0, "max": 200.0 }
    }
  }
  ```

### A.5.2 Test Coverage

- Integration tests verify:
  - The `/v1/ingest/resource_status` endpoint returns the correct structure and metrics fields
  - Metrics are aggregated from recent jobs and steps
  - See: `test_resource_status_endpoint` in `tests/integration/test_ingestion_pipeline/test_resource_throttling.py`