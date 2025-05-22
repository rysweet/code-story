"""Domain models for graph interaction."""

import time
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class QueryType(str, Enum):
    """Type of Cypher query."""

    READ = "read"
    WRITE = "write"


class CypherQuery(BaseModel):
    """Model for raw Cypher query execution."""

    query: str = Field(
        ...,
        description="The Cypher query to execute",
        examples=["MATCH (n) RETURN n LIMIT 10"],
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the Cypher query",
        examples=[{"name": "John", "limit": 10}],
    )
    query_type: QueryType = Field(
        default=QueryType.READ,
        description="Type of query (read-only or write)",
    )
    timeout: int | None = Field(
        default=30,
        description="Query timeout in seconds",
        ge=1,
        le=300,
    )

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        """Validate that query is not empty."""
        if not v.strip():
            raise ValueError("Query must not be empty")
        return v


class QueryResultFormat(str, Enum):
    """Format of query results."""

    TABULAR = "tabular"  # Default format with columns and rows
    GRAPH = "graph"  # Nodes and relationships
    CSV = "csv"  # For export


class QueryResult(BaseModel):
    """Model for Cypher query results."""

    query_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Query execution ID"
    )
    columns: list[str] = Field(..., description="Column names in result set")
    rows: list[list[Any]] = Field(..., description="Result rows")
    row_count: int = Field(..., description="Number of rows returned")
    execution_time_ms: int = Field(
        ..., description="Query execution time in milliseconds"
    )
    has_more: bool = Field(default=False, description="Whether there are more results")
    format: QueryResultFormat = Field(
        default=QueryResultFormat.TABULAR, description="Format of the results"
    )


class VectorSearchMode(str, Enum):
    """Mode for vector search."""

    SIMILARITY = "similarity"  # Cosine similarity
    EUCLIDEAN = "euclidean"  # Euclidean distance
    HYBRID = "hybrid"  # Combination of vector and keyword search


class EntityType(str, Enum):
    """Types of entities that can be searched."""

    ANY = "any"
    NODE = "node"
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    DIRECTORY = "directory"
    DOCUMENT = "document"


class VectorQuery(BaseModel):
    """Model for semantic/embedding search."""

    query: str = Field(
        ...,
        description="Natural language query or keywords for search",
        min_length=3,
    )
    entity_type: EntityType | None = Field(
        default=EntityType.ANY,
        description="Type of entity to search for",
    )
    mode: VectorSearchMode = Field(
        default=VectorSearchMode.SIMILARITY,
        description="Search mode (similarity, euclidean, hybrid)",
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )
    min_score: float = Field(
        default=0.5,
        description="Minimum similarity score (0-1)",
        ge=0.0,
        le=1.0,
    )


class SearchResult(BaseModel):
    """Single result item from vector search."""

    id: str = Field(..., description="Node ID")
    name: str = Field(..., description="Node name/label")
    type: str = Field(..., description="Entity type")
    score: float = Field(..., description="Similarity score (0-1)")
    content_snippet: str | None = Field(
        default=None, description="Content snippet with highlighted match"
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node properties",
    )
    path: str | None = Field(
        default=None,
        description="File path (for file/directory entities)",
    )


class VectorResult(BaseModel):
    """Model for vector search results."""

    results: list[SearchResult] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of matching results")
    execution_time_ms: int = Field(
        ..., description="Search execution time in milliseconds"
    )
    query_embedding_time_ms: int | None = Field(
        default=None,
        description="Time to generate query embedding",
    )


class PathRelationshipType(str, Enum):
    """Types of relationship constraints for path finding."""

    ANY = "any"
    CALLS = "calls"
    IMPORTS = "imports"
    CONTAINS = "contains"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"


class PathAlgorithm(str, Enum):
    """Path finding algorithms."""

    SHORTEST = "shortest"  # Single shortest path
    DIJKSTRA = "dijkstra"  # Weighted shortest path
    ALL_SHORTEST = "all_shortest"  # All shortest paths
    ALL_SIMPLE = "all_simple"  # All simple paths


class PathDirection(str, Enum):
    """Direction for path traversal."""

    OUTGOING = "outgoing"  # Only follow outgoing relationships
    INCOMING = "incoming"  # Only follow incoming relationships
    BOTH = "both"  # Follow relationships in either direction


class PathRequest(BaseModel):
    """Model for path finding between nodes."""

    start_node_id: str = Field(
        ...,
        description="ID of the starting node",
    )
    end_node_id: str = Field(
        ...,
        description="ID of the ending node",
    )
    algorithm: PathAlgorithm = Field(
        default=PathAlgorithm.SHORTEST,
        description="Path finding algorithm to use",
    )
    relationship_types: list[PathRelationshipType] | None = Field(
        default=None,
        description="Types of relationships to consider",
    )
    direction: PathDirection = Field(
        default=PathDirection.BOTH,
        description="Direction for path traversal",
    )
    max_depth: int = Field(
        default=10,
        description="Maximum path depth to search",
        ge=1,
        le=50,
    )
    limit: int = Field(
        default=1,
        description="Maximum number of paths to return",
        ge=1,
        le=10,
    )


