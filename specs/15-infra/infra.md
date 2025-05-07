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

## 15.6 Testing Strategy

- **Local Validation** - Verify all services start correctly using Docker Compose and can communicate with each other.
- **Azure Deployment Testing** - Deploy to a test environment in Azure and validate service connectivity and functionality.
- **Load Testing** - Test system behavior under load to validate scaling configurations.
- **Security Testing** - Verify secret management and service-to-service authentication.
- **Chaos Testing** - Simulate service failures to ensure resilience and proper recovery.

## 15.7 Acceptance Criteria

- `./infra/scripts/start.sh` successfully starts all services locally with proper networking and volume mounts.
- `azd up` successfully deploys all components to Azure Container Apps with proper configuration.
- Local environment and Azure deployment have functional parity for all services.
- Secrets are securely managed in both local and cloud environments.
- Observability tools provide visibility into system health and performance.
- Services recover automatically from temporary failures.
- Documentation clearly explains how to use and extend the infrastructure.

---
