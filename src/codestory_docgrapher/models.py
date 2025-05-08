"""Data models for documentation entities and relationships.

This module defines data models used by the Documentation Grapher for
representing documentation entities, their relationships, and metadata.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Types of documentation documents."""
    
    README = "README"
    MARKDOWN = "Markdown"
    RESTRUCTURED_TEXT = "ReStructuredText"
    DOCSTRING = "Docstring"
    COMMENT = "Comment"
    API_DOC = "APIDoc"
    USER_GUIDE = "UserGuide"
    DEVELOPER_GUIDE = "DeveloperGuide"
    TUTORIAL = "Tutorial"
    OTHER = "Other"


class EntityType(str, Enum):
    """Types of documentation entities."""
    
    SECTION = "Section"
    HEADING = "Heading"
    PARAGRAPH = "Paragraph"
    CODE_BLOCK = "CodeBlock"
    LIST = "List"
    TABLE = "Table"
    IMAGE = "Image"
    LINK = "Link"
    REFERENCE = "Reference"
    EXAMPLE = "Example"
    FUNCTION_DESC = "FunctionDescription"
    CLASS_DESC = "ClassDescription"
    MODULE_DESC = "ModuleDescription"
    PARAMETER_DESC = "ParameterDescription"
    RETURN_DESC = "ReturnDescription"
    EXCEPTION_DESC = "ExceptionDescription"
    ATTRIBUTE_DESC = "AttributeDescription"
    VERSION_INFO = "VersionInfo"
    AUTHOR_INFO = "AuthorInfo"


class RelationType(str, Enum):
    """Types of relationships between documentation entities."""
    
    CONTAINS = "CONTAINS"
    REFERENCES = "REFERENCES"
    DESCRIBES = "DESCRIBES"
    EXTENDS = "EXTENDS"
    EXAMPLE_OF = "EXAMPLE_OF"
    RELATED_TO = "RELATED_TO"
    PRECEDES = "PRECEDES"
    FOLLOWS = "FOLLOWS"
    DEPENDS_ON = "DEPENDS_ON"
    PART_OF = "PART_OF"


class DocumentationFile(BaseModel):
    """Represents a documentation file in the repository."""
    
    path: str
    name: str
    doc_type: DocumentType
    content: str
    file_id: Optional[str] = None  # Neo4j ID of corresponding File node
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class DocumentationEntity(BaseModel):
    """Represents an entity within a documentation file."""
    
    id: str = Field(default_factory=lambda: f"entity_{uuid.uuid4()}")
    type: EntityType
    content: str
    file_path: str
    source_text: str
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    line_number: Optional[int] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    referenced_code: List[str] = Field(default_factory=list)  # Neo4j IDs of referenced code entities


class DocumentationRelationship(BaseModel):
    """Represents a relationship between documentation entities."""
    
    id: str = Field(default_factory=lambda: f"rel_{uuid.uuid4()}")
    type: RelationType
    source_id: str  # ID of source entity
    target_id: str  # ID of target entity
    properties: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class DocumentationGraph(BaseModel):
    """Represents a graph of documentation entities and relationships."""
    
    documents: Dict[str, DocumentationFile] = Field(default_factory=dict)
    entities: Dict[str, DocumentationEntity] = Field(default_factory=dict)
    relationships: Dict[str, DocumentationRelationship] = Field(default_factory=dict)
    
    # Keep track of progress
    processed_files: int = 0
    total_files: int = 0
    processed_entities: int = 0
    processed_relationships: int = 0
    
    def add_document(self, document: DocumentationFile) -> None:
        """Add a document to the graph.
        
        Args:
            document: Documentation file to add
        """
        self.documents[document.path] = document
        self.total_files += 1
    
    def add_entity(self, entity: DocumentationEntity) -> None:
        """Add an entity to the graph.
        
        Args:
            entity: Documentation entity to add
        """
        self.entities[entity.id] = entity
        self.processed_entities += 1
    
    def add_relationship(self, relationship: DocumentationRelationship) -> None:
        """Add a relationship to the graph.
        
        Args:
            relationship: Documentation relationship to add
        """
        self.relationships[relationship.id] = relationship
        self.processed_relationships += 1
    
    def get_progress(self) -> float:
        """Get the overall progress as a percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        if self.total_files == 0:
            return 0.0
        
        return (self.processed_files / self.total_files) * 100.0