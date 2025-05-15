# Summarizer Step Developer Guide

## Overview

The Summarizer workflow step is a key component of the Code Story ingestion pipeline that analyzes a repository's code structure and generates natural language summaries for code elements. It works by:

1. Building a dependency graph of code elements (files, directories, classes, functions, etc.)
2. Processing nodes in parallel, starting from leaf nodes (with no dependencies)
3. Generating summaries using the LLM client with specialized prompts
4. Storing the summaries in Neo4j with links to the original nodes
5. Gradually working up the dependency graph to generate higher-level summaries

## Architecture

The Summarizer step consists of several key components:

- **SummarizerStep**: Main class implementing the `PipelineStep` interface
- **DependencyAnalyzer**: Builds and analyzes the DAG of code dependencies
- **ParallelExecutor**: Manages throttled concurrent processing of nodes
- **Prompt Templates**: Specialized prompts for different node types
- **ContentExtractor**: Utilities for extracting code content and context
- **ProgressTracker**: Tracks and reports summarization progress

The summarization process follows a bottom-up approach, starting with leaf nodes and working up the dependency hierarchy to generate increasingly higher-level summaries.

## Usage

### Running the Summarizer Step

You can run the Summarizer step through the ingestion pipeline or directly:

```python
from src.codestory_summarizer.step import SummarizerStep

# Create the step
step = SummarizerStep()

# Run the step
job_id = step.run(
    repository_path="/path/to/repository",
    max_concurrency=5,  # Optional: Limit parallel processing
    max_tokens_per_file=8000  # Optional: Limit tokens per file
)

# Check status
status = step.status(job_id)
print(f"Status: {status['status']}")
print(f"Progress: {status.get('progress', 0):.1f}%")
```

### Checking Summarization Results

After running the Summarizer step, summaries are stored in Neo4j and can be queried:

```cypher
// Get summaries for files
MATCH (f:File)-[:HAS_SUMMARY]->(s:Summary)
RETURN f.path, s.text LIMIT 10

// Get summaries for classes
MATCH (c:Class)-[:HAS_SUMMARY]->(s:Summary)
RETURN c.name, s.text LIMIT 10

// Get the repository summary
MATCH (r:Repository)-[:HAS_SUMMARY]->(s:Summary)
RETURN r.name, s.text
```

The step also stores summaries in a `.summaries` directory within the repository for easy inspection.

## Configuration Options

The Summarizer step supports the following configuration options:

| Option | Default | Description |
|--------|---------|-------------|
| `max_concurrency` | 5 | Maximum number of concurrent summarization tasks |
| `max_tokens_per_file` | 8000 | Maximum number of tokens to include in prompts |
| `update_mode` | false | Whether to update existing summaries or regenerate all |

## Dependency Graph

The dependency graph is a key data structure that represents the relationships between code elements. The graph is built from the Neo4j database and includes:

- Files and their dependencies (imports)
- Directories and their hierarchical relationships
- Classes and their inheritance relationships
- Functions and methods within classes
- Module relationships

The graph is processed from leaf nodes (no dependencies) to root nodes, ensuring that child nodes are summarized before their parents.

## Prompt Templates

The Summarizer uses specialized prompt templates for different node types:

- **File Nodes**: Focus on overall file purpose, structure, and key components
- **Class Nodes**: Emphasize class responsibilities, methods, and inheritance
- **Function/Method Nodes**: Concentrate on purpose, parameters, and behavior
- **Directory Nodes**: Summarize overall purpose and content relationships
- **Repository Node**: Provide a high-level overview of the codebase

Custom prompt templates can be added or modified in the `prompts` package.

## Error Handling and Recovery

The Summarizer step implements robust error handling:

- Failed nodes are marked in the graph but don't block processing of other nodes
- The step tracks progress and can be interrupted and resumed
- Detailed error information is logged and stored in status results
- Timeout handling prevents infinite processing of large files

## Integration Tests

Comprehensive integration tests ensure the Summarizer functions correctly:

- Tests verify that summaries are generated for all node types
- Mock LLM client prevents actual API calls during testing
- Tests cover both initial processing and update scenarios
- Database state is verified after processing

## Performance Considerations

The Summarizer can process large repositories efficiently, but consider:

- Setting appropriate `max_concurrency` for your hardware
- Using `max_tokens_per_file` to limit token usage for large files
- For very large repositories, process in batches by subdirectory
- Monitor memory usage as the dependency graph can grow large

## Extending the Summarizer

To extend the Summarizer:

1. Add new prompt templates for additional node types
2. Enhance the content extractor for specialized file types
3. Implement custom filtering to ignore certain files/directories
4. Add new summary storage formats or export options