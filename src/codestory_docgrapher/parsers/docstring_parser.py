from typing import Any

"""Parser for code docstrings in various languages.

This module provides a parser for extracting entities and relationships
from docstrings in code files (Python, JavaScript, Java, etc.).
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


@ParserFactory.register(DocumentType.DOCSTRING)
class DocstringParser(Parser):
    """Parser for code docstrings.

    This parser extracts entities and relationships from docstrings in
    various programming languages.
    """

    def __init__(self) -> None:
        """Initialize the docstring parser."""
        # Python docstring patterns
        self.py_docstring_pattern = re.compile(r'"""(.*?)"""', re.DOTALL)
        self.py_docstring_pattern_alt = re.compile(r"'''(.*?)'''", re.DOTALL)

        # JavaScript/TypeScript JSDoc patterns
        self.jsdoc_pattern = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)

        # Java/C++/C# Javadoc/Doxygen patterns
        self.javadoc_pattern = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)

        # Function/class/method detection
        self.py_function_pattern = re.compile(r"def\s+(\w+)\s*\(")
        self.py_class_pattern = re.compile(r"class\s+(\w+)")

        self.js_function_pattern = re.compile(r"function\s+(\w+)\s*\(")
        self.js_method_pattern = re.compile(r"(\w+)\s*[=:]\s*function\s*\(")
        self.js_class_pattern = re.compile(r"class\s+(\w+)")

        self.java_method_pattern = re.compile(
            r"(?:public|private|protected|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *\{?"
        )
        self.java_class_pattern = re.compile(
            r"(?:public|private|protected|static) +class +(\w+)"
        )

        # Docstring tag patterns
        self.param_pattern = re.compile(r"@param|:param|Parameters:|Args:|Arguments:")
        self.return_pattern = re.compile(r"@return|:return|Returns:|Return:")
        self.raises_pattern = re.compile(r"@raises|:raises|Raises:|Exceptions:|:except")
        self.example_pattern = re.compile(r"@example|Examples:|Example:")

    def parse(self, document: DocumentationFile) -> dict[str, Any]:
        """Parse docstrings from a code file.

        Args:
            document: The documentation file to parse

        Returns:
            Dict containing extracted entities and relationships
        """
        content = document.content
        file_path = document.path
        source_type = document.metadata.get("source_type", "unknown")

        entities: list[Any] = []
        relationships: list[Any] = []

        # Extract docstrings based on the source type
        docstrings: list[DocumentationEntity]
        if source_type == "python":
            docstrings = self._extract_python_docstrings(content, file_path)
        elif source_type in ["javascript", "typescript"]:
            docstrings = self._extract_js_docstrings(content, file_path)
        elif source_type in ["java", "c", "cpp", "h", "hpp"]:
            docstrings = self._extract_javadoc_docstrings(content, file_path)
        else:
            # Try all extraction methods
            docstrings = []
            docstrings.extend(self._extract_python_docstrings(content, file_path))
            docstrings.extend(self._extract_js_docstrings(content, file_path))
            docstrings.extend(self._extract_javadoc_docstrings(content, file_path))

        # Add docstring entities
        entities.extend(docstrings)

        # Create section entities for each docstring component
        for docstring in docstrings:
            sections = self._extract_docstring_sections(docstring)
            entities.extend(sections)

            # Create relationships between docstring and its sections
            for section in sections:
                relationship = DocumentationRelationship(
                    type=RelationType.CONTAINS,
                    source_id=docstring.id,
                    target_id=section.id,
                )
                relationships.append(relationship)

        return {"entities": entities, "relationships": relationships}

    def _extract_python_docstrings(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract Python docstrings from code content.

        Args:
            content: Code content
            file_path: Path to the code file

        Returns:
            List of docstring entities
        """
        entities: list[DocumentationEntity] = []

        # Find all docstrings with triple double quotes
        for match in self.py_docstring_pattern.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            # Determine the docstring's owner (function, class, module)
            owner_type, owner_name = self._find_python_docstring_owner(
                content, start_pos
            )

            entity_type = self._get_entity_type_for_owner(owner_type)

            entity = DocumentationEntity(
                type=entity_type,
                content=docstring,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "owner_type": owner_type,
                    "owner_name": owner_name,
                    "language": "python",
                },
            )
            entities.append(entity)

        # Find all docstrings with triple single quotes
        for match in self.py_docstring_pattern_alt.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            # Determine the docstring's owner (function, class, module)
            owner_type, owner_name = self._find_python_docstring_owner(
                content, start_pos
            )

            entity_type = self._get_entity_type_for_owner(owner_type)

            entity = DocumentationEntity(
                type=entity_type,
                content=docstring,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "owner_type": owner_type,
                    "owner_name": owner_name,
                    "language": "python",
                },
            )
            entities.append(entity)

        return entities

    def _extract_js_docstrings(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract JavaScript/TypeScript docstrings (JSDoc) from code content.

        Args:
            content: Code content
            file_path: Path to the code file

        Returns:
            List of docstring entities
        """
        entities: list[DocumentationEntity] = []

        # Find all JSDoc comments
        for match in self.jsdoc_pattern.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            # Determine the docstring's owner (function, class, method)
            owner_type, owner_name = self._find_js_docstring_owner(content, end_pos)

            entity_type = self._get_entity_type_for_owner(owner_type)

            entity = DocumentationEntity(
                type=entity_type,
                content=docstring,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "owner_type": owner_type,
                    "owner_name": owner_name,
                    "language": "javascript",
                },
            )
            entities.append(entity)

        return entities

    def _extract_javadoc_docstrings(
        self, content: str, file_path: str
    ) -> list[DocumentationEntity]:
        """Extract Java/C++/C# docstrings (Javadoc/Doxygen) from code content.

        Args:
            content: Code content
            file_path: Path to the code file

        Returns:
            List of docstring entities
        """
        entities: list[DocumentationEntity] = []

        # Find all Javadoc comments
        for match in self.javadoc_pattern.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()

            # Determine line number
            line_number = content[:start_pos].count("\n") + 1

            # Determine the docstring's owner (method, class)
            owner_type, owner_name = self._find_java_docstring_owner(content, end_pos)

            entity_type = self._get_entity_type_for_owner(owner_type)

            entity = DocumentationEntity(
                type=entity_type,
                content=docstring,
                file_path=file_path,
                source_text=match.group(0),
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=line_number,
                metadata={
                    "owner_type": owner_type,
                    "owner_name": owner_name,
                    "language": "java",
                },
            )
            entities.append(entity)

        return entities

    def _find_python_docstring_owner(self, content: str, pos: int) -> tuple[str, str]:
        """Find the owner (function, class, module) of a Python docstring.

        Args:
            content: Code content
            pos: Position of the docstring

        Returns:
            Tuple of (owner_type, owner_name)
        """
        # Get the line number of the docstring
        line_number = content[:pos].count("\n")

        # Check if the docstring belongs to a function
        for match in self.py_function_pattern.finditer(content):
            func_line = content[: match.start()].count("\n")
            if func_line >= line_number - 1 and func_line <= line_number + 3:
                return "function", match.group(1)

        # Check if the docstring belongs to a class
        for match in self.py_class_pattern.finditer(content):
            class_line = content[: match.start()].count("\n")
            if class_line >= line_number - 1 and class_line <= line_number + 3:
                return "class", match.group(1)

        # If no function or class is found, assume it's a module docstring
        return "module", "module"

    def _find_js_docstring_owner(self, content: str, pos: int) -> tuple[str, str]:
        """Find the owner (function, class, method) of a JavaScript/TypeScript docstring.

        Args:
            content: Code content
            pos: Position of the docstring

        Returns:
            Tuple of (owner_type, owner_name)
        """
        # Get content after the docstring
        after_content = content[pos : pos + 500]  # Look at the next 500 characters

        # Check for functions
        func_match = self.js_function_pattern.search(after_content)
        if func_match:
            return "function", func_match.group(1)

        # Check for methods
        method_match = self.js_method_pattern.search(after_content)
        if method_match:
            return "method", method_match.group(1)

        # Check for classes
        class_match = self.js_class_pattern.search(after_content)
        if class_match:
            return "class", class_match.group(1)

        # If no function, method, or class is found, assume it's a module docstring
        return "module", "module"

    def _find_java_docstring_owner(self, content: str, pos: int) -> tuple[str, str]:
        """Find the owner (method, class) of a Java/C++/C# docstring.

        Args:
            content: Code content
            pos: Position of the docstring

        Returns:
            Tuple of (owner_type, owner_name)
        """
        # Get content after the docstring
        after_content = content[pos : pos + 500]  # Look at the next 500 characters

        # Check for methods
        method_match = self.java_method_pattern.search(after_content)
        if method_match:
            return "method", method_match.group(1)

        # Check for classes
        class_match = self.java_class_pattern.search(after_content)
        if class_match:
            return "class", class_match.group(1)

        # If no method or class is found, assume it's a module/file docstring
        return "module", "module"

    def _get_entity_type_for_owner(self, owner_type: str) -> EntityType:
        """Get the appropriate entity type for a docstring owner.

        Args:
            owner_type: Type of the docstring owner

        Returns:
            EntityType for the docstring
        """
        if owner_type == "function" or owner_type == "method":
            return EntityType.FUNCTION_DESC
        elif owner_type == "class":
            return EntityType.CLASS_DESC
        elif owner_type == "module":
            return EntityType.MODULE_DESC
        else:
            return EntityType.PARAGRAPH

    def _extract_docstring_sections(
        self, docstring: DocumentationEntity
    ) -> list[DocumentationEntity]:
        """Extract sections (parameters, returns, etc.) from a docstring.

        Args:
            docstring: The docstring entity

        Returns:
            List of section entities
        """
        sections: list[Any] = []
        content = docstring.content
        file_path = docstring.file_path

        # Split docstring into lines
        lines = content.split("\n")

        # Find parameter descriptions
        param_sections = self._extract_parameter_sections(
            lines, file_path, docstring.id
        )
        sections.extend(param_sections)

        # Find return descriptions
        return_sections = self._extract_return_sections(lines, file_path, docstring.id)
        sections.extend(return_sections)

        # Find exception/raises descriptions
        raises_sections = self._extract_raises_sections(lines, file_path, docstring.id)
        sections.extend(raises_sections)

        # Find examples
        example_sections = self._extract_example_sections(
            lines, file_path, docstring.id
        )
        sections.extend(example_sections)

        return sections

    def _extract_parameter_sections(
        self, lines: list[str], file_path: str, parent_id: str
    ) -> list[DocumentationEntity]:
        """Extract parameter descriptions from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of parameter description entities
        """
        sections: list[DocumentationEntity] = []
        in_params = False
        param_section: list[str] = []

        for _i, line in enumerate(lines):
            if self.param_pattern.search(line):
                # Start of parameters section
                if param_section:
                    # Add previous section if it exists
                    entity = DocumentationEntity(
                        type=EntityType.PARAMETER_DESC,
                        content="\n".join(param_section),
                        file_path=file_path,
                        source_text="\n".join(param_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    param_section = []

                in_params = True
                param_section.append(line)
            elif in_params and (
                line.strip() == "" or line.startswith(" ") or line.startswith("\t")
            ):
                # Continue parameter section
                param_section.append(line)
            elif in_params:
                # End of parameter section
                if param_section:
                    entity = DocumentationEntity(
                        type=EntityType.PARAMETER_DESC,
                        content="\n".join(param_section),
                        file_path=file_path,
                        source_text="\n".join(param_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    param_section = []
                in_params = False

        # Add last section if it exists
        if param_section:
            entity = DocumentationEntity(
                type=EntityType.PARAMETER_DESC,
                content="\n".join(param_section),
                file_path=file_path,
                source_text="\n".join(param_section),
                start_pos=None,
                end_pos=None,
                line_number=None,
                parent_id=parent_id,
                metadata={},
            )
            sections.append(entity)

        return sections

    def _extract_return_sections(
        self, lines: list[str], file_path: str, parent_id: str
    ) -> list[DocumentationEntity]:
        """Extract return descriptions from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of return description entities
        """
        sections: list[DocumentationEntity] = []
        in_returns = False
        return_section: list[str] = []

        for _i, line in enumerate(lines):
            if self.return_pattern.search(line):
                # Start of returns section
                if return_section:
                    # Add previous section if it exists
                    entity = DocumentationEntity(
                        type=EntityType.RETURN_DESC,
                        content="\n".join(return_section),
                        file_path=file_path,
                        source_text="\n".join(return_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    return_section = []

                in_returns = True
                return_section.append(line)
            elif in_returns and (
                line.strip() == "" or line.startswith(" ") or line.startswith("\t")
            ):
                # Continue return section
                return_section.append(line)
            elif in_returns:
                # End of return section
                if return_section:
                    entity = DocumentationEntity(
                        type=EntityType.RETURN_DESC,
                        content="\n".join(return_section),
                        file_path=file_path,
                        source_text="\n".join(return_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    return_section = []
                in_returns = False

        # Add last section if it exists
        if return_section:
            entity = DocumentationEntity(
                type=EntityType.RETURN_DESC,
                content="\n".join(return_section),
                file_path=file_path,
                source_text="\n".join(return_section),
                start_pos=None,
                end_pos=None,
                line_number=None,
                parent_id=parent_id,
                metadata={},
            )
            sections.append(entity)

        return sections

    def _extract_raises_sections(
        self, lines: list[str], file_path: str, parent_id: str
    ) -> list[DocumentationEntity]:
        """Extract exception/raises descriptions from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of exception description entities
        """
        sections: list[DocumentationEntity] = []
        in_raises = False
        raises_section: list[str] = []

        for _i, line in enumerate(lines):
            if self.raises_pattern.search(line):
                # Start of raises section
                if raises_section:
                    # Add previous section if it exists
                    entity = DocumentationEntity(
                        type=EntityType.EXCEPTION_DESC,
                        content="\n".join(raises_section),
                        file_path=file_path,
                        source_text="\n".join(raises_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    raises_section = []

                in_raises = True
                raises_section.append(line)
            elif in_raises and (
                line.strip() == "" or line.startswith(" ") or line.startswith("\t")
            ):
                # Continue raises section
                raises_section.append(line)
            elif in_raises:
                # End of raises section
                if raises_section:
                    entity = DocumentationEntity(
                        type=EntityType.EXCEPTION_DESC,
                        content="\n".join(raises_section),
                        file_path=file_path,
                        source_text="\n".join(raises_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    raises_section = []
                in_raises = False

        # Add last section if it exists
        if raises_section:
            entity = DocumentationEntity(
                type=EntityType.EXCEPTION_DESC,
                content="\n".join(raises_section),
                file_path=file_path,
                source_text="\n".join(raises_section),
                start_pos=None,
                end_pos=None,
                line_number=None,
                parent_id=parent_id,
                metadata={},
            )
            sections.append(entity)

        return sections

    def _extract_example_sections(
        self, lines: list[str], file_path: str, parent_id: str
    ) -> list[DocumentationEntity]:
        """Extract example sections from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of example entities
        """
        sections: list[DocumentationEntity] = []
        in_example = False
        example_section: list[str] = []

        for _i, line in enumerate(lines):
            if self.example_pattern.search(line):
                # Start of example section
                if example_section:
                    # Add previous section if it exists
                    entity = DocumentationEntity(
                        type=EntityType.EXAMPLE,
                        content="\n".join(example_section),
                        file_path=file_path,
                        source_text="\n".join(example_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    example_section = []

                in_example = True
                example_section.append(line)
            elif in_example and (
                line.strip() == "" or line.startswith(" ") or line.startswith("\t")
            ):
                # Continue example section
                example_section.append(line)
            elif in_example:
                # End of example section
                if example_section:
                    entity = DocumentationEntity(
                        type=EntityType.EXAMPLE,
                        content="\n".join(example_section),
                        file_path=file_path,
                        source_text="\n".join(example_section),
                        start_pos=None,
                        end_pos=None,
                        line_number=None,
                        parent_id=parent_id,
                        metadata={},
                    )
                    sections.append(entity)
                    example_section = []
                in_example = False

        # Add last section if it exists
        if example_section:
            entity = DocumentationEntity(
                type=EntityType.EXAMPLE,
                content="\n".join(example_section),
                file_path=file_path,
                source_text="\n".join(example_section),
                start_pos=None,
                end_pos=None,
                line_number=None,
                parent_id=parent_id,
                metadata={},
            )
            sections.append(entity)

        return sections
