from typing import Any

"""Parser for ReStructuredText documentation files.

This module provides a parser for extracting entities and relationships
from ReStructuredText documentation files.
"""

import logging
import re

from ..models import (
    DocumentationEntity,
    DocumentationFile,
    DocumentationRelationship,
    DocumentType,
    EntityType,
    RelationType,
)
from .parser_factory import Parser, ParserFactory

logger = logging.getLogger(__name__)


@ParserFactory.register(DocumentType.RESTRUCTURED_TEXT)
class RstParser(Parser):
    """Parser for ReStructuredText documentation files.

    This parser extracts entities and relationships from ReStructuredText files.
    """

    def __init__(self) -> None:
        """Initialize the RST parser."""
        # Heading patterns for different styles (e.g., === or ---)
        self.heading_pattern1 = re.compile(
            r'^([=\-`:\'"~^_*+#])\1{2,}\s*$\n^(.+?)$\n([=\-`:\'"~^_*+#])\3{2,}\s*$',
            re.MULTILINE,
        )
        self.heading_pattern2 = re.compile(
            r'^(.+?)$\n([=\-`:\'"~^_*+#])\2{2,}\s*$', re.MULTILINE
        )

        # Directive patterns
        self.directive_pattern = re.compile(
            r"^\.\. ([a-z]+)::\s*(.*?)$\n(?:\s{3}(.*?)$)?(?:\n\s{3}(.*?)$)*",
            re.MULTILINE,
        )

        # Code block pattern
        self.code_block_pattern = re.compile(
            r"^\.\. code-block::\s*(\w*)\s*$\n\s+(.+?)$(?:\n\s+.*?)*$",
            re.MULTILINE | re.DOTALL,
        )

        # Link pattern
        self.link_pattern = re.compile(r"`([^`]+)`_")
        self.ext_link_pattern = re.compile(r"`([^`]+)`__")
        self.link_def_pattern = re.compile(r"^\.\. _([^:]+):\s*(.+)$", re.MULTILINE)

        # Image pattern
        self.image_pattern = re.compile(
            r"^\.\. image::\s*(.+?)$(?:\n\s+:([a-z]+):\s*(.+?)$)*", re.MULTILINE
        )

        # List pattern
        self.list_pattern = re.compile(
            r"(?:^\s*(?:[*+#-]|\d+[.)]) .+$\n?)+", re.MULTILINE
        )

        # Code reference patterns
        self.code_ref_patterns = [
            # Function/method references: :func:`function_name`
            re.compile(r":func:`([^`]+)`"),
            # Class references: :class:`ClassName`
            re.compile(r":class:`([^`]+)`"),
            # Module references: :mod:`module_name`
            re.compile(r":mod:`([^`]+)`"),
            # File references: :file:`filename.ext`
            re.compile(r":file:`([^`]+)`"),
        ]

    def parse(self, document: DocumentationFile) -> dict:
        """Parse a ReStructuredText documentation file.

        Args:
            document: The documentation file to parse

        Returns:
            Dict containing extracted entities and relationships
        """
        content = document.content
        file_path = document.path

        entities: list[Any] = []
        relationships: list[Any] = []

        # Extract headings and create section entities
        headings: list[Any] = []
        headings.extend(self._extract_headings_style1(content, file_path))
        headings.extend(self._extract_headings_style2(content, file_path))
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

        return {"entities": entities, "relationships": relationships}

    def _extract_headings_style1(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract headings with over/underlines from ReStructuredText content.

        Args:
            content: ReStructuredText content
            file_path: Path to the documentation file

        Returns:
            List of heading entities
        """
        entities: list[Any] = []

        # Find all headings with over/underlines (e.g., === Title ===)
        for match in self.heading_pattern1.finditer(content):
            overline_char = match.group(1)
            heading_text = match.group(2).strip()
            match.group(3)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            # Determine heading level based on character
            level = self._get_heading_level(overline_char)

            entity = DocumentationEntity(
                type=EntityType.HEADING,
                content=heading_text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"level": level, "style": "overunder", "char": overline_char},
            )
            entities.append(entity)

        return entities

    def _extract_headings_style2(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract headings with underlines from ReStructuredText content.

        Args:
            content: ReStructuredText content
            file_path: Path to the documentation file

        Returns:
            List of heading entities
        """
        entities: list[Any] = []

        # Find all headings with underlines (e.g., Title ===)
        for match in self.heading_pattern2.finditer(content):
            heading_text = match.group(1).strip()
            underline_char = match.group(2)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            # Determine heading level based on character
            level = self._get_heading_level(underline_char)

            entity = DocumentationEntity(
                type=EntityType.HEADING,
                content=heading_text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"level": level, "style": "under", "char": underline_char},
            )
            entities.append(entity)

        return entities

    def _get_heading_level(self, char: str) -> int:
        """Determine heading level based on RST convention.

        Args:
            char: Character used for heading underline/overline

        Returns:
            Heading level (1-6)
        """
        # Common RST heading level characters in order of importance
        chars = ["#", "*", "=", "-", "^", '"']

        try:
            level = chars.index(char) + 1
        except ValueError:
            # Default to level 6 for unknown characters
            level = 6

        return min(level, 6)  # Cap at level 6

    def _create_heading_hierarchy(
        self, headings: list[DocumentationEntity]
    ) -> list[DocumentationRelationship]:
        """Create hierarchy relationships between headings.

        Args:
            headings: List of heading entities

        Returns:
            List of relationships between headings
        """
        relationships: list[Any] = []

        # Sort headings by position in document
        sorted_headings = sorted(headings, key=lambda h: h.start_pos or 0)

        # Stack to keep track of parent headings
        stack: list[Any] = []

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
                    target_id=heading.id,
                )
                relationships.append(relationship)

            # Push current heading to stack
            stack.append(heading)

        return relationships

    def _extract_code_blocks(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract code blocks from ReStructuredText content.

        Args:
            content: ReStructuredText content
            file_path: Path to the documentation file

        Returns:
            List of code block entities
        """
        entities: list[Any] = []

        # Find all code blocks
        for match in self.code_block_pattern.finditer(content):
            language = match.group(1)
            code = match.group(2)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            entity = DocumentationEntity(
                type=EntityType.CODE_BLOCK,
                content=code,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"language": language},
            )
            entities.append(entity)

        return entities

    def _extract_links(self, content: str, file_path: str) -> list[DocumentationEntity]:
        """Extract links from ReStructuredText content.

        Args:
            content: ReStructuredText content
            file_path: Path to the documentation file

        Returns:
            List of link entities
        """
        entities: list[Any] = []

        # Find all links (inline style)
        for match in self.link_pattern.finditer(content):
            text = match.group(1)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            entity = DocumentationEntity(
                type=EntityType.LINK,
                content=text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"url": f"#{text.lower().replace(' ', '-')}"},
            )
            entities.append(entity)

        # Find all external links (inline style)
        for match in self.ext_link_pattern.finditer(content):
            text = match.group(1)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            entity = DocumentationEntity(
                type=EntityType.LINK,
                content=text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"url": f"#external-{text.lower().replace(' ', '-')}"},
            )
            entities.append(entity)

        # Find link definitions
        for match in self.link_def_pattern.finditer(content):
            text = match.group(1)
            url = match.group(2)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            entity = DocumentationEntity(
                type=EntityType.LINK,
                content=text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"url": url},
            )
            entities.append(entity)

        return entities

    def _extract_images(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract images from ReStructuredText content.

        Args:
            content: ReStructuredText content
            file_path: Path to the documentation file

        Returns:
            List of image entities
        """
        entities: list[Any] = []

        # Find all images
        for match in self.image_pattern.finditer(content):
            url = match.group(1)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            entity = DocumentationEntity(
                type=EntityType.IMAGE,
                content=f"Image: {url}",
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"url": url},
            )
            entities.append(entity)

        return entities

    def _extract_lists(self, content: str, file_path: str) -> list[DocumentationEntity]:
        """Extract lists from ReStructuredText content.

        Args:
            content: ReStructuredText content
            file_path: Path to the documentation file

        Returns:
            List of list entities
        """
        entities: list[Any] = []

        # Find all lists
        for match in self.list_pattern.finditer(content):
            list_text = match.group(0)
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            entity = DocumentationEntity(
                type=EntityType.LIST,
                content=list_text,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={"items": list_text.count("\n") + 1},
            )
            entities.append(entity)

        return entities

    def _extract_code_references(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract code references from ReStructuredText content.

        Args:
            content: ReStructuredText content
            file_path: Path to the documentation file

        Returns:
            List of reference entities
        """
        entities: list[Any] = []

        # Find all code references
        for pattern in self.code_ref_patterns:
            for match in pattern.finditer(content):
                reference = match.group(1)
                start_pos = match.start()
                end_pos = match.end()

                # Determine line number
                line_number = content[:start_pos].count("\n") + 1

                ref_type = "unknown"
                if ":func:" in match.group(0):
                    ref_type = "function"
                elif ":class:" in match.group(0):
                    ref_type = "class"
                elif ":mod:" in match.group(0):
                    ref_type = "module"
                elif ":file:" in match.group(0):
                    ref_type = "file"

                entity = DocumentationEntity(
                    type=EntityType.REFERENCE,
                    content=reference,
                    file_path=file_path,
                    source_text=match.group(0),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    line_number=line_number,
                    metadata={"ref_type": ref_type},
                )
                entities.append(entity)

        return entities

    def _create_entity_relationships(
        self,
        containers: list[DocumentationEntity],
        contained: list[DocumentationEntity],
    ) -> list[DocumentationRelationship]:
        """Create relationships between container entities and contained entities.

        Args:
            containers: List of container entities (e.g., headings)
            contained: List of contained entities (e.g., code blocks)

        Returns:
            List of relationships
        """
        relationships: list[Any] = []

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
                    target_id=entity.id,
                )
                relationships.append(relationship)

                # Update parent-child relationship
                entity.parent_id = container.id
                container.children.append(entity.id)

        return relationships