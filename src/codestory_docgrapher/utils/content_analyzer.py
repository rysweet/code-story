from typing import Any

"""Content analyzer for documentation content.

This module provides functionality for analyzing documentation content
to extract entities, relationships, and other information.
"""

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

    def __init__(self, use_llm: bool = True) -> None:
        """Initialize the content analyzer.

        Args:
            use_llm: Whether to use LLM for advanced analysis
        """
        self.use_llm = use_llm
        self.llm_client = create_client() if use_llm else None

        # Regular expressions for common patterns
        self.heading_pattern = re.compile(r"^(#+)\s+(.+)$", re.MULTILINE)
        self.code_block_pattern = re.compile(r"```(\w*)\n(.*?)\n```", re.DOTALL)
        self.api_reference_pattern = re.compile(r"`([^`]+)`")
        self.api_function_pattern = re.compile(r"`([a-zA-Z0-9_]+\(\))`")
        self.api_class_pattern = re.compile(r"`([A-Z][a-zA-Z0-9_]*)`")
        self.api_module_pattern = re.compile(r"`([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)`")

    def analyze_entity_content(self, entity: DocumentationEntity) -> dict[str, Any]:
        """Analyze the content of a documentation entity.

        Args:
            entity: The documentation entity to analyze

        Returns:
            Dict with analysis results
        """
        content = entity.content

        # Use appropriate analysis method based on entity type
        if entity.type == EntityType.HEADING:
            return self._analyze_heading(content)
        elif entity.type == EntityType.CODE_BLOCK:
            language = entity.metadata.get("language", "")
            # Ensure language is always a string for type safety
            if not isinstance(language, str):
                language = str(language)
            return self._analyze_code_block(content, language)
        elif entity.type == EntityType.FUNCTION_DESC:
            return self._analyze_function_desc(content)
        elif entity.type == EntityType.CLASS_DESC:
            return self._analyze_class_desc(content)
        elif entity.type == EntityType.MODULE_DESC:
            return self._analyze_module_desc(content)
        else:
            # Generic analysis for other entity types
            return self._analyze_generic(content)

    def _analyze_heading(self, content: str) -> dict[str, Any]:
        """Analyze a heading.

        Args:
            content: Heading content

        Returns:
            Dict with analysis results
        """
        # Extract semantic information from heading
        keywords = self._extract_keywords(content)

        # Check if heading indicates a specific section type
        section_type = "generic"
        if any(kw in content.lower() for kw in ["install", "setup", "getting started"]):
            section_type = "installation"
        elif any(kw in content.lower() for kw in ["usage", "example", "how to"]):
            section_type = "usage"
        elif any(kw in content.lower() for kw in ["api", "reference", "documentation"]):
            section_type = "api"
        elif any(
            kw in content.lower() for kw in ["config", "configuration", "setting"]
        ):
            section_type = "configuration"

        return {"keywords": keywords, "section_type": section_type}

    def _analyze_code_block(self, content: str, language: str) -> dict[str, Any]:
        """Analyze a code block.

        Args:
            content: Code block content
            language: Programming language of the code block

        Returns:
            Dict with analysis results
        """
        # Count lines of code
        lines = content.strip().split("\n")
        line_count = len(lines)

        # Detect if this is an example or usage snippet
        is_example = False
        if any(line.strip().startswith("# Example") for line in lines):
            is_example = True

        # Extract imports/dependencies
        dependencies: list[Any] = []
        if language in ["python", "py"]:
            for line in lines:
                if re.match(r"^import\s+|^from\s+\w+\s+import", line.strip()):
                    dependencies.append(line.strip())
        elif language in ["javascript", "js", "typescript", "ts"]:
            for line in lines:
                if re.match(r"^import\s+|^const\s+\w+\s*=\s*require", line.strip()):
                    dependencies.append(line.strip())

        # Extract function/class definitions
        definitions: list[Any] = []
        if language in ["python", "py"]:
            for line in lines:
                if re.match(r"^def\s+\w+|^class\s+\w+", line.strip()):
                    definitions.append(line.strip())
        elif language in ["javascript", "js", "typescript", "ts"]:
            for line in lines:
                if re.match(
                    r"^function\s+\w+|^class\s+\w+|^const\s+\w+\s*=\s*function",
                    line.strip(),
                ):
                    definitions.append(line.strip())

        return {
            "language": language,
            "line_count": line_count,
            "is_example": is_example,
            "dependencies": dependencies,
            "definitions": definitions,
        }

    def _analyze_function_desc(self, content: str) -> dict[str, Any]:
        """Analyze a function description.

        Args:
            content: Function description content

        Returns:
            Dict with analysis results
        """
        # Extract parameter descriptions
        param_pattern = re.compile(r"@param|:param|Parameters:|Args:|Arguments:")
        params: list[Any] = []
        for line in content.split("\n"):
            if param_pattern.search(line):
                params.append(line.strip())

        # Extract return descriptions
        return_pattern = re.compile(r"@return|:return|Returns:|Return:")
        returns: list[Any] = []
        for line in content.split("\n"):
            if return_pattern.search(line):
                returns.append(line.strip())

        # Extract raises/exceptions
        raises_pattern = re.compile(r"@raises|:raises|Raises:|Exceptions:|:except")
        raises: list[Any] = []
        for line in content.split("\n"):
            if raises_pattern.search(line):
                raises.append(line.strip())

        # Use LLM to extract function purpose if enabled
        purpose = ""
        if self.use_llm and self.llm_client:
            # mypy: ensure llm_client is not None
            purpose = self._extract_function_purpose(content)

        return {
            "parameters": params,
            "returns": returns,
            "raises": raises,
            "purpose": purpose,
        }

    def _analyze_class_desc(self, content: str) -> dict[str, Any]:
        """Analyze a class description.

        Args:
            content: Class description content

        Returns:
            Dict with analysis results
        """
        # Extract method descriptions
        method_pattern = re.compile(r"@method|:method|Methods:|Method:")
        methods: list[Any] = []
        for line in content.split("\n"):
            if method_pattern.search(line):
                methods.append(line.strip())

        # Extract attribute descriptions
        attr_pattern = re.compile(r"@attribute|:attribute|Attributes:|Attribute:")
        attributes: list[Any] = []
        for line in content.split("\n"):
            if attr_pattern.search(line):
                attributes.append(line.strip())

        # Use LLM to extract class purpose if enabled
        purpose = ""
        if self.use_llm and self.llm_client:
            purpose = self._extract_class_purpose(content)

        return {"methods": methods, "attributes": attributes, "purpose": purpose}

    def _analyze_module_desc(self, content: str) -> dict[str, Any]:
        """Analyze a module description.

        Args:
            content: Module description content

        Returns:
            Dict with analysis results
        """
        # Extract exported classes
        class_pattern = re.compile(r"@class|:class|Classes:|Class:")
        classes: list[Any] = []
        for line in content.split("\n"):
            if class_pattern.search(line):
                classes.append(line.strip())

        # Extract exported functions
        func_pattern = re.compile(r"@function|:function|Functions:|Function:")
        functions: list[Any] = []
        for line in content.split("\n"):
            if func_pattern.search(line):
                functions.append(line.strip())

        # Use LLM to extract module purpose if enabled
        purpose = ""
        if self.use_llm and self.llm_client:
            purpose = self._extract_module_purpose(content)

        return {"classes": classes, "functions": functions, "purpose": purpose}

    def _analyze_generic(self, content: str) -> dict[str, Any]:
        """Analyze generic content.

        Args:
            content: Content to analyze

        Returns:
            Dict with analysis results
        """
        # Extract API references
        api_refs: list[Any] = []
        for match in self.api_reference_pattern.finditer(content):
            api_refs.append(match.group(1))

        # Extract keywords
        keywords = self._extract_keywords(content)

        return {"api_references": api_refs, "keywords": keywords}

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract keywords from content.

        Args:
            content: Content to extract keywords from

        Returns:
            List of keywords
        """
        # Simple keyword extraction based on word frequency
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", content.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "and",
            "is",
            "in",
            "to",
            "of",
            "for",
            "with",
            "this",
            "that",
            "it",
            "on",
            "as",
            "by",
            "an",
            "are",
            "be",
            "or",
            "from",
        }

        keywords = [w for w in words if w not in stop_words]

        # Count word frequency
        word_counts: dict[str, int] = {}
        for word in keywords:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Get top keywords by frequency
        sorted_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [k for k, _ in sorted_keywords[:10]]

    def _extract_function_purpose(self, content: str) -> str:
        """Extract function purpose using LLM.

        Args:
            content: Function description content

        Returns:
            Function purpose
        """
        prompt = f"""
        Extract the purpose of this function from its docstring. Return a single sentence
        that describes what the function does, starting with a verb.
        
        Docstring:
        {content}
        
        Function purpose:
        """

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a technical documentation analyzer.",
            ),
            ChatMessage(role=ChatRole.USER, content=prompt),
        ]

        try:
            assert self.llm_client is not None
            response = self.llm_client.chat(
                messages=messages, max_tokens=100, temperature=0.0
            )
            result = response.choices[0].message.content
            return result.strip() if isinstance(result, str) else ""
        except Exception as e:
            logger.warning(f"Error extracting function purpose: {e}")
            return ""

    def _extract_class_purpose(self, content: str) -> str:
        """Extract class purpose using LLM.

        Args:
            content: Class description content

        Returns:
            Class purpose
        """
        prompt = f"""
        Extract the purpose of this class from its docstring. Return a single sentence
        that describes what the class represents or does.

        Docstring:
        {content}

        Class purpose:
        """

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a technical documentation analyzer.",
            ),
            ChatMessage(role=ChatRole.USER, content=prompt),
        ]

        try:
            assert self.llm_client is not None
            response = self.llm_client.chat(
                messages=messages, max_tokens=100, temperature=0.0
            )
            result = response.choices[0].message.content
            return result.strip() if isinstance(result, str) else ""
        except Exception as e:
            logger.warning(f"Error extracting class purpose: {e}")
            return ""

    def _extract_module_purpose(self, content: str) -> str:
        """Extract module purpose using LLM.

        Args:
            content: Module description content

        Returns:
            Module purpose
        """
        prompt = f"""
        Extract the purpose of this module from its docstring. Return a single sentence
        that describes what the module provides or does.

        Docstring:
        {content}

        Module purpose:
        """

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a technical documentation analyzer.",
            ),
            ChatMessage(role=ChatRole.USER, content=prompt),
        ]

        try:
            assert self.llm_client is not None
            response = self.llm_client.chat(
                messages=messages, max_tokens=100, temperature=0.0
            )
            result = response.choices[0].message.content
            return result.strip() if isinstance(result, str) else ""
        except Exception as e:
            logger.warning(f"Error extracting module purpose: {e}")
            return ""
