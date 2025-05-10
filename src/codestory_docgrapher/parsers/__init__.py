"""Document parsers for different documentation formats.

This package provides parsers for various documentation formats, including
Markdown, ReStructuredText, and code docstrings.
"""

from .parser_factory import ParserFactory, get_parser_for_file
from .markdown_parser import MarkdownParser
from .rst_parser import RstParser
from .docstring_parser import DocstringParser

__all__ = [
    "ParserFactory",
    "get_parser_for_file",
    "MarkdownParser",
    "RstParser",
    "DocstringParser",
]