class PathNode(BaseModel):
    """Node in a path result."""

    id: str = Field(..., description="Node ID")
    labels: list[str] = Field(..., description="Node labels")
    properties: dict[str, Any] = Field(..., description="Node properties")


class PathRelationship(BaseModel):
    """Relationship in a path result."""

    id: str = Field(..., description="Relationship ID")
    type: str = Field(..., description="Relationship type")
    properties: dict[str, Any] = Field(..., description="Relationship properties")
    start_node_id: str = Field(..., description="ID of the start node")
    end_node_id: str = Field(..., description="ID of the end node")


class Path(BaseModel):
    """Single path in a path result."""

    nodes: list[PathNode] = Field(..., description="Nodes in the path")
    relationships: list[PathRelationship] = Field(
        ..., description="Relationships in the path"
    )
    length: int = Field(..., description="Path length (number of relationships)")
    cost: float | None = Field(
        default=None, description="Path cost (for weighted paths)"
    )


class PathResult(BaseModel):
    """Model for path finding results."""

    paths: list[Path] = Field(..., description="Found paths")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    total_paths_found: int = Field(..., description="Total number of paths found")


class AskRequest(BaseModel):
    """Model for natural language question."""

    question: str = Field(
        ...,
        description="Natural language question about the codebase",
        min_length=3,
    )
    context_size: int = Field(
        default=5,
        description="Number of context items to use for answering",
        ge=1,
        le=20,
    )
    include_code_snippets: bool = Field(
        default=True,
        description="Whether to include code snippets in the response",
    )
    conversation_id: str | None = Field(
        default=None,
        description="ID for continued conversation context",
    )


class ReferenceType(str, Enum):
    """Types of references in answers."""

    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    DIRECTORY = "directory"
    DOCUMENT = "document"


class Reference(BaseModel):
    """Reference to a code entity."""

    id: str = Field(..., description="Entity ID")
    type: ReferenceType = Field(..., description="Type of reference")
    name: str = Field(..., description="Name of the entity")
    path: str | None = Field(default=None, description="Path to the entity")
    snippet: str | None = Field(default=None, description="Code snippet")
    relevance_score: float = Field(..., description="Relevance to the question (0-1)")


class AskAnswer(BaseModel):
    """Model for natural language answer."""

    answer: str = Field(..., description="Natural language answer to the question")
    references: list[Reference] = Field(..., description="References to code entities")
    conversation_id: str = Field(
        ..., description="ID for continued conversation context"
    )
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    confidence_score: float = Field(
        ...,
        description="Confidence in the answer (0-1)",
        ge=0.0,
        le=1.0,
    )


class VisualizationType(str, Enum):
    """Type of graph visualization."""

    FORCE = "force"  # Force-directed graph
    HIERARCHY = "hierarchy"  # Tree-like hierarchical visualization
    RADIAL = "radial"  # Radial layout
    SANKEY = "sankey"  # Flow diagram


class VisualizationTheme(str, Enum):
    """Theme for graph visualization."""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Auto-detect based on user preferences


class NodeFilter(BaseModel):
    """Filter for graph nodes in visualization."""

    node_types: list[str] | None = Field(
        default=None, description="Types of nodes to include"
    )
    search_query: str | None = Field(
        default=None, description="Text search to filter nodes"
    )
    max_nodes: int = Field(
        default=100, 
        description="Maximum number of nodes to display initially", 
        ge=10, 
        le=500
    )
    include_orphans: bool = Field(
        default=False, description="Whether to include nodes with no connections"
    )


class VisualizationRequest(BaseModel):
    """Request parameters for graph visualization."""

    type: VisualizationType = Field(
        default=VisualizationType.FORCE, description="Type of visualization"
    )
    theme: VisualizationTheme = Field(
        default=VisualizationTheme.AUTO, description="Visualization theme"
    )
    filter: NodeFilter | None = Field(
        default=None, description="Filter for nodes to include"
    )
    focus_node_id: str | None = Field(
        default=None, description="Node ID to focus the visualization on"
    )
    depth: int = Field(
        default=2, 
        description="Depth of relationships to include from focus node", 
        ge=1, 
        le=5
    )
    

class DatabaseClearRequest(BaseModel):
    """Request to clear the database."""
    
    confirm: bool = Field(
        default=False,
        description="Confirmation that the database should be cleared. Must be True."
    )
    preserve_schema: bool = Field(
        default=True,
        description="Whether to preserve constraints and indexes."
    )
    
    @field_validator("confirm")
    @classmethod
    def confirm_must_be_true(cls, v: bool) -> bool:
        """Validate that confirm is True."""
        if not v:
            raise ValueError("Database clear operation must be explicitly confirmed")
        return v


class DatabaseClearResponse(BaseModel):
    """Response from database clear operation."""
    
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Description of the operation result")
    timestamp: str = Field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        description="Timestamp of the operation"
    )
