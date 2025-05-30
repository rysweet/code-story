"""Data models for graph database entities.

This module defines Pydantic models for various node and relationship types
in the knowledge graph.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Enumeration of node types in the knowledge graph."""

    FILE = "File"
    DIRECTORY = "Directory"
    CLASS = "Class"
    FUNCTION = "Function"
    METHOD = "Method"
    MODULE = "Module"
    SUMMARY = "Summary"
    DOCUMENTATION = "Documentation"


class RelationshipType(str, Enum):
    """Enumeration of relationship types in the knowledge graph."""

    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS_FROM = "INHERITS_FROM"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    SUMMARIZED_BY = "SUMMARIZED_BY"


class BaseNode(BaseModel):
    """Base model for all node types."""

    id: str | None = None
    labels: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert the node to a dictionary suitable for Neo4j.

        Returns:
            Dictionary representation of the node
        """
        result = self.model_dump(exclude={"id"})
        result.update(self.properties)
        return result


class BaseRelationship(BaseModel):
    """Base model for all relationship types."""

    id: str | None = None
    type: str
    start_node_id: str
    end_node_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert the relationship to a dictionary suitable for Neo4j.

        Returns:
            Dictionary representation of the relationship
        """
        result = self.model_dump(exclude={"id", "start_node_id", "end_node_id"})
        result.update(self.properties)
        return result


class FileNode(BaseNode):
    """Represents a file in the repository."""

    path: str
    name: str
    extension: str | None = None
    size: int | None = None
    content: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        """Initialize FileNode with the File label."""
        super().__init__(**data)
        if NodeType.FILE.value not in self.labels:
            self.labels.append(NodeType.FILE.value)


class DirectoryNode(BaseNode):
    """Represents a directory in the repository."""

    path: str
    name: str

    def __init__(self, **data: Any) -> None:
        """Initialize DirectoryNode with the Directory label."""
        super().__init__(**data)
        if NodeType.DIRECTORY.value not in self.labels:
            self.labels.append(NodeType.DIRECTORY.value)


class CodeNode(BaseNode):
    """Base model for code-related nodes (Class, Function, Method, Module)."""

    name: str
    module: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    documentation: str | None = None
    code: str | None = None


class ClassNode(CodeNode):
    """Represents a class definition."""

    methods: list[str] = Field(default_factory=list)
    base_classes: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        """Initialize ClassNode with the Class label."""
        super().__init__(**data)
        if NodeType.CLASS.value not in self.labels:
            self.labels.append(NodeType.CLASS.value)


class FunctionNode(CodeNode):
    """Represents a function definition."""

    signature: str | None = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    return_type: str | None = None

    def __init__(self, **data: Any) -> None:
        """Initialize FunctionNode with the Function label."""
        super().__init__(**data)
        if NodeType.FUNCTION.value not in self.labels:
            self.labels.append(NodeType.FUNCTION.value)


class MethodNode(FunctionNode):
    """Represents a method (function inside a class)."""

    class_name: str

    def __init__(self, **data: Any) -> None:
        """Initialize MethodNode with the Method label."""
        super().__init__(**data)
        if NodeType.METHOD.value not in self.labels:
            self.labels.append(NodeType.METHOD.value)


class ModuleNode(CodeNode):
    """Represents a module or package."""

    imports: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        """Initialize ModuleNode with the Module label."""
        super().__init__(**data)
        if NodeType.MODULE.value not in self.labels:
            self.labels.append(NodeType.MODULE.value)


class SummaryNode(BaseNode):
    """Contains natural language summaries generated by LLMs."""

    text: str
    embedding: list[float] | None = None
    summary_type: str = "general"  # general, function, class, etc.

    def __init__(self, **data: Any) -> None:
        """Initialize SummaryNode with the Summary label."""
        super().__init__(**data)
        if NodeType.SUMMARY.value not in self.labels:
            self.labels.append(NodeType.SUMMARY.value)


class DocumentationNode(BaseNode):
    """Represents documentation content."""

    content: str
    doc_type: str = "inline"  # inline, docstring, markdown, etc.
    embedding: list[float] | None = None

    def __init__(self, **data: Any) -> None:
        """Initialize DocumentationNode with the Documentation label."""
        super().__init__(**data)
        if NodeType.DOCUMENTATION.value not in self.labels:
            self.labels.append(NodeType.DOCUMENTATION.value)


# Relationship models


class ContainsRelationship(BaseRelationship):
    """Represents a CONTAINS relationship between nodes."""

    def __init__(self, **data: Any) -> None:
        """Initialize ContainsRelationship with the CONTAINS type."""
        if "type" not in data:
            data["type"] = RelationshipType.CONTAINS.value
        super().__init__(**data)


class ImportsRelationship(BaseRelationship):
    """Represents an IMPORTS relationship between modules."""

    def __init__(self, **data: Any) -> None:
        """Initialize ImportsRelationship with the IMPORTS type."""
        if "type" not in data:
            data["type"] = RelationshipType.IMPORTS.value
        super().__init__(**data)


class CallsRelationship(BaseRelationship):
    """Represents a CALLS relationship between functions/methods."""

    call_line: int | None = None

    def __init__(self, **data: Any) -> None:
        """Initialize CallsRelationship with the CALLS type."""
        if "type" not in data:
            data["type"] = RelationshipType.CALLS.value
        super().__init__(**data)


class InheritsFromRelationship(BaseRelationship):
    """Represents an INHERITS_FROM relationship between classes."""

    def __init__(self, **data: Any) -> None:
        """Initialize InheritsFromRelationship with the INHERITS_FROM type."""
        if "type" not in data:
            data["type"] = RelationshipType.INHERITS_FROM.value
        super().__init__(**data)


class DocumentedByRelationship(BaseRelationship):
    """Represents a DOCUMENTED_BY relationship."""

    def __init__(self, **data: Any) -> None:
        """Initialize DocumentedByRelationship with the DOCUMENTED_BY type."""
        if "type" not in data:
            data["type"] = RelationshipType.DOCUMENTED_BY.value
        super().__init__(**data)


class SummarizedByRelationship(BaseRelationship):
    """Represents a SUMMARIZED_BY relationship."""

    def __init__(self, **data: Any) -> None:
        """Initialize SummarizedByRelationship with the SUMMARIZED_BY type."""
        if "type" not in data:
            data["type"] = RelationshipType.SUMMARIZED_BY.value
        super().__init__(**data)