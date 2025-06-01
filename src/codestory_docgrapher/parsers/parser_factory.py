from collections.abc import Callable
from typing import Dict, Optional, Type

"Parser factory for creating appropriate parsers for different document types.\n\nThis module provides a factory for creating the appropriate parser based on\nthe type of documentation file.\n"
import logging

from ..models import DocumentationFile, DocumentType

logger = logging.getLogger(__name__)


class Parser:
    """Base class for document parsers.

    All document parsers should implement this interface.
    """

    def parse(self, document: DocumentationFile) -> dict[str, object]:
        """Parse a documentation file and extract entities and relationships.

        Args:
            document: The documentation file to parse

        Returns:
            Dict containing extracted entities and relationships
        """
        raise NotImplementedError("Subclasses must implement parse()")


class ParserFactory:
    """Factory for creating parsers based on document type.

    This class creates the appropriate parser for a given document type.
    """

    _parsers: Dict[DocumentType, Type[Parser]] = {}

    @classmethod
    def register(cls, doc_type: DocumentType) -> Callable[[Type[Parser]], Type[Parser]]:
        """Register a parser class for a document type.

        This is a decorator for registering parser classes.

        Args:
            doc_type: The document type to register the parser for

        Returns:
            Decorator function
        """

        def decorator(parser_class: Type[Parser]) -> Type[Parser]:
            cls._parsers[doc_type] = parser_class
            return parser_class

        return decorator

    @classmethod
    def create(cls, doc_type: DocumentType) -> Optional[Parser]:
        """Create a parser for the given document type.

        Args:
            doc_type: The document type to create a parser for

        Returns:
            An instance of the appropriate parser, or None if no parser is registered
        """
        parser_class = cls._parsers.get(doc_type)
        if parser_class is None:
            logger.warning(f"No parser registered for document type: {doc_type}")
            return None
        return parser_class()


def get_parser_for_file(document: DocumentationFile) -> Optional[Parser]:
    """Get a parser for the given documentation file.

    Args:
        document: The documentation file to get a parser for

    Returns:
        An instance of the appropriate parser, or None if no parser is registered
    """
    return ParserFactory.create(document.doc_type)
