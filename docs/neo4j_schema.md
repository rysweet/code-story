# CodeStory Neo4j Database Schema

This document describes the knowledge graph schema used by CodeStory to represent code repositories.

## Node Types

The following node types are used to represent different elements of a codebase:

### File System Nodes

- **File**: A file in the repository
  - `path`: Absolute path to the file
  - `name`: File name 
  - `extension`: File extension
  - `size`: File size in bytes
  - `content`: File content (if stored)
  - `metadata`: Additional metadata as JSON

- **Directory**: A directory in the repository
  - `path`: Absolute path to the directory
  - `name`: Directory name

### Code Structure Nodes

- **Module**: A module or package in the codebase
  - `name`: Module name
  - `path`: Module path
  - `imports`: List of imported modules
  - `exports`: List of exported symbols
  - `metadata`: Additional metadata as JSON

- **Class**: A class definition
  - `name`: Class name
  - `file_path`: Path to the file containing the class
  - `line_number`: Starting line number
  - `end_line`: Ending line number
  - `superclasses`: List of parent classes
  - `methods`: List of method names
  - `attributes`: List of attribute names
  - `code`: Class code
  - `embedding`: Vector embedding for semantic search

- **Function**: A standalone function
  - `name`: Function name
  - `file_path`: Path to the file containing the function
  - `line_number`: Starting line number
  - `end_line`: Ending line number
  - `signature`: Function signature
  - `parameters`: List of parameter names
  - `return_type`: Return type information
  - `code`: Function code
  - `embedding`: Vector embedding for semantic search

- **Method**: A class method
  - `name`: Method name
  - `class_name`: Name of the class it belongs to
  - `file_path`: Path to the file containing the method
  - `line_number`: Starting line number
  - `end_line`: Ending line number
  - `signature`: Method signature
  - `parameters`: List of parameter names
  - `return_type`: Return type information
  - `is_static`: Whether the method is static
  - `visibility`: Method visibility (public, private, protected)
  - `code`: Method code
  - `embedding`: Vector embedding for semantic search

### Documentation Nodes

- **Documentation**: Documentation content
  - `content`: Documentation text
  - `type`: Type of documentation (docstring, comment, README, etc.)
  - `file_path`: Path to the file containing the documentation
  - `line_number`: Starting line number
  - `end_line`: Ending line number
  - `embedding`: Vector embedding for semantic search

- **Summary**: Generated summaries of code elements
  - `content`: Summary text
  - `target_type`: Type of the summarized element
  - `target_name`: Name of the summarized element
  - `embedding`: Vector embedding for semantic search

## Relationship Types

The following relationship types connect the nodes in the knowledge graph:

- **CONTAINS**: Directory contains a file or subdirectory
  - `directory` → `file|directory`

- **IMPORTS**: Module imports another module
  - `module` → `module`
  - Properties:
    - `import_type`: How the import is done (regular, dynamic, etc.)
    - `import_name`: Name used for the import (if aliased)

- **CALLS**: Function/method calls another function/method
  - `function|method` → `function|method`
  - Properties:
    - `line_number`: Line number of the call
    - `argument_count`: Number of arguments in the call

- **INHERITS_FROM**: Class inherits from another class
  - `class` → `class`
  - Properties:
    - `inheritance_type`: Type of inheritance

- **DOCUMENTED_BY**: Code element is documented by documentation
  - `class|function|method|module` → `documentation`

- **SUMMARIZED_BY**: Code element is summarized by a summary
  - `class|function|method|module|file` → `summary`

## Schema Visualization

```
(Directory)-[:CONTAINS]->(File)
(Directory)-[:CONTAINS]->(Directory)
(File)-[:CONTAINS]->(Module)
(File)-[:CONTAINS]->(Class)
(File)-[:CONTAINS]->(Function)
(Class)-[:CONTAINS]->(Method)
(Module)-[:IMPORTS]->(Module)
(Function)-[:CALLS]->(Function)
(Method)-[:CALLS]->(Method)
(Method)-[:CALLS]->(Function)
(Class)-[:INHERITS_FROM]->(Class)
(Function)-[:DOCUMENTED_BY]->(Documentation)
(Method)-[:DOCUMENTED_BY]->(Documentation)
(Class)-[:DOCUMENTED_BY]->(Documentation)
(Module)-[:DOCUMENTED_BY]->(Documentation)
(Function)-[:SUMMARIZED_BY]->(Summary)
(Method)-[:SUMMARIZED_BY]->(Summary)
(Class)-[:SUMMARIZED_BY]->(Summary)
(Module)-[:SUMMARIZED_BY]->(Summary)
(File)-[:SUMMARIZED_BY]->(Summary)
```

## Vector Indexes

To enable semantic similarity search, vector indexes are created for the following properties:

- `Class.embedding`
- `Function.embedding`
- `Method.embedding`
- `Documentation.embedding`
- `Summary.embedding`

## Constraints

The following uniqueness constraints are enforced:

- `File.path` is unique
- `Directory.path` is unique
- Combination of `Class.name` and `File.path` is unique
- Combination of `Function.name`, `signature` and `File.path` is unique
- Combination of `Method.name`, `Class.name` and `signature` is unique

## Indexes

The following indexes are created to improve query performance:

- `File.name`
- `File.extension`
- `Class.name`
- `Function.name`
- `Method.name`
- `Documentation.content` (full-text index)
- `Summary.content` (full-text index)

## Example Cypher Queries

### Find all classes in a file

```cypher
MATCH (f:File {path: "/path/to/file.py"})-[:CONTAINS]->(c:Class)
RETURN c.name, c.line_number
```

### Find all methods of a class

```cypher
MATCH (c:Class {name: "MyClass"})-[:CONTAINS]->(m:Method)
RETURN m.name, m.signature, m.line_number
```

### Find who calls a specific function

```cypher
MATCH (caller)-[:CALLS]->(f:Function {name: "my_function"})
RETURN caller.name, caller.file_path
```

### Find class inheritance hierarchy

```cypher
MATCH p = (c:Class {name: "MyClass"})-[:INHERITS_FROM*]->(parent:Class)
RETURN [node in nodes(p) | node.name] as inheritance_path
```

### Semantic search for similar functions

```cypher
// Assuming query_embedding is provided
CALL db.index.vector.queryNodes("function_embedding", 10, $query_embedding) 
YIELD node, score
RETURN node.name, node.file_path, score
```