"""Document parsers for different documentation formats.

This package provides parsers for various documentation formats, including
Markdown, ReStructuredText, and code docstrings.
"""

from .docstring_parser import DocstringParser
from .markdown_parser import MarkdownParser
from .parser_factory import ParserFactory, get_parser_for_file
from .rst_parser import RstParser

__all__ = [
    "DocstringParser",
    "MarkdownParser",
    "ParserFactory",
    "RstParser",
    "get_parser_for_file",
]
