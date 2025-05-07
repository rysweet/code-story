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

## 7.3 Code Structure

The Blarify Workflow Step is delivered as a standalone plugin package (codestory_blarify) that implements the PipelineStep interface and registers itself via entry-points.

```text
src/
└── codestory_blarify/
    ├── __init__.py
    ├── step.py               # BlarifyStep implementation
    ├── Dockerfile            # Builds the container image with Blarify
    └── requirements.txt      # Step-specific dependencies (blarify, neo4j-driver)
```

step.py snippet:

```python
from codestory.ingestion_pipeline.base import PipelineStep
from ingestion_pipeline.celery_app import app
from codestory.graphdb.neo4j_connector import Neo4jConnector

class BlarifyStep(PipelineStep):
    def __init__(self, docker_image=None, timeout=None):
        self.image = docker_image or config.DEFAULT_IMAGE
        self.timeout = timeout or config.DEFAULT_TIMEOUT
        self.neo4j = Neo4jConnector()

    def run(self, repository_path: str, **kwargs) -> str:
        """Launch Blarify container to parse code and write AST+symbols into Neo4j."""
        # 1. Pull or build the Docker image
        # 2. Mount `repository_path` into /workspace in container
        # 3. Execute `blarify parse /workspace --output neo4j://...`
        # 4. Return a Celery task_id for tracking
        ...

    def status(self, run_id: str) -> StepStatus:
        """Query Celery for task status and container logs."""
        ...

    def cancel(self, run_id: str) -> None:
        """Revoke the Celery task and stop the container if running."""
        ...

    def ingestion_update(self, repository_path: str, **kwargs) -> str:
        """Re-run parsing incrementally for changed files."""
        ...
      def stop(self, run_id: str) -> None:
         """Stop the Blarify container and clean up resources."""
         ...
   ```

	•	Entry-Point Registration (in pyproject.toml):
   ```toml 
   [project.entry-points."codestory.pipeline.steps"]
   blarify = "codestory_blarify.step:BlarifyStep"
   ```

## 7.4 Testing strategy

- **Unit** - unit tests for each method of the BlarifyStep class.
- **Integration** - integration tests depend on the actual database and Blarify tool. Ensure that the BlarifyStep can be started and stopped successfully. Ensure that the BlarifyStep can be queried successfully. Ensure that the resulting data in the graph database is correct. Use a small known repository for the ingestion testing. 


---

