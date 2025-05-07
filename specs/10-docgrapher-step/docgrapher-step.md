# 10.0 Documentation Grapher Workflow Step

**Previous:** [Summarizer Workflow Step](../09-summarizer-step/summarizer-step.md) | **Next:** [Code Story Service](../11-code-story-service/code-story-service.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)
- [Graph Database Service](../04-graph-database/graph-database.md)
- [AI Client](../05-ai-client/ai-client.md)
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)
- [Blarify Workflow Step](../07-blarify-step/blarify-step.md) (depends on its output)
- [FileSystem Workflow Step](../08-filesystem-step/filesystem-step.md) (depends on its output)
- [Summarizer Workflow Step](../09-summarizer-step/summarizer-step.md) (depends on its output)

**Used by:**
- [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)

## 10.1 Purpose

**DocumentationGrapher** is a workflow step in the ingestion pipeline that creates a knowledge graph of the documentation and links it to the relevant AST, Filesystem, and Summary nodes. It searches the repository for any documentation files (e.g., README, markdown files, etc.) and parses them to extract relevant information. The extracted information is then stored in the **Graph Service** with links to the parts of the software that they describe. 

## 10.2 Responsibilities
- Implement the `PipelineStep` interface.
- Search the repository for any documentation files (e.g., README, markdown files, etc.) and parse them to extract relevant information.
- Create a knowledge graph of the documentation and link it to the relevant AST, Filesystem, and Summary nodes in the **Graph Service**.

## 10.3 Code Structure

```text
src/codestory/ingestion/steps/documentation_grapher/
├── __init__.py                # Exports public APIs
├── documentation_grapher_step.py # Main class implementing PipelineStep interface
├── document_finder.py         # Locates documentation files in the repository
├── parsers/                   # Package for different document format parsers
│   ├── __init__.py
│   ├── markdown_parser.py     # Parser for Markdown files
│   ├── rst_parser.py          # Parser for ReStructuredText files
│   ├── docstring_parser.py    # Parser for code docstrings
│   └── parser_factory.py      # Factory for creating appropriate parsers
├── models.py                  # Data models for documentation entities and relationships
├── entity_linker.py           # Links documentation entities to code entities
├── knowledge_graph.py         # Builds the knowledge graph of documentation
└── utils/
    ├── __init__.py
    ├── content_analyzer.py    # Analyzes documentation content for entities and relationships
    ├── path_matcher.py        # Matches documentation references to filesystem paths
    └── progress_tracker.py    # Tracks progress of documentation processing
```

Key components:

1. **DocumentationGrapherStep**: Implements the `PipelineStep` interface and orchestrates the documentation graphing process.

2. **DocumentFinder**: Searches the repository for documentation files (README, markdown files, docstrings, etc.).

3. **Parsers Package**: Contains parsers for different documentation formats:
   - MarkdownParser: Parses Markdown files
   - RstParser: Parses ReStructuredText files
   - DocstringParser: Extracts and parses docstrings from code files
   - ParserFactory: Creates appropriate parsers based on file types

4. **EntityLinker**: Creates connections between documentation entities and code entities in the graph.

5. **KnowledgeGraph**: Builds the knowledge graph representation of documentation and relationships.

6. **Models**: Data classes for representing documentation entities and relationships.

7. **Utils Package**:
   - ContentAnalyzer: Analyzes documentation content for entities and relationships
   - PathMatcher: Resolves references in documentation to actual filesystem paths
   - ProgressTracker: Tracks processing progress for status reporting

The documentation graphing process follows these steps:
1. Search the repository for documentation files
2. Parse each documentation file using the appropriate parser
3. Extract entities and relationships from the documentation
4. Link documentation entities to code entities in the graph
5. Create the knowledge graph of documentation
6. Store the knowledge graph in Neo4j with links to related code entities
## 10.4 Testing strategy
- **Unit** - unit tests for each method of the DocumentationGrapher class.
- **Integration** - integration tests depend on the actual database and OpenAI API. Ensure that the DocumentationGrapher can be started and stopped successfully. Ensure that the DocumentationGrapher can be queried successfully. Ensure that the resulting data in the graph database is correct. Use a small known repository for the ingestion testing.

---

