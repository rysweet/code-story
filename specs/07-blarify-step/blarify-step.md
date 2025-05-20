# 7.0 Blarify Workflow Step

**Previous:** [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md) | **Next:** [FileSystem Workflow Step](../08-filesystem-step/filesystem-step.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Graph Database Service](../04-graph-database/graph-database.md)
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)

**Used by:**
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)

## 7.1 Purpose

**BlarifyStep** is a workflow step in the ingestion pipeline that runs [Blarify](https://github.com/blarApp/blarify) in a linux container to parse the codebase and store the raw AST in the **Graph Service** with bindings to the symbol table derived from LSPs by blarify. Blarify directly parses the codebase and generates a graph of the codebase in neo4j. Thus the Blarify Step depends upon the Neo4J Graph Database Service. The BlarifyStep will run in Docker locally or in Azure Container Apps. 

## 7.2 Responsibilities

- Implement the `PipelineStep` interface.
- Run the Blarify tool in a linux container to parse the codebase and store the raw AST and symbol bindings in the **Graph Service**.
- The BlarifyStep will run in a container locally or in Azure Container Apps.
- Estimate the status of the job based on the progress of the Blarify tool.
- Support incremental updates for changed files in repositories.
- Handle both local Docker execution and container-to-container networking.

## 7.3 Code Structure

The Blarify Workflow Step is delivered as a standalone plugin package (codestory_blarify) that implements the PipelineStep interface and registers itself via entry-points.

```text
src/
└── codestory_blarify/
    ├── __init__.py
    ├── step.py               # BlarifyStep implementation
    └── requirements.txt      # Step-specific dependencies (docker, celery, neo4j-driver)
```

The implementation uses the prebuilt `blarapp/blarify:latest` Docker image rather than building a custom image.

step.py snippet:

```python
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus
from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
import docker
from celery import shared_task

class BlarifyStep(PipelineStep):
    def __init__(self, docker_image: str | None = None, timeout: int | None = None):
        """Initialize the Blarify step.

        Args:
            docker_image: Optional custom Docker image for Blarify
            timeout: Optional timeout in seconds for the Blarify process
        """
        self.settings = get_settings()
        self.image = docker_image or DEFAULT_IMAGE
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.active_jobs: dict[str, dict[str, Any]] = {}

        # Try to initialize Docker client
        try:
            self.docker_client = docker.from_env()
            # Test Docker connection
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.warning(
                f"Docker client initialization failed: {e}. Will use Celery task."
            )
            self.docker_client = None

    def run(self, repository_path: str, **config: Any) -> str:
        """Run the Blarify step."""
        # Implementation details...
        pass

    def status(self, job_id: str) -> dict[str, Any]:
        """Check the status of a job."""
        # Implementation details...
        pass

    def stop(self, job_id: str) -> dict[str, Any]:
        """Stop a running job."""
        # Implementation details...
        pass

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel a job."""
        # Implementation details...
        pass

    def ingestion_update(self, repository_path: str, **config: Any) -> str:
        """Update the graph with Blarify for a repository.

        This runs Blarify in incremental mode, which only processes files
        that have changed since the last run.
        """
        # Implementation details...
        pass
```

Entry-Point Registration (in pyproject.toml):
```toml 
[project.entry-points."codestory.pipeline.steps"]
blarify = "codestory_blarify.step:BlarifyStep"
```

## 7.4 Key Features

- **Asynchronous Processing**: Uses Celery tasks for non-blocking execution
- **Progress Tracking**: Monitors Docker container logs to estimate completion percentage
- **Docker Integration**: 
  - Uses the prebuilt `blarapp/blarify:latest` image
  - Mounts repository paths as read-only volumes
  - Handles container networking detection for Neo4j connections
- **Error Handling**: Graceful failure recovery with detailed error reporting
- **Incremental Processing**: Supports incremental mode for repository updates
- **Resource Management**: Proper cleanup of containers and resources
- **Container-to-Container Communication**: Special handling for Docker networking environments
- **Timeout Handling**: Detects inactivity and handles process timeouts

## 7.5 Testing Strategy

- **Unit** - unit tests for each method of the BlarifyStep class.
- **Integration** - integration tests depend on the actual database and Blarify tool. Ensure that the BlarifyStep can be started and stopped successfully. Ensure that the BlarifyStep can be queried successfully. Ensure that the resulting data in the graph database is correct. Use a small known repository for the ingestion testing. 
- **Pipeline Integration** - Test as part of the complete ingestion pipeline flow.
- **Docker Environment Testing** - Test both local Docker execution and container-to-container networking scenarios.


---