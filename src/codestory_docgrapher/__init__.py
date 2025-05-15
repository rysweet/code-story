"""Documentation Grapher workflow step for Code Story ingestion pipeline.

This package implements a workflow step that creates a knowledge graph
of documentation and links it to code entities in the repository.
"""

from .step import DocumentationGrapherStep

__all__ = ["DocumentationGrapherStep"]
