"""Filesystem step for the ingestion pipeline.

This module provides a workflow step that processes the filesystem structure
of a repository, creating a graph of directories and files that can be linked
to AST nodes.
"""

try:
    from .step import FileSystemStep
    __all__ = ["FileSystemStep"]
except ImportError:
    # The step module may not be available during testing
    __all__ = []
EOF < /dev/null