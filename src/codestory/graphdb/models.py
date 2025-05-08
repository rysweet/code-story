
"""Data models for graph entities (File, Directory, Class, Function, Module, Summary, Documentation)."""

from pydantic import BaseModel


class FileNode(BaseModel):
    """Represents a file in the repository graph."""

    path: str
    size: int | None = None
    content: str | None = None


class DirectoryNode(BaseModel):
    """Represents a directory in the repository graph."""

    path: str


class ClassNode(BaseModel):
    """Represents a class definition in the graph."""

    name: str
    module: str
    documentation: str | None = None


class FunctionNode(BaseModel):
    """Represents a function or method in the graph."""

    name: str
    signature: str | None = None
    documentation: str | None = None
    module: str | None = None


class ModuleNode(BaseModel):
    """Represents a module or package in the graph."""

    name: str
    path: str


class SummaryNode(BaseModel):
    """Represents a summary node with text and embedding."""

    text: str
    embedding: list[float] | None = None


class DocumentationNode(BaseModel):
    """Represents documentation content in the graph."""

    content: str
    type: str | None = None
    embedding: list[float] | None = None
