from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field
from typing import Any
'Data models for documentation entities and relationships.\n\nThis module defines data models used by the Documentation Grapher for\nrepresenting documentation entities, their relationships, and metadata.\n'

class DocumentType(str, Enum):
    """Types of documentation documents."""
    README = 'README'
    MARKDOWN = 'Markdown'
    RESTRUCTURED_TEXT = 'ReStructuredText'
    DOCSTRING = 'Docstring'
    COMMENT = 'Comment'
    API_DOC = 'APIDoc'
    USER_GUIDE = 'UserGuide'
    DEVELOPER_GUIDE = 'DeveloperGuide'
    TUTORIAL = 'Tutorial'
    OTHER = 'Other'

class EntityType(str, Enum):
    """Types of documentation entities."""
    SECTION = 'Section'
    HEADING = 'Heading'
    PARAGRAPH = 'Paragraph'
    CODE_BLOCK = 'CodeBlock'
    LIST = 'List'
    TABLE = 'Table'
    IMAGE = 'Image'
    LINK = 'Link'
    REFERENCE = 'Reference'
    EXAMPLE = 'Example'
    FUNCTION_DESC = 'FunctionDescription'
    CLASS_DESC = 'ClassDescription'
    MODULE_DESC = 'ModuleDescription'
    PARAMETER_DESC = 'ParameterDescription'
    RETURN_DESC = 'ReturnDescription'
    EXCEPTION_DESC = 'ExceptionDescription'
    ATTRIBUTE_DESC = 'AttributeDescription'
    VERSION_INFO = 'VersionInfo'
    AUTHOR_INFO = 'AuthorInfo'

class RelationType(str, Enum):
    """Types of relationships between documentation entities."""
    CONTAINS = 'CONTAINS'
    REFERENCES = 'REFERENCES'
    DESCRIBES = 'DESCRIBES'
    EXTENDS = 'EXTENDS'
    EXAMPLE_OF = 'EXAMPLE_OF'
    RELATED_TO = 'RELATED_TO'
    PRECEDES = 'PRECEDES'
    FOLLOWS = 'FOLLOWS'
    DEPENDS_ON = 'DEPENDS_ON'
    PART_OF = 'PART_OF'

class DocumentationFile(BaseModel):
    """Represents a documentation file in the repository."""
    path: str
    name: str
    doc_type: DocumentType
    content: str
    file_id: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

class DocumentationEntity(BaseModel):
    """Represents an entity within a documentation file."""
    id: str = Field(default_factory=lambda: f'entity_{uuid4()}')
    type: EntityType
    content: str
    file_path: str
    source_text: str
    start_pos: int | None = None
    end_pos: int | None = None
    line_number: int | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    parent_id: str | None = None
    children: list[str] = Field(default_factory=list)
    referenced_code: list[str] = Field(default_factory=list)

class DocumentationRelationship(BaseModel):
    """Represents a relationship between documentation entities."""
    id: str = Field(default_factory=lambda: f'rel_{uuid4()}')
    type: RelationType
    source_id: str
    target_id: str
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)

class DocumentationGraph(BaseModel):
    """Represents a graph of documentation entities and relationships."""
    documents: dict[str, DocumentationFile] = Field(default_factory=dict)
    entities: dict[str, DocumentationEntity] = Field(default_factory=dict)
    relationships: dict[str, DocumentationRelationship] = Field(default_factory=dict)
    processed_files: int = 0
    total_files: int = 0
    processed_entities: int = 0
    processed_relationships: int = 0

    def add_document(self: Any, document: DocumentationFile) -> None:
        """Add a document to the graph.

        Args:
            document: Documentation file to add
        """
        self.documents[document.path] = document
        self.total_files += 1

    def add_entity(self: Any, entity: DocumentationEntity) -> None:
        """Add an entity to the graph.

        Args:
            entity: Documentation entity to add
        """
        self.entities[entity.id] = entity
        self.processed_entities += 1

    def add_relationship(self: Any, relationship: DocumentationRelationship) -> None:
        """Add a relationship to the graph.

        Args:
            relationship: Documentation relationship to add
        """
        self.relationships[relationship.id] = relationship
        self.processed_relationships += 1

    def get_progress(self: Any) -> float:
        """Get the overall progress as a percentage.

        Returns:
            Progress percentage (0-100)
        """
        if self.total_files == 0:
            return 0.0
        return self.processed_files / self.total_files * 100.0