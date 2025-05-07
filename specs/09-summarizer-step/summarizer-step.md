# 9.0 Summarizer Workflow Step

**Previous:** [FileSystem Workflow Step](../08-filesystem-step/filesystem-step.md) | **Next:** [Documentation Grapher Step](../10-docgrapher-step/docgrapher-step.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Graph Database Service](../04-graph-database/graph-database.md)
- [AI Client](../05-ai-client/ai-client.md)
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)
- [Blarify Workflow Step](../07-blarify-step/blarify-step.md) (depends on its output)
- [FileSystem Workflow Step](../08-filesystem-step/filesystem-step.md) (depends on its output)

**Used by:**
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)

## 9.1 Purpose

**Summarizer** is a workflow step in the ingestion pipeline that computes a DAG of code dependencies and walks from leaf nodes to the top and computes natural language English summaries for each AST or filesystem node using an LLM (from the ai module) and stores them in the **Graph Service** with links to the nodes they describe. Each directory or larger module of the code base should have an overall summary as well, along with a top level summary of the whole repository. The Summarizer will run in a container locally or in Azure Container Apps.  Every leaf node shall be processed in parallel up to a configurable limit (default = 5), and the DAG will be traversed in parallel as well. 

## 9.2 Responsibilities

- Implement the `PipelineStep` interface.
- Using the contents of the code, compute natural language English summaries or explanations for each AST or filesystem node.
- Process leaf nodes in parallel up to a configurable limit.
- Store summaries in the **Graph Service** with links to the nodes they describe.
- Compute a top level summary of the whole repository.
- Compute a summary for each directory or larger module of the code base.
- Estimate the status of the job based on the progress of the summarization process.

## 9.3 Architecture and Code Structure

```text
src/codestory/ingestion/steps/summarizer/
├── __init__.py                # Exports public APIs
├── summarizer_step.py         # Main SummarizerStep class implementing PipelineStep interface
├── dependency_analyzer.py     # Builds and analyzes the DAG of code dependencies
├── parallel_executor.py       # Manages parallel processing of nodes with configurable limits
├── models.py                  # Data models for summaries and intermediate representations
├── prompts/                   # Directory containing prompt templates for different node types
│   ├── __init__.py
│   ├── file_node.py           # Prompt templates for file nodes
│   ├── class_node.py          # Prompt templates for class nodes
│   ├── function_node.py       # Prompt templates for function/method nodes
│   ├── module_node.py         # Prompt templates for module nodes
│   └── directory_node.py      # Prompt templates for directory nodes
└── utils/
    ├── __init__.py
    ├── content_extractor.py   # Utilities for extracting code content to summarize
    └── progress_tracker.py    # Utilities for tracking and reporting summarization progress
```

Key components:

1. **SummarizerStep**: Implements the `PipelineStep` interface and orchestrates the overall summarization process.

2. **DependencyAnalyzer**: Builds a directed acyclic graph (DAG) of code dependencies by querying the Neo4j database for AST and filesystem nodes. It identifies leaf nodes for initial processing.

3. **ParallelExecutor**: Manages parallel processing of nodes with configurable concurrency limits. Implements throttling and work queuing.

4. **Prompts Package**: Contains templated prompts for different node types to achieve consistent and high-quality summaries. Each module provides specialized prompt construction for its node type.

5. **Models**: Data classes for representing summaries and intermediate data structures during processing.

6. **Utils Package**:
   - ContentExtractor: Collects code snippets and context for summarization
   - ProgressTracker: Tracks summarization progress for status reporting

The summarization process follows these steps:
1. Build the dependency DAG by querying Neo4j for AST and filesystem nodes
2. Identify leaf nodes in the DAG for initial processing
3. Process leaf nodes in parallel (up to the configured limit)
4. For each node:
   - Extract relevant code and context
   - Generate a summary using the appropriate prompt template and the LLM client
   - Store the summary in Neo4j with links to the corresponding node
5. Continue traversing the DAG upward, processing nodes whose dependencies have already been summarized
6. Generate higher-level summaries for directories and modules
7. Finally, generate a top-level repository summary

