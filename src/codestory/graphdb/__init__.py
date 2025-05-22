"""Graph database module for Neo4j interaction.

This module provides tools for connecting to and querying a Neo4j graph database,
managing its schema, and performing operations like vector similarity search.
"""

from .exceptions import (
    ConnectionError,
    ExportError,
    Neo4jError,
    QueryError,
    SchemaError,
    TransactionError,
)
from .export import (
    export_cypher_script,
    export_graph_data,
    export_to_csv,
    export_to_json,
)
from .models import (
    BaseNode,
    BaseRelationship,
    CallsRelationship,
    ClassNode,
    ContainsRelationship,
    DirectoryNode,
    DocumentationNode,
    DocumentedByRelationship,
    FileNode,
    FunctionNode,
    ImportsRelationship,
    InheritsFromRelationship,
    MethodNode,
    ModuleNode,
    NodeType,
    RelationshipType,
    SummarizedByRelationship,
    SummaryNode,
)
from .neo4j_connector import Neo4jConnector, create_connector
from .schema import (
    create_custom_vector_index,
    get_schema_initialization_queries,
    initialize_schema,
    verify_schema,
)

# Define package exports
__all__ = [
    # Connector
    "Neo4jConnector",
    "create_connector",
    # Exceptions
    "Neo4jError",
    "ConnectionError",
    "QueryError",
    "SchemaError",
    "TransactionError",
    "ExportError",
    # Node models
    "NodeType",
    "BaseNode",
    "FileNode",
    "DirectoryNode",
    "ClassNode",
    "FunctionNode",
    "MethodNode",
    "ModuleNode",
    "SummaryNode",
    "DocumentationNode",
    # Relationship models
    "RelationshipType",
    "BaseRelationship",
    "ContainsRelationship",
    "ImportsRelationship",
    "CallsRelationship",
    "InheritsFromRelationship",
    "DocumentedByRelationship",
    "SummarizedByRelationship",
    # Schema
    "initialize_schema",
    "create_custom_vector_index",
    "get_schema_initialization_queries",
    "verify_schema",
    # Export
    "export_to_json",
    "export_to_csv",
    "export_graph_data",
    "export_cypher_script",
]
