from typing import Any
'Parser for code docstrings in various languages.\n\nThis module provides a parser for extracting entities and relationships\nfrom docstrings in code files (Python, JavaScript, Java, etc.).\n'
import logging
import re
from ..models import DocumentationEntity, DocumentationFile, DocumentationRelationship, DocumentType, EntityType, RelationType
from .parser_factory import Parser, ParserFactory
logger = logging.getLogger(__name__)

@ParserFactory.register(DocumentType.DOCSTRING)
class DocstringParser(Parser):
    """Parser for code docstrings.

    This parser extracts entities and relationships from docstrings in
    various programming languages.
    """

    def __init__(self: Any) -> None:
        """Initialize the docstring parser."""
        self.py_docstring_pattern = re.compile('"""(.*?)"""', re.DOTALL)
        self.py_docstring_pattern_alt = re.compile("'''(.*?)'''", re.DOTALL)
        self.jsdoc_pattern = re.compile('/\\*\\*(.*?)\\*/', re.DOTALL)
        self.javadoc_pattern = re.compile('/\\*\\*(.*?)\\*/', re.DOTALL)
        self.py_function_pattern = re.compile('def\\s+(\\w+)\\s*\\(')
        self.py_class_pattern = re.compile('class\\s+(\\w+)')
        self.js_function_pattern = re.compile('function\\s+(\\w+)\\s*\\(')
        self.js_method_pattern = re.compile('(\\w+)\\s*[=:]\\s*function\\s*\\(')
        self.js_class_pattern = re.compile('class\\s+(\\w+)')
        self.java_method_pattern = re.compile('(?:public|private|protected|static|\\s) +[\\w\\<\\>\\[\\]]+\\s+(\\w+) *\\([^\\)]*\\) *\\{?')
        self.java_class_pattern = re.compile('(?:public|private|protected|static) +class +(\\w+)')
        self.param_pattern = re.compile('@param|:param|Parameters:|Args:|Arguments:')
        self.return_pattern = re.compile('@return|:return|Returns:|Return:')
        self.raises_pattern = re.compile('@raises|:raises|Raises:|Exceptions:|:except')
        self.example_pattern = re.compile('@example|Examples:|Example:')

    def parse(self: Any, document: DocumentationFile) -> dict[str, Any]:
        """Parse docstrings from a code file.

        Args:
            document: The documentation file to parse

        Returns:
            Dict containing extracted entities and relationships
        """
        content = document.content
        file_path = document.path
        source_type = document.metadata.get('source_type', 'unknown')
        entities: list[Any] = []
        relationships: list[Any] = []
        if source_type == 'python':
            docstrings = self._extract_python_docstrings(content, file_path)
        elif source_type in ['javascript', 'typescript']:
            docstrings = self._extract_js_docstrings(content, file_path)
        elif source_type in ['java', 'c', 'cpp', 'h', 'hpp']:
            docstrings = self._extract_javadoc_docstrings(content, file_path)
        else:
            docstrings: list[Any] = [][no - redef]
            docstrings.extend(self._extract_python_docstrings(content, file_path))
            docstrings.extend(self._extract_js_docstrings(content, file_path))
            docstrings.extend(self._extract_javadoc_docstrings(content, file_path))
        entities.extend(docstrings)
        for docstring in docstrings:
            sections = self._extract_docstring_sections(docstring)
            entities.extend(sections)
            for section in sections:
                relationship = DocumentationRelationship(type=RelationType.CONTAINS, source_id=docstring.id, target_id=section.id)
                relationships.append(relationship)
        return {'entities': entities, 'relationships': relationships}

    def _extract_python_docstrings(self: Any, content: str, file_path: str) -> list[DocumentationEntity]:
        """Extract Python docstrings from code content.

        Args:
            content: Code content
            file_path: Path to the code file

        Returns:
            List of docstring entities
        """
        entities: list[Any] = []
        for match in self.py_docstring_pattern.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            line_number = content[:start_pos].count('\n') + 1
            owner_type, owner_name = self._find_python_docstring_owner(content, start_pos)
            entity_type = self._get_entity_type_for_owner(owner_type)
            entity = DocumentationEntity(type=entity_type, content=docstring, file_path=file_path, source_text=match.group(0), start_pos=start_pos, end_pos=end_pos, line_number=line_number, metadata={'owner_type': owner_type, 'owner_name': owner_name, 'language': 'python'})
            entities.append(entity)
        for match in self.py_docstring_pattern_alt.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            line_number = content[:start_pos].count('\n') + 1
            owner_type, owner_name = self._find_python_docstring_owner(content, start_pos)
            entity_type = self._get_entity_type_for_owner(owner_type)
            entity = DocumentationEntity(type=entity_type, content=docstring, file_path=file_path, source_text=match.group(0), start_pos=start_pos, end_pos=end_pos, line_number=line_number, metadata={'owner_type': owner_type, 'owner_name': owner_name, 'language': 'python'})
            entities.append(entity)
        return entities

    def _extract_js_docstrings(self: Any, content: str, file_path: str) -> list[DocumentationEntity]:
        """Extract JavaScript/TypeScript docstrings (JSDoc) from code content.

        Args:
            content: Code content
            file_path: Path to the code file

        Returns:
            List of docstring entities
        """
        entities: list[Any] = []
        for match in self.jsdoc_pattern.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            line_number = content[:start_pos].count('\n') + 1
            owner_type, owner_name = self._find_js_docstring_owner(content, end_pos)
            entity_type = self._get_entity_type_for_owner(owner_type)
            entity = DocumentationEntity(type=entity_type, content=docstring, file_path=file_path, source_text=match.group(0), start_pos=start_pos, end_pos=end_pos, line_number=line_number, metadata={'owner_type': owner_type, 'owner_name': owner_name, 'language': 'javascript'})
            entities.append(entity)
        return entities

    def _extract_javadoc_docstrings(self: Any, content: str, file_path: str) -> list[DocumentationEntity]:
        """Extract Java/C++/C# docstrings (Javadoc/Doxygen) from code content.

        Args:
            content: Code content
            file_path: Path to the code file

        Returns:
            List of docstring entities
        """
        entities: list[Any] = []
        for match in self.javadoc_pattern.finditer(content):
            docstring = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            line_number = content[:start_pos].count('\n') + 1
            owner_type, owner_name = self._find_java_docstring_owner(content, end_pos)
            entity_type = self._get_entity_type_for_owner(owner_type)
            entity = DocumentationEntity(type=entity_type, content=docstring, file_path=file_path, source_text=match.group(0), start_pos=start_pos, end_pos=end_pos, line_number=line_number, metadata={'owner_type': owner_type, 'owner_name': owner_name, 'language': 'java'})
            entities.append(entity)
        return entities

    def _find_python_docstring_owner(self: Any, content: str, pos: int) -> tuple[str, str]:
        """Find the owner (function, class, module) of a Python docstring.

        Args:
            content: Code content
            pos: Position of the docstring

        Returns:
            Tuple of (owner_type, owner_name)
        """
        line_number = content[:pos].count('\n')
        for match in self.py_function_pattern.finditer(content):
            func_line = content[:match.start()].count('\n')
            if func_line >= line_number - 1 and func_line <= line_number + 3:
                return ('function', match.group(1))
        for match in self.py_class_pattern.finditer(content):
            class_line = content[:match.start()].count('\n')
            if class_line >= line_number - 1 and class_line <= line_number + 3:
                return ('class', match.group(1))
        return ('module', 'module')

    def _find_js_docstring_owner(self: Any, content: str, pos: int) -> tuple[str, str]:
        """Find the owner (function, class, method) of a JavaScript/TypeScript docstring.

        Args:
            content: Code content
            pos: Position of the docstring

        Returns:
            Tuple of (owner_type, owner_name)
        """
        after_content = content[pos:pos + 500]
        func_match = self.js_function_pattern.search(after_content)
        if func_match:
            return ('function', func_match.group(1))
        method_match = self.js_method_pattern.search(after_content)
        if method_match:
            return ('method', method_match.group(1))
        class_match = self.js_class_pattern.search(after_content)
        if class_match:
            return ('class', class_match.group(1))
        return ('module', 'module')

    def _find_java_docstring_owner(self: Any, content: str, pos: int) -> tuple[str, str]:
        """Find the owner (method, class) of a Java/C++/C# docstring.

        Args:
            content: Code content
            pos: Position of the docstring

        Returns:
            Tuple of (owner_type, owner_name)
        """
        after_content = content[pos:pos + 500]
        method_match = self.java_method_pattern.search(after_content)
        if method_match:
            return ('method', method_match.group(1))
        class_match = self.java_class_pattern.search(after_content)
        if class_match:
            return ('class', class_match.group(1))
        return ('module', 'module')

    def _get_entity_type_for_owner(self: Any, owner_type: str) -> EntityType:
        """Get the appropriate entity type for a docstring owner.

        Args:
            owner_type: Type of the docstring owner

        Returns:
            EntityType for the docstring
        """
        if owner_type == 'function' or owner_type == 'method':
            return EntityType.FUNCTION_DESC
        elif owner_type == 'class':
            return EntityType.CLASS_DESC
        elif owner_type == 'module':
            return EntityType.MODULE_DESC
        else:
            return EntityType.PARAGRAPH

    def _extract_docstring_sections(self: Any, docstring: DocumentationEntity) -> list[DocumentationEntity]:
        """Extract sections (parameters, returns, etc.) from a docstring.

        Args:
            docstring: The docstring entity

        Returns:
            List of section entities
        """
        sections: list[Any] = []
        content = docstring.content
        file_path = docstring.file_path
        lines = content.split('\n')
        param_sections = self._extract_parameter_sections(lines, file_path, docstring.id)
        sections.extend(param_sections)
        return_sections = self._extract_return_sections(lines, file_path, docstring.id)
        sections.extend(return_sections)
        raises_sections = self._extract_raises_sections(lines, file_path, docstring.id)
        sections.extend(raises_sections)
        example_sections = self._extract_example_sections(lines, file_path, docstring.id)
        sections.extend(example_sections)
        return sections

    def _extract_parameter_sections(self: Any, lines: list[str], file_path: str, parent_id: str) -> list[DocumentationEntity]:
        """Extract parameter descriptions from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of parameter description entities
        """
        sections: list[Any] = []
        in_params = False
        param_section: list[str] = []
        for _i, line in enumerate(lines):
            if self.param_pattern.search(line):
                if param_section:
                    entity = DocumentationEntity(type=EntityType.PARAMETER_DESC, content='\n'.join(param_section), file_path=file_path, source_text='\n'.join(param_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    param_section: list[Any] = [][no - redef]
                in_params = True
                param_section.append(line)
            elif in_params and (line.strip() == '' or line.startswith(' ') or line.startswith('\t')):
                param_section.append(line)
            elif in_params:
                if param_section:
                    entity = DocumentationEntity(type=EntityType.PARAMETER_DESC, content='\n'.join(param_section), file_path=file_path, source_text='\n'.join(param_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    param_section: list[Any] = [][no - redef]
                in_params = False
        if param_section:
            entity = DocumentationEntity(type=EntityType.PARAMETER_DESC, content='\n'.join(param_section), file_path=file_path, source_text='\n'.join(param_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
            sections.append(entity)
        return sections

    def _extract_return_sections(self: Any, lines: list[str], file_path: str, parent_id: str) -> list[DocumentationEntity]:
        """Extract return descriptions from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of return description entities
        """
        sections: list[Any] = []
        in_returns = False
        return_section: list[str] = []
        for _i, line in enumerate(lines):
            if self.return_pattern.search(line):
                if return_section:
                    entity = DocumentationEntity(type=EntityType.RETURN_DESC, content='\n'.join(return_section), file_path=file_path, source_text='\n'.join(return_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    return_section: list[Any] = [][no - redef]
                in_returns = True
                return_section.append(line)
            elif in_returns and (line.strip() == '' or line.startswith(' ') or line.startswith('\t')):
                return_section.append(line)
            elif in_returns:
                if return_section:
                    entity = DocumentationEntity(type=EntityType.RETURN_DESC, content='\n'.join(return_section), file_path=file_path, source_text='\n'.join(return_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    return_section: list[Any] = [][no - redef]
                in_returns = False
        if return_section:
            entity = DocumentationEntity(type=EntityType.RETURN_DESC, content='\n'.join(return_section), file_path=file_path, source_text='\n'.join(return_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
            sections.append(entity)
        return sections

    def _extract_raises_sections(self: Any, lines: list[str], file_path: str, parent_id: str) -> list[DocumentationEntity]:
        """Extract exception/raises descriptions from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of exception description entities
        """
        sections: list[Any] = []
        in_raises = False
        raises_section: list[str] = []
        for _i, line in enumerate(lines):
            if self.raises_pattern.search(line):
                if raises_section:
                    entity = DocumentationEntity(type=EntityType.EXCEPTION_DESC, content='\n'.join(raises_section), file_path=file_path, source_text='\n'.join(raises_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    raises_section: list[Any] = [][no - redef]
                in_raises = True
                raises_section.append(line)
            elif in_raises and (line.strip() == '' or line.startswith(' ') or line.startswith('\t')):
                raises_section.append(line)
            elif in_raises:
                if raises_section:
                    entity = DocumentationEntity(type=EntityType.EXCEPTION_DESC, content='\n'.join(raises_section), file_path=file_path, source_text='\n'.join(raises_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    raises_section: list[Any] = [][no - redef]
                in_raises = False
        if raises_section:
            entity = DocumentationEntity(type=EntityType.EXCEPTION_DESC, content='\n'.join(raises_section), file_path=file_path, source_text='\n'.join(raises_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
            sections.append(entity)
        return sections

    def _extract_example_sections(self: Any, lines: list[str], file_path: str, parent_id: str) -> list[DocumentationEntity]:
        """Extract example sections from docstring lines.

        Args:
            lines: Docstring lines
            file_path: Path to the file
            parent_id: ID of the parent docstring entity

        Returns:
            List of example entities
        """
        sections: list[Any] = []
        in_example = False
        example_section: list[Any] = []
        for _i, line in enumerate(lines):
            if self.example_pattern.search(line):
                if example_section:
                    entity = DocumentationEntity(type=EntityType.EXAMPLE, content='\n'.join(example_section), file_path=file_path, source_text='\n'.join(example_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    example_section: list[Any] = [][no - redef]
                in_example = True
                example_section.append(line)
            elif in_example and (line.strip() == '' or line.startswith(' ') or line.startswith('\t')):
                example_section.append(line)
            elif in_example:
                if example_section:
                    entity = DocumentationEntity(type=EntityType.EXAMPLE, content='\n'.join(example_section), file_path=file_path, source_text='\n'.join(example_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
                    sections.append(entity)
                    example_section: list[Any] = [][no - redef]
                in_example = False
        if example_section:
            entity = DocumentationEntity(type=EntityType.EXAMPLE, content='\n'.join(example_section), file_path=file_path, source_text='\n'.join(example_section), start_pos=None, end_pos=None, line_number=None, parent_id=parent_id, metadata={})
            sections.append(entity)
        return sections