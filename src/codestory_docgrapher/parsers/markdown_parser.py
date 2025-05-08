"""Parser for Markdown documentation files.

This module provides a parser for extracting entities and relationships
from Markdown documentation files.
"""

import logging
import re
import uuid
from typing import Dict, List, Optional, Tuple

from ..models import DocumentationEntity, DocumentationFile, DocumentationRelationship
from ..models import DocumentType, EntityType, RelationType
from .parser_factory import Parser, ParserFactory

logger = logging.getLogger(__name__)


@ParserFactory.register(DocumentType.MARKDOWN)
@ParserFactory.register(DocumentType.README)
class MarkdownParser(Parser):
    """Parser for Markdown documentation files.
    
    This parser extracts entities and relationships from Markdown files.
    """
    
    def __init__(self):
        """Initialize the Markdown parser."""
        self.heading_pattern = re.compile(r'^(#+)\s+(.+)$', re.MULTILINE)
        self.code_block_pattern = re.compile(r'```(\w*)\n(.*?)\n```', re.DOTALL)
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        self.image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        self.list_pattern = re.compile(r'((?:^\s*[-*+]\s+.*$\n?)+)', re.MULTILINE)
        
        # Code reference patterns
        self.code_ref_patterns = [
            # Function/method calls: `function_name()` or `Class.method()`
            re.compile(r'`([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?\(\))`'),
            # Class references: `ClassName`
            re.compile(r'`([A-Z][a-zA-Z0-9_]*)`'),
            # File/module references
            re.compile(r'`([a-zA-Z0-9_]+\.(?:py|js|ts|java|cpp|h|md))`'),
            # Code paths
            re.compile(r'`((?:[a-zA-Z0-9_]+/)+[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9]+)?)`')
        ]
    
    def parse(self, document: DocumentationFile) -> Dict:
        """Parse a Markdown documentation file.
        
        Args:
            document: The documentation file to parse
            
        Returns:
            Dict containing extracted entities and relationships
        """
        content = document.content
        file_path = document.path
        
        entities = []
        relationships = []
        
        # Extract headings and create section entities
        headings = self._extract_headings(content, file_path)
        entities.extend(headings)
        
        # Create parent-child relationships between headings
        heading_relationships = self._create_heading_hierarchy(headings)
        relationships.extend(heading_relationships)
        
        # Extract code blocks
        code_blocks = self._extract_code_blocks(content, file_path)
        entities.extend(code_blocks)
        
        # Extract links
        links = self._extract_links(content, file_path)
        entities.extend(links)
        
        # Extract images
        images = self._extract_images(content, file_path)
        entities.extend(images)
        
        # Extract lists
        lists = self._extract_lists(content, file_path)
        entities.extend(lists)
        
        # Extract code references
        code_refs = self._extract_code_references(content, file_path)
        entities.extend(code_refs)
        
        # Create relationships between entities
        rel_heading_code = self._create_entity_relationships(headings, code_blocks)
        relationships.extend(rel_heading_code)
        
        rel_heading_links = self._create_entity_relationships(headings, links)
        relationships.extend(rel_heading_links)
        
        rel_heading_images = self._create_entity_relationships(headings, images)
        relationships.extend(rel_heading_images)
        
        rel_heading_lists = self._create_entity_relationships(headings, lists)
        relationships.extend(rel_heading_lists)
        
        rel_heading_refs = self._create_entity_relationships(headings, code_refs)
        relationships.extend(rel_heading_refs)
        
        return {
            "entities": entities,
            "relationships": relationships
        }
    
    def _extract_headings(self, content: str, file_path: str) -> List[DocumentationEntity]:
        """Extract headings from Markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to the documentation file
            
        Returns:
            List of heading entities
        """
        entities = []
        
        # Find all headings
        for match in self.heading_pattern.finditer(content):
            level = len(match.group(1))  # Number of # characters
            heading_text = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # Determine line number
            line_number = content[:start_pos].count('\n') + 1
            
            entity = DocumentationEntity(
                type=EntityType.HEADING,
                content=heading_text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "level": level
                }
            )
            entities.append(entity)
        
        return entities
    
    def _create_heading_hierarchy(self, headings: List[DocumentationEntity]) -> List[DocumentationRelationship]:
        """Create hierarchy relationships between headings.
        
        Args:
            headings: List of heading entities
            
        Returns:
            List of relationships between headings
        """
        relationships = []
        
        # Sort headings by position in document
        sorted_headings = sorted(headings, key=lambda h: h.start_pos or 0)
        
        # Stack to keep track of parent headings
        stack = []
        
        for heading in sorted_headings:
            level = heading.metadata.get("level", 1)
            
            # Pop from stack until we find a parent with lower level
            while stack and stack[-1].metadata.get("level", 1) >= level:
                stack.pop()
            
            # If there's a parent, create a relationship
            if stack:
                parent = stack[-1]
                heading.parent_id = parent.id
                parent.children.append(heading.id)
                
                relationship = DocumentationRelationship(
                    type=RelationType.CONTAINS,
                    source_id=parent.id,
                    target_id=heading.id
                )
                relationships.append(relationship)
            
            # Push current heading to stack
            stack.append(heading)
        
        return relationships
    
    def _extract_code_blocks(self, content: str, file_path: str) -> List[DocumentationEntity]:
        """Extract code blocks from Markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to the documentation file
            
        Returns:
            List of code block entities
        """
        entities = []
        
        # Find all code blocks
        for match in self.code_block_pattern.finditer(content):
            language = match.group(1)
            code = match.group(2)
            start_pos = match.start()
            end_pos = match.end()
            
            # Determine line number
            line_number = content[:start_pos].count('\n') + 1
            
            entity = DocumentationEntity(
                type=EntityType.CODE_BLOCK,
                content=code,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "language": language
                }
            )
            entities.append(entity)
        
        return entities
    
    def _extract_links(self, content: str, file_path: str) -> List[DocumentationEntity]:
        """Extract links from Markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to the documentation file
            
        Returns:
            List of link entities
        """
        entities = []
        
        # Find all links
        for match in self.link_pattern.finditer(content):
            text = match.group(1)
            url = match.group(2)
            start_pos = match.start()
            end_pos = match.end()
            
            # Determine line number
            line_number = content[:start_pos].count('\n') + 1
            
            entity = DocumentationEntity(
                type=EntityType.LINK,
                content=text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "url": url
                }
            )
            entities.append(entity)
        
        return entities
    
    def _extract_images(self, content: str, file_path: str) -> List[DocumentationEntity]:
        """Extract images from Markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to the documentation file
            
        Returns:
            List of image entities
        """
        entities = []
        
        # Find all images
        for match in self.image_pattern.finditer(content):
            alt_text = match.group(1)
            url = match.group(2)
            start_pos = match.start()
            end_pos = match.end()
            
            # Determine line number
            line_number = content[:start_pos].count('\n') + 1
            
            entity = DocumentationEntity(
                type=EntityType.IMAGE,
                content=alt_text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "url": url
                }
            )
            entities.append(entity)
        
        return entities
    
    def _extract_lists(self, content: str, file_path: str) -> List[DocumentationEntity]:
        """Extract lists from Markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to the documentation file
            
        Returns:
            List of list entities
        """
        entities = []
        
        # Find all lists
        for match in self.list_pattern.finditer(content):
            list_text = match.group(1)
            start_pos = match.start()
            end_pos = match.end()
            
            # Determine line number
            line_number = content[:start_pos].count('\n') + 1
            
            entity = DocumentationEntity(
                type=EntityType.LIST,
                content=list_text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "items": list_text.count('\n') + 1
                }
            )
            entities.append(entity)
        
        return entities
    
    def _extract_code_references(self, content: str, file_path: str) -> List[DocumentationEntity]:
        """Extract code references from Markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to the documentation file
            
        Returns:
            List of reference entities
        """
        entities = []
        
        # Find all code references
        for pattern in self.code_ref_patterns:
            for match in pattern.finditer(content):
                reference = match.group(1)
                start_pos = match.start()
                end_pos = match.end()
                
                # Determine line number
                line_number = content[:start_pos].count('\n') + 1
                
                entity = DocumentationEntity(
                    type=EntityType.REFERENCE,
                    content=reference,
                    file_path=file_path,
                    source_text=match.group(0),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    line_number=line_number,
                    metadata={}
                )
                entities.append(entity)
        
        return entities
    
    def _create_entity_relationships(
        self,
        containers: List[DocumentationEntity],
        contained: List[DocumentationEntity]
    ) -> List[DocumentationRelationship]:
        """Create relationships between container entities and contained entities.
        
        Args:
            containers: List of container entities (e.g., headings)
            contained: List of contained entities (e.g., code blocks)
            
        Returns:
            List of relationships
        """
        relationships = []
        
        # Sort containers by position
        sorted_containers = sorted(containers, key=lambda e: e.start_pos or 0)
        
        # For each contained entity, find the closest container that precedes it
        for entity in contained:
            if entity.start_pos is None:
                continue
                
            container = None
            for potential_container in sorted_containers:
                if potential_container.start_pos is None:
                    continue
                    
                if potential_container.start_pos < entity.start_pos:
                    container = potential_container
                else:
                    break
            
            if container:
                relationship = DocumentationRelationship(
                    type=RelationType.CONTAINS,
                    source_id=container.id,
                    target_id=entity.id
                )
                relationships.append(relationship)
                
                # Update parent-child relationship
                entity.parent_id = container.id
                container.children.append(entity.id)
        
        return relationships