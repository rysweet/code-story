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
    "BaseNode",
    "BaseRelationship",
    "CallsRelationship",
    "ClassNode",
    "ConnectionError",
    "ContainsRelationship",
    "DirectoryNode",
    "DocumentationNode",
    "DocumentedByRelationship",
    "ExportError",
    "FileNode",
    "FunctionNode",
    "ImportsRelationship",
    "InheritsFromRelationship",
    "MethodNode",
    "ModuleNode",
    # Connector
    "Neo4jConnector",
    # Exceptions
    "Neo4jError",
    # Node models
    "NodeType",
    "QueryError",
    # Relationship models
    "RelationshipType",
    "SchemaError",
    "SummarizedByRelationship",
    "SummaryNode",
    "TransactionError",
    "create_connector",
    "create_custom_vector_index",
    "export_cypher_script",
    "export_graph_data",
    "export_to_csv",
    # Export
    "export_to_json",
    "get_schema_initialization_queries",
    # Schema
    "initialize_schema",
    "verify_schema",
]
