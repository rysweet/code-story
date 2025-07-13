# 15.0 Infra Module

**Previous:** [GUI](../14-gui/gui.md) | **Next:** [Documentation](../16-documentation/documentation.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- All other components (deploys and configures them)

**Used by:** All components (provides runtime environment)

## 15.1 Purpose

Provide infrastructure-as-code for both local development (Docker Compose) and cloud deployment (Azure Container Apps). This module ensures consistent deployment across environments, manages service configuration and networking, and coordinates container lifecycle. The infrastructure design prioritizes developer experience for local development while establishing a deployment pattern that scales in production.

## 15.2 Responsibilities

- Define container configurations for all services (Neo4j, Redis, Code Story Service, Celery workers, MCP adapter, GUI)
- Provide networking to allow inter-service communication
- Manage persistent volumes for stateful services (Neo4j, Redis)
- Configure authentication and security for service-to-service communication
- Enable health checks and restart policies for service resilience
- Support both local development and cloud deployment scenarios
- Facilitate secrets management across environments
- Enable observability with logging, metrics, and tracing

## 15.3 Architecture and Code Structure

The infrastructure module consists of several key components:

```
infra/
├── docker/                        # Docker-related files
│   ├── Dockerfile.service         # Multi-stage build for Python services
│   ├── Dockerfile.gui             # Build for React GUI
│   ├── Dockerfile.mcp             # Build for MCP adapter
│   └── docker-compose.override.yml  # Local development overrides
├── scripts/                       # Helper scripts
│   ├── start.sh                   # Start local development environment
│   ├── stop.sh                    # Stop local development environment
│   └── healthcheck.sh             # Verify service health
├── azure/                         # Azure deployment files
│   ├── main.bicep                 # Main Bicep template
│   ├── modules/                   # Modular Bicep files
│   │   ├── container-apps.bicep   # Container Apps Environment
│   │   ├── neo4j.bicep            # Neo4j database deployment
│   │   ├── redis.bicep            # Redis cache deployment
│   │   ├── service.bicep          # Code Story service deployment
│   │   ├── mcp.bicep              # MCP adapter deployment
│   │   └── gui.bicep              # GUI deployment
│   └── parameters/                # Environment-specific parameters
│       ├── dev.parameters.json    # Development parameters
│       └── prod.parameters.json   # Production parameters
├── .devcontainer/                 # Dev container configuration
│   └── devcontainer.json          # VS Code dev container config
├── azure.yaml                     # AZD configuration
└── docker-compose.yaml            # Main compose file
```

### 15.3.1 Docker Compose Structure

The `docker-compose.yaml` file defines the following services:

```yaml
services:
  neo4j:
    image: neo4j:5.x
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data
      - ./plugins:/plugins
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_apoc_export_file_enabled=true
      - NEO4J_apoc_import_file_enabled=true
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  service:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.service
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_URI=redis://redis:6379
    depends_on:
      - neo4j
      - redis

  worker:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.service
      target: worker
    command: celery -A codestory.ingestion_pipeline.celery_app worker -l info
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_URI=redis://redis:6379
    depends_on:
      - neo4j
      - redis
      - service

  mcp:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.mcp
    ports:
      - "8001:8001"
    environment:
      - SERVICE_URL=http://service:8000
    depends_on:
      - service

  gui:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.gui
    ports:
      - "5173:80"
    environment:
      - API_URL=http://localhost:8000
      - MCP_URL=http://localhost:8001
    depends_on:
      - service
      - mcp

volumes:
  neo4j_data:
  redis_data:
```

### 15.3.2 Azure Container Apps Deployment

Azure deployment uses the Azure Developer CLI (AZD) for streamlined infrastructure provisioning:

```
# azure.yaml
name: code-story
services:
  service:
    project: ./src/codestory
    language: python
    host: containerapp
  mcp:
    project: ./src/codestory_mcp
    language: python
    host: containerapp
  gui:
    project: ./gui
    language: typescript
    host: containerapp
```

The Bicep templates define Azure resources including:
- Container Apps Environment with Log Analytics
- Azure Container Registry for image storage
- Managed Identity for service-to-service authentication
- Azure Cache for Redis
- Azure Container Apps for each service with appropriate scaling rules

## 15.4 Implementation Steps

1. **Set up Docker Compose environment**
   - Create base `docker-compose.yaml` with all required services
   - Configure environment variables and port mappings for local development
   - Define volumes for persistent data (Neo4j, Redis)
   - Create Dockerfiles for each service with appropriate base images

2. **Implement multi-stage builds**
   - Create `Dockerfile.service` with development and production stages
   - Optimize Python and Node.js dependencies installation
   - Configure appropriate ENTRYPOINT and CMD for each service
   - Add health checks for container orchestration

3. **Create startup and management scripts**
   - Implement `start.sh` to handle first-time setup and service startup
   - Create `stop.sh` for graceful shutdown and cleanup
   - Add `healthcheck.sh` to verify all services are running correctly
   - Ensure scripts work cross-platform (bash with Windows compatibility)

4. **Configure VS Code devcontainer**
   - Create `.devcontainer/devcontainer.json` for consistent dev environment
   - Define required VS Code extensions for Python, TypeScript, Docker
   - Configure environment variables and mount points
   - Set up appropriate port forwards

5. **Implement Azure deployment with AZD**
   - Create `azure.yaml` defining service projects
   - Implement main Bicep template with resource grouping
   - Create modular Bicep files for each component
   - Configure environment-specific parameters

6. **Set up Azure Container Apps**
   - Configure Container Apps Environment with appropriate settings
   - Define ingress and networking rules for services
   - Set up scaling rules based on metrics
   - Configure service-to-service communication

7. **Implement secrets management**
   - Create KeyVault for secure storage
   - Configure secret references in Container Apps
   - Implement managed identity for authentication
   - Add environment-specific secret management

8. **Add observability configuration**
   - Configure Log Analytics workspace
   - Set up Application Insights for telemetry
   - Add Prometheus scraping endpoints
   - Configure OpenTelemetry for distributed tracing

9. **Create CI/CD workflows**
   - Implement GitHub Actions for build and test
   - Add deployment workflows for Azure
   - Configure environment-based promotions
   - Add infrastructure validation checks

10. **Document infrastructure usage**
    - Create detailed README with setup instructions
    - Document environment variables and configuration options
    - Add troubleshooting guides for common issues
    - Include architecture diagrams for better understanding

11. **Verification and Review**
    - Run all infrastructure components in a test environment
    - Verify all services start correctly and can communicate
    - Test deployment to Azure and validate functionality
    - Verify proper secret management in all environments
    - Test scaling and resilience under load
    - Simulate service failures to test recovery
    - Verify observability tools provide adequate visibility
    - Run security checks on all infrastructure components
    - Perform thorough code review against requirements
    - Validate documentation accuracy with test deployments
    - Make necessary adjustments based on review findings
    - Re-test infrastructure after any changes
    - Document issues found and their resolutions
    - Create detailed PR for final review

## 15.5 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to quickly start all services locally so that I can test changes in a complete environment. | • Running `./infra/scripts/start.sh` brings up all services.<br>• Services are accessible on expected ports.<br>• Environment variables are correctly configured.<br>• Persistent data is maintained between restarts. |
| As a developer, I want to deploy the entire application to Azure so that I can run it in a production-like environment. | • `azd up` successfully deploys all services to Azure.<br>• Services are correctly configured and connected.<br>• Secrets are stored securely in KeyVault.<br>• Services are accessible via public endpoints. |
| As an operator, I want proper health checks for all services so that I can ensure system reliability. | • Each container has appropriate health checks configured.<br>• Unhealthy containers are automatically restarted.<br>• Health status is exposed via monitoring endpoints.<br>• Health check failures trigger appropriate alerts. |
| As a security engineer, I want secure service-to-service communication so that the system maintains data confidentiality. | • Services use managed identities for authentication in Azure.<br>• Communication between services uses secure protocols.<br>• Secrets are not exposed in configuration files.<br>• Network access is restricted to required paths only. |
| As a developer, I want consistent development environments so that code works the same locally and in CI/CD. | • Dev containers provide consistent tooling and dependencies.<br>• Docker Compose configuration matches production service relationships.<br>• Environment variables can be overridden for local testing.<br>• Local services can be individually restarted for development. |
| As an operator, I want scalable infrastructure so the system can handle varying loads. | • Azure Container Apps are configured with appropriate scaling rules.<br>• Stateless services can scale horizontally.<br>• Database and cache services have appropriate resource allocations.<br>• Performance metrics are available for capacity planning. |
| As a developer, I want to see logs and metrics from all services so that I can troubleshoot issues. | • Logs are centralized in Log Analytics.<br>• Metrics are available via Prometheus endpoints.<br>• Distributed traces connect requests across services.<br>• Query tools are available for log analysis. |
| As a developer, I want to extend the infrastructure with new services so that I can add features to the system. | • Infrastructure code is modular and well-documented.<br>• Adding new services requires minimal changes to existing code.<br>• Documentation explains the process for adding services.<br>• Templates exist for common service types. |

## 15.6 Test Infrastructure

The infrastructure module provides comprehensive test infrastructure support with container lifecycle management and CI/CD integration for reliable, parallelizable testing.

### 15.6.1 Test Infrastructure Architecture

**Anti-patterns Replaced:**
- Manual Docker Compose setup requiring pre-existing services
- Hardcoded ports causing test conflicts in parallel execution
- Inconsistent test environments across local and CI
- Tests depending on external infrastructure state

**New Unified Pattern:**
- Testcontainers for dynamic, isolated service instances
- Centralized fixture management in [`tests/integration/conftest.py`](../../tests/integration/conftest.py)
- Container lifecycle automation with health checks
- Environment isolation preventing cross-test contamination

### 15.6.2 Container Lifecycle Management

```python
@pytest.fixture(scope="session")
def test_containers_and_service():
    """Session-scoped fixture managing complete test infrastructure."""
    # Dynamic container allocation
    neo4j_container = Neo4jContainer("neo4j:5.19")
    redis_container = RedisContainer("redis:7.2.4")
    
    # Health check integration
    neo4j_container.with_env("NEO4J_AUTH", "neo4j/password")
    
    # Start containers with automatic port mapping
    neo4j = neo4j_container.start()
    redis = redis_container.start()
    
    # Extract dynamic connection details
    neo4j_uri = f"bolt://localhost:{neo4j.get_exposed_port(7687)}"
    redis_uri = f"redis://localhost:{redis.get_exposed_port(6379)}/0"
    
    # Configure environment for all test processes
    os.environ["CODESTORY_NEO4J__URI"] = neo4j_uri
    os.environ["CODESTORY_REDIS__URI"] = redis_uri
    
    # Verify service readiness
    wait_for_services_ready(neo4j_uri, redis_uri)
    
    yield {
        "neo4j_uri": neo4j_uri,
        "redis_uri": redis_uri,
        "service_url": f"http://localhost:{service_port}/v1"
    }
    
    # Automatic cleanup
    neo4j.stop()
    redis.stop()
```

### 15.6.3 CI/CD Integration for Tests

**Docker-in-Docker Strategy:**
```yaml
# .github/workflows/test.yml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:dind
        options: --privileged
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Test Environment
        run: |
          # Install UV package manager
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env
          
          # Install dependencies
          uv sync --dev
          
          # Verify Docker availability
          docker info
      
      - name: Run Integration Tests
        run: |
          # Run tests with testcontainers
          uv run pytest tests/integration/ \
            -v \
            --tb=short \
            --timeout=300 \
            -n auto
        env:
          TESTCONTAINERS_RYUK_DISABLED: true
          DOCKER_HOST: unix:///var/run/docker.sock
```

### 15.6.4 Test Environment Configuration

**Environment Priority Order:**
1. Test fixture environment variables (highest)
2. `CODESTORY_*__*` prefixed variables
3. `NEO4J_*`, `REDIS_*` standard variables
4. Default configuration values (lowest)

```python
@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test-specific environment settings."""
    test_config = {
        # Disable external API calls during testing
        "DISABLE_OPENAI_HEALTHCHECK": "1",
        "AZURE_OPENAI_API_KEY": "test-key",
        
        # Configure test-specific timeouts
        "CELERY_TASK_ALWAYS_EAGER": "False",
        "CELERY_TASK_EAGER_PROPAGATES": "False",
        
        # Enable debug logging for tests
        "LOG_LEVEL": "DEBUG",
        "STRUCTLOG_DEBUG": "1"
    }
    
    for key, value in test_config.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup test environment
    for key in test_config:
        os.environ.pop(key, None)
```

### 15.6.5 Container Health Verification

```python
def wait_for_services_ready(neo4j_uri: str, redis_uri: str, timeout: int = 60):
    """Verify all services are ready before proceeding with tests."""
    import time
    import socket
    from neo4j import GraphDatabase
    import redis as redis_py
    
    # Parse connection details
    neo4j_host, neo4j_port = parse_bolt_uri(neo4j_uri)
    redis_host, redis_port = parse_redis_uri(redis_uri)
    
    # TCP connectivity check
    for host, port in [(neo4j_host, neo4j_port), (redis_host, redis_port)]:
        for _ in range(timeout):
            try:
                with socket.create_connection((host, port), timeout=2):
                    break
            except ConnectionRefusedError:
                time.sleep(1)
        else:
            raise RuntimeError(f"Service at {host}:{port} not ready")
    
    # Application-level health checks
    driver = GraphDatabase.driver(neo4j_uri, auth=("neo4j", "password"))
    try:
        with driver.session() as session:
            session.run("RETURN 1").single()
    finally:
        driver.close()
    
    redis_client = redis_py.from_url(redis_uri)
    assert redis_client.ping(), "Redis not responding to ping"
```

### 15.6.6 Parallel Test Execution

**Resource Isolation Strategy:**
- Each test worker gets unique testcontainer instances
- Dynamic port allocation prevents conflicts
- Separate Docker networks per test session
- Independent environment variable scoping

```python
@pytest.fixture(scope="session", autouse=True)
def aggressive_container_cleanup():
    """Ensure clean slate for each test session."""
    import subprocess
    
    # Remove all test-related containers
    try:
        result = subprocess.run([
            "docker", "ps", "-aq",
            "--filter", "label=testcontainers"
        ], capture_output=True, text=True)
        
        if result.stdout.strip():
            subprocess.run([
                "docker", "rm", "-f"
            ] + result.stdout.strip().split())
    except Exception as e:
        print(f"Container cleanup warning: {e}")
    
    yield
    
    # Post-session cleanup
    subprocess.run([
        "docker", "system", "prune", "-f",
        "--filter", "label=testcontainers"
    ], capture_output=True)
```

### 15.6.7 Integration with Docker Compose

**Test-Specific Compose Configuration:**
```yaml
# docker-compose.test.yml
version: "3.8"
services:
  neo4j:
    image: neo4j:community
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_dbms_default__database=testdb
    ports:
      - "7475:7474"  # Different ports to avoid conflicts
      - "7687:7687"
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p password 'RETURN 1'"]
      interval: 10s
      timeout: 10s
      retries: 15

  redis:
    image: redis:7.2.4-alpine
    ports:
      - "6380:6379"  # Different port to avoid conflicts
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 3s
      retries: 10
```

For detailed test patterns and examples, see:
- [Main Test Infrastructure Overview](../Main.md#test-infrastructure-architecture)
- [Ingestion Pipeline Test Patterns](../06-ingestion-pipeline/ingestion-pipeline.md#test-patterns)
- [Test Validation Report](../test-validation-report.md)

## 15.7 Testing Strategy

- **Local Validation** - Verify all services start correctly using Docker Compose and can communicate with each other.
- **Azure Deployment Testing** - Deploy to a test environment in Azure and validate service connectivity and functionality.
- **Load Testing** - Test system behavior under load to validate scaling configurations.
- **Security Testing** - Verify secret management and service-to-service authentication.
- **Chaos Testing** - Simulate service failures to ensure resilience and proper recovery.
- **Integration Testing** - Use testcontainers for self-contained, parallelizable integration tests.
- **CI/CD Testing** - Automated testing in GitHub Actions with Docker-in-Docker support.

## 15.8 Acceptance Criteria

- `./infra/scripts/start.sh` successfully starts all services locally with proper networking and volume mounts.
- `azd up` successfully deploys all components to Azure Container Apps with proper configuration.
- Local environment and Azure deployment have functional parity for all services.
- Secrets are securely managed in both local and cloud environments.
- Observability tools provide visibility into system health and performance.
- Services recover automatically from temporary failures.
- Documentation clearly explains how to use and extend the infrastructure.
- **Test infrastructure enables parallel, isolated integration tests without external dependencies.**
- **CI/CD pipelines successfully run all tests with testcontainer-based infrastructure.**
- **Container lifecycle management provides consistent environments across local and CI execution.**

---
