# 8.0 FileSystem Workflow Step

**Previous:** [Blarify Workflow Step](../07-blarify-step/blarify-step.md) | **Next:** [Summarizer Workflow Step](../09-summarizer-step/summarizer-step.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Graph Database Service](../04-graph-database/graph-database.md)
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)
- [Blarify Workflow Step](../07-blarify-step/blarify-step.md) (runs after this step)

**Used by:**
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)

## 8.1 Purpose

**FileSystemStep** is a workflow step in the ingestion pipeline that creates a graph of the filesystem layout of the codebase and links it to the AST+symbol nodes. Its operation involves two key functions:
- Obtaining the filesystem layout of the codebase and creating a corresponding graph of the filesystem layout in Neo4J
- Linking the filesystem nodes to the related AST+symbol nodes in the graph database (e.g., linking a file to the class it implements, or the function it contains, etc.)

The FileSystemStep depends upon the Neo4J Graph Database Service, the BlarifyStep (which must run first to create AST nodes), and the Ingestion Pipeline.

## 8.2 Responsibilities
- Implement the `PipelineStep` interface.
- Recursively traverse the repository file system to identify all files and directories.
- Apply configured ignore patterns to skip irrelevant files (e.g., .git, `node_modules`).
- Create `Directory` and `File` nodes in the graph database with appropriate properties.
- Establish relationships between filesystem nodes (e.g., `CONTAINS` relationships).
- Link filesystem nodes to AST nodes created by BlarifyStep through appropriate relationships.
- Extract basic metadata such as file size, extension, last modified date, etc.
- Estimate the status of the job based on the progress of the filesystem graph creation process.
- Allow for incremental updates when files change through `ingestion_update`.

## 8.3 Code Structure

The FileSystem Workflow Step is delivered as a standalone plugin package (codestory_filesystem) that implements the PipelineStep interface and registers itself via entry-points.

```text
src/
└── codestory_filesystem/
    ├── __init__.py                   # Package initialization
    ├── step.py                       # FileSystemStep implementation
    ├── scanner.py                    # Filesystem traversal and analysis
    ├── linker.py                     # Links File nodes to AST nodes
    ├── models.py                     # Data models for filesystem entities
    └── utils/
        ├── __init__.py
        ├── path_utils.py             # Path manipulation utilities
        └── progress_tracker.py       # Job progress tracking
```

### 8.3.1 Usage Example

```python
from codestory_filesystem.step import FileSystemStep
import time

# Initialize the filesystem step with custom ignore patterns
filesystem_step = FileSystemStep(ignore_patterns=[
    ".git/", "node_modules/", "__pycache__/", ".venv/",
    "*.pyc", "*.log", "*.tmp", "build/", "dist/"
])

# Start processing a repository
repository_path = "/path/to/your/repository"
job_id = filesystem_step.run(repository_path)
print(f"Started filesystem processing with job ID: {job_id}")

# Poll for status until complete
while True:
    status = filesystem_step.status(job_id)
    print(f"Progress: {status.progress_percentage}%, Status: {status.state}")
    
    if status.state in ("COMPLETED", "FAILED", "CANCELLED"):
        break
        
    time.sleep(5)  # Check every 5 seconds

# Once complete, display results summary
if status.state == "COMPLETED":
    print(f"Created {status.stats['directories']} directories and {status.stats['files']} files")
    print(f"Linked {status.stats['linked_ast_nodes']} AST nodes to filesystem nodes")
    
    # Later, when files change, you can run incremental update
    update_job_id = filesystem_step.ingestion_update(repository_path)
    print(f"Started incremental update with job ID: {update_job_id}")
else:
    print(f"Job failed with error: {status.error_message}")
    
    # If needed, you can cancel a long-running job
    filesystem_step.cancel(job_id)
```

Entry-Point Registration (in pyproject.toml):
```toml
[project.entry-points."codestory.pipeline.steps"]
filesystem = "codestory_filesystem.step:FileSystemStep"
```

## 8.4 Neo4J Data Model

The FileSystemStep creates and maintains the following node types and relationships:

**Nodes:**
- `Directory` - Properties: path, name, last_modified
- `File` - Properties: path, name, size, extension, content_type, last_modified, content (optional)

**Relationships:**
- `CONTAINS` - Directory contains subdirectories or files
- `IMPLEMENTS` - File implements AST node (e.g., class, interface)
- `DEFINES` - File defines an AST node (e.g., function, variable)
- `DESCRIBES` - File describes an AST node (e.g., documentation)

## 8.5 Process Flow

The filesystem step follows this process:
1. Start filesystem traversal from repository root
2. For each directory encountered:
   - Create `Directory` node if it doesn't exist
   - Establish `CONTAINS` relationship with parent directory
3. For each file encountered:
   - Create `File` node with metadata properties
   - Establish `CONTAINS` relationship with parent directory
   - Apply content-type detection for common file formats
4. After all filesystem nodes are created:
   - Query AST nodes created by BlarifyStep
   - Establish relationships between File nodes and corresponding AST nodes
5. Update job status throughout the process for progress tracking

## 8.6 Testing Strategy

- **Unit Tests**
  - Test directory and file traversal logic with mock filesystem
  - Test ignore pattern application
  - Test node and relationship creation
  - Test AST linking algorithm
  
- **Integration Tests**
  - Test with actual repository with known structure
  - Verify correct graph representation in Neo4j
  - Validate linking between filesystem and AST nodes
  - Test incremental update functionality

- **Performance Tests**
  - Benchmark with repositories of various sizes
  - Test optimized bulk loading for large repositories
  - Measure memory consumption during traversal

## 8.7 Acceptance Criteria

- The FileSystemStep accurately represents the repository filesystem structure in Neo4j.
- All files and directories are properly linked with `CONTAINS` relationships.
- Ignore patterns correctly exclude specified files and directories.
- File metadata (size, extension, etc.) is accurately captured.
- FileSystemStep successfully links filesystem nodes to corresponding AST nodes.
- Progress reporting provides accurate status during processing.
- The step can be stopped and restarted without data corruption.
- Incremental updates efficiently process only changed files.
- Performance is acceptable even for large repositories with many files.

---

