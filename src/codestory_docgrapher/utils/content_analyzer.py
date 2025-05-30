from typing import Any
'Content analyzer for documentation content.\n\nThis module provides functionality for analyzing documentation content\nto extract entities, relationships, and other information.\n'
import logging
import re
from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole
from ..models import DocumentationEntity, EntityType
logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Analyzes documentation content for entities and relationships.

    This class uses patterns and LLM analysis to extract entities,
    relationships, and other structured information from documentation content.
    """

    def __init__(self: Any, use_llm: bool=True) -> None:
        """Initialize the content analyzer.

        Args:
            use_llm: Whether to use LLM for advanced analysis
        """
        self.use_llm = use_llm
        self.llm_client = create_client() if use_llm else None
        self.heading_pattern = re.compile('^(#+)\\s+(.+)$', re.MULTILINE)
        self.code_block_pattern = re.compile('```(\\w*)\\n(.*?)\\n```', re.DOTALL)
        self.api_reference_pattern = re.compile('`([^`]+)`')
        self.api_function_pattern = re.compile('`([a-zA-Z0-9_]+\\(\\))`')
        self.api_class_pattern = re.compile('`([A-Z][a-zA-Z0-9_]*)`')
        self.api_module_pattern = re.compile('`([a-zA-Z0-9_]+\\.[a-zA-Z0-9_]+)`')

    def analyze_entity_content(self: Any, entity: DocumentationEntity) -> dict[str, Any]:
        """Analyze the content of a documentation entity.

        Args:
            entity: The documentation entity to analyze

        Returns:
            Dict with analysis results
        """
        content = entity.content
        if entity.type == EntityType.HEADING:
            return self._analyze_heading(content)
        elif entity.type == EntityType.CODE_BLOCK:
            return self._analyze_code_block(content, entity.metadata.get('language', ''))
        elif entity.type == EntityType.FUNCTION_DESC:
            return self._analyze_function_desc(content)
        elif entity.type == EntityType.CLASS_DESC:
            return self._analyze_class_desc(content)
        elif entity.type == EntityType.MODULE_DESC:
            return self._analyze_module_desc(content)
        else:
            return self._analyze_generic(content)

    def _analyze_heading(self: Any, content: str) -> dict[str, Any]:
        """Analyze a heading.

        Args:
            content: Heading content

        Returns:
            Dict with analysis results
        """
        keywords = self._extract_keywords(content)
        section_type = 'generic'
        if any((kw in content.lower() for kw in ['install', 'setup', 'getting started'])):
            section_type = 'installation'
        elif any((kw in content.lower() for kw in ['usage', 'example', 'how to'])):
            section_type = 'usage'
        elif any((kw in content.lower() for kw in ['api', 'reference', 'documentation'])):
            section_type = 'api'
        elif any((kw in content.lower() for kw in ['config', 'configuration', 'setting'])):
            section_type = 'configuration'
        return {'keywords': keywords, 'section_type': section_type}

    def _analyze_code_block(self: Any, content: str, language: str) -> dict[str, Any]:
        """Analyze a code block.

        Args:
            content: Code block content
            language: Programming language of the code block

        Returns:
            Dict with analysis results
        """
        lines = content.strip().split('\n')
        line_count = len(lines)
        is_example = False
        if any((line.strip().startswith('# Example') for line in lines)):
            is_example = True
        dependencies: list[Any] = []
        if language in ['python', 'py']:
            for line in lines:
                if re.match('^import\\s+|^from\\s+\\w+\\s+import', line.strip()):
                    dependencies.append(line.strip())
        elif language in ['javascript', 'js', 'typescript', 'ts']:
            for line in lines:
                if re.match('^import\\s+|^const\\s+\\w+\\s*=\\s*require', line.strip()):
                    dependencies.append(line.strip())
        definitions: list[Any] = []
        if language in ['python', 'py']:
            for line in lines:
                if re.match('^def\\s+\\w+|^class\\s+\\w+', line.strip()):
                    definitions.append(line.strip())
        elif language in ['javascript', 'js', 'typescript', 'ts']:
            for line in lines:
                if re.match('^function\\s+\\w+|^class\\s+\\w+|^const\\s+\\w+\\s*=\\s*function', line.strip()):
                    definitions.append(line.strip())
        return {'language': language, 'line_count': line_count, 'is_example': is_example, 'dependencies': dependencies, 'definitions': definitions}

    def _analyze_function_desc(self: Any, content: str) -> dict[str, Any]:
        """Analyze a function description.

        Args:
            content: Function description content

        Returns:
            Dict with analysis results
        """
        param_pattern = re.compile('@param|:param|Parameters:|Args:|Arguments:')
        params: list[Any] = []
        for line in content.split('\n'):
            if param_pattern.search(line):
                params.append(line.strip())
        return_pattern = re.compile('@return|:return|Returns:|Return:')
        returns: list[Any] = []
        for line in content.split('\n'):
            if return_pattern.search(line):
                returns.append(line.strip())
        raises_pattern = re.compile('@raises|:raises|Raises:|Exceptions:|:except')
        raises: list[Any] = []
        for line in content.split('\n'):
            if raises_pattern.search(line):
                raises.append(line.strip())
        purpose = ''
        if self.use_llm and self.llm_client:
            purpose = self._extract_function_purpose(content)
        return {'parameters': params, 'returns': returns, 'raises': raises, 'purpose': purpose}

    def _analyze_class_desc(self: Any, content: str) -> dict[str, Any]:
        """Analyze a class description.

        Args:
            content: Class description content

        Returns:
            Dict with analysis results
        """
        method_pattern = re.compile('@method|:method|Methods:|Method:')
        methods: list[Any] = []
        for line in content.split('\n'):
            if method_pattern.search(line):
                methods.append(line.strip())
        attr_pattern = re.compile('@attribute|:attribute|Attributes:|Attribute:')
        attributes: list[Any] = []
        for line in content.split('\n'):
            if attr_pattern.search(line):
                attributes.append(line.strip())
        purpose = ''
        if self.use_llm and self.llm_client:
            purpose = self._extract_class_purpose(content)
        return {'methods': methods, 'attributes': attributes, 'purpose': purpose}

    def _analyze_module_desc(self: Any, content: str) -> dict[str, Any]:
        """Analyze a module description.

        Args:
            content: Module description content

        Returns:
            Dict with analysis results
        """
        class_pattern = re.compile('@class|:class|Classes:|Class:')
        classes: list[Any] = []
        for line in content.split('\n'):
            if class_pattern.search(line):
                classes.append(line.strip())
        func_pattern = re.compile('@function|:function|Functions:|Function:')
        functions: list[Any] = []
        for line in content.split('\n'):
            if func_pattern.search(line):
                functions.append(line.strip())
        purpose = ''
        if self.use_llm and self.llm_client:
            purpose = self._extract_module_purpose(content)
        return {'classes': classes, 'functions': functions, 'purpose': purpose}

    def _analyze_generic(self: Any, content: str) -> dict[str, Any]:
        """Analyze generic content.

        Args:
            content: Content to analyze

        Returns:
            Dict with analysis results
        """
        api_refs: list[Any] = []
        for match in self.api_reference_pattern.finditer(content):
            api_refs.append(match.group(1))
        keywords = self._extract_keywords(content)
        return {'api_references': api_refs, 'keywords': keywords}

    def _extract_keywords(self: Any, content: str) -> list[str]:
        """Extract keywords from content.

        Args:
            content: Content to extract keywords from

        Returns:
            List of keywords
        """
        words = re.findall('\\b[a-zA-Z][a-zA-Z0-9_]{2,}\\b', content.lower())
        stop_words = {'the', 'and', 'is', 'in', 'to', 'of', 'for', 'with', 'this', 'that', 'it', 'on', 'as', 'by', 'an', 'are', 'be', 'or', 'from'}
        keywords = [w for w in words if w not in stop_words]
        word_counts: dict[str, int] = {}
        for word in keywords:
            word_counts[word] = word_counts.get(word, 0) + 1
        sorted_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [k for k, _ in sorted_keywords[:10]]

    def _extract_function_purpose(self: Any, content: str) -> str:
        """Extract function purpose using LLM.

        Args:
            content: Function description content

        Returns:
            Function purpose
        """
        prompt = f'\n        Extract the purpose of this function from its docstring. Return a single sentence\n        that describes what the function does, starting with a verb.\n        \n        Docstring:\n        {content}\n        \n        Function purpose:\n        '
        messages = [ChatMessage(role=ChatRole.SYSTEM, content='You are a technical documentation analyzer.'), ChatMessage(role=ChatRole.USER, content=prompt)]
        try:
            response = self.llm_client.chat(messages=messages, max_tokens=100, temperature=0.0)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f'Error extracting function purpose: {e}')
            return ''

    def _extract_class_purpose(self: Any, content: str) -> str:
        """Extract class purpose using LLM.

        Args:
            content: Class description content

        Returns:
            Class purpose
        """
        prompt = f'\n        Extract the purpose of this class from its docstring. Return a single sentence\n        that describes what the class represents or does.\n        \n        Docstring:\n        {content}\n        \n        Class purpose:\n        '
        messages = [ChatMessage(role=ChatRole.SYSTEM, content='You are a technical documentation analyzer.'), ChatMessage(role=ChatRole.USER, content=prompt)]
        try:
            response = self.llm_client.chat(messages=messages, max_tokens=100, temperature=0.0)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f'Error extracting class purpose: {e}')
            return ''

    def _extract_module_purpose(self: Any, content: str) -> str:
        """Extract module purpose using LLM.

        Args:
            content: Module description content

        Returns:
            Module purpose
        """
        prompt = f'\n        Extract the purpose of this module from its docstring. Return a single sentence\n        that describes what the module provides or does.\n        \n        Docstring:\n        {content}\n        \n        Module purpose:\n        '
        messages = [ChatMessage(role=ChatRole.SYSTEM, content='You are a technical documentation analyzer.'), ChatMessage(role=ChatRole.USER, content=prompt)]
        try:
            response = self.llm_client.chat(messages=messages, max_tokens=100, temperature=0.0)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f'Error extracting module purpose: {e}')
            return ''