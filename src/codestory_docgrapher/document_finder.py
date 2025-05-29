from typing import Any

"""Document finder for locating documentation files in repositories.

This module provides functionality for locating documentation files
within a repository, including Markdown files, README files, and
documentation within code files.
"""

import logging
import os
import re

from codestory.graphdb.neo4j_connector import Neo4jConnector

from .models import DocumentationFile, DocumentType

logger = logging.getLogger(__name__)


class DocumentFinder:
    """Locates documentation files in a repository.

    This class searches for documentation files in a repository, including
    standalone documentation files (Markdown, RST) and documentation within
    code files (docstrings, comments).
    """

    def __init__(self, connector: Neo4jConnector, repository_path: str) -> None:
        """Initialize the document finder.

        Args:
            connector: Neo4j database connector
            repository_path: Path to the repository
        """
        self.connector = connector
        self.repository_path = repository_path
        self.doc_extensions = {
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".rst": DocumentType.RESTRUCTURED_TEXT,
            ".txt": DocumentType.OTHER,
        }
        self.doc_filenames = {
            "readme": DocumentType.README,
            "contributing": DocumentType.DEVELOPER_GUIDE,
            "changelog": DocumentType.DEVELOPER_GUIDE,
            "license": DocumentType.OTHER,
            "authors": DocumentType.OTHER,
            "api": DocumentType.API_DOC,
            "tutorial": DocumentType.TUTORIAL,
            "guide": DocumentType.USER_GUIDE,
            "docs": DocumentType.OTHER,
        }
        self.doc_directories = {
            "docs",
            "doc",
            "documentation",
            "wiki",
            "guides",
            "tutorials",
        }

    def find_documentation_files(
        self, ignore_patterns: list[str] | None = None
    ) -> list[DocumentationFile]:
        """Find documentation files in the repository.

        Args:
            ignore_patterns: Optional list of patterns to ignore

        Returns:
            List of DocumentationFile objects
        """
        ignore_patterns = ignore_patterns or []
        ignore_regex = self._compile_ignore_patterns(ignore_patterns)

        doc_files: list[Any] = []
        doc_files.extend(self._find_standalone_docs(ignore_regex))
        doc_files.extend(self._find_code_docstrings(ignore_regex))

        logger.info(f"Found {len(doc_files)} documentation files in repository")
        return doc_files

    def _compile_ignore_patterns(self, patterns: list[str]) -> list[re.Pattern[str]]:
        """Compile ignore patterns into regular expressions.

        Args:
            patterns: List of glob patterns to ignore

        Returns:
            List of compiled regular expressions
        """
        result: list[Any] = []
        for pattern in patterns:
            # Convert glob pattern to regex
            regex = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
            try:
                result.append(re.compile(regex))
            except re.error:
                logger.warning(f"Invalid ignore pattern: {pattern}")
        return result

    def _should_ignore(self, path: str, ignore_patterns: list[re.Pattern[str]]) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check
            ignore_patterns: List of patterns to ignore

        Returns:
            True if the path should be ignored, False otherwise
        """
        return any(pattern.search(path) for pattern in ignore_patterns)

    def _find_standalone_docs(self, ignore_patterns: list[re.Pattern[str]]) -> list[DocumentationFile]:
        """Find standalone documentation files (Markdown, RST, etc.).

        Args:
            ignore_patterns: List of patterns to ignore

        Returns:
            List of DocumentationFile objects
        """
        result: list[Any] = []

        # Query Neo4j for file nodes
        query = """
        MATCH (f:File)
        RETURN ID(f) as id, f.path as path, f.name as name, f.extension as extension
        """

        files = self.connector.run_query(query, fetch_all=True)

        for file_data in files:
            file_path = file_data["path"]
            file_name = file_data["name"].lower()
            file_extension = file_data.get("extension", "").lower()
            file_id = str(file_data["id"])

            # Skip ignored files
            if self._should_ignore(file_path, ignore_patterns):
                continue

            # Check if the file is a documentation file by extension
            doc_type = None
            if f".{file_extension}" in self.doc_extensions:
                doc_type = self.doc_extensions[f".{file_extension}"]

            # Check if the file is a documentation file by name
            for doc_name, doc_name_type in self.doc_filenames.items():
                if doc_name in file_name:
                    doc_type = doc_name_type
                    break

            # Check if the file is in a documentation directory
            if not doc_type:
                for doc_dir in self.doc_directories:
                    if f"/{doc_dir}/" in file_path.lower():
                        # Determine type based on extension if possible
                        if f".{file_extension}" in self.doc_extensions:
                            doc_type = self.doc_extensions[f".{file_extension}"]
                        else:
                            doc_type = DocumentType.OTHER
                        break

            # If this is a documentation file, add it to the result
            if doc_type:
                # Read the file content
                absolute_path = os.path.join(self.repository_path, file_path)
                try:
                    with open(absolute_path, encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Error reading file {absolute_path}: {e}")
                    content = ""

                doc_file = DocumentationFile(
                    path=file_path,
                    name=file_data["name"],
                    doc_type=doc_type,
                    content=content,
                    file_id=file_id,
                    metadata={"extension": file_extension},
                )
                result.append(doc_file)

        return result

    def _find_code_docstrings(self, ignore_patterns: list[re.Pattern[str]]) -> list[DocumentationFile]:
        """Find documentation within code files (docstrings, comments).

        Args:
            ignore_patterns: List of patterns to ignore

        Returns:
            List of DocumentationFile objects
        """
        result: list[Any] = []

        # Query Neo4j for files with docstrings
        query = """
        MATCH (f:File)
        WHERE f.extension IN ["py", "js", "ts", "java", "c", "cpp", "h", "hpp"]
        RETURN ID(f) as id, f.path as path, f.name as name, f.extension as extension
        """

        files = self.connector.run_query(query, fetch_all=True)

        for file_data in files:
            file_path = file_data["path"]
            file_extension = file_data.get("extension", "").lower()
            file_id = str(file_data["id"])

            # Skip ignored files
            if self._should_ignore(file_path, ignore_patterns):
                continue

            # Check if there are docstrings in the file
            absolute_path = os.path.join(self.repository_path, file_path)

            # For Python files, we specifically look for docstrings
            if file_extension == "py":
                try:
                    with open(absolute_path, encoding="utf-8") as f:
                        content = f.read()

                        # Simple docstring detection
                        if '"""' in content or "'''" in content:
                            doc_file = DocumentationFile(
                                path=file_path,
                                name=file_data["name"],
                                doc_type=DocumentType.DOCSTRING,
                                content=content,
                                file_id=file_id,
                                metadata={
                                    "extension": file_extension,
                                    "source_type": "python",
                                },
                            )
                            result.append(doc_file)
                except Exception as e:
                    logger.warning(f"Error reading file {absolute_path}: {e}")

            # For JavaScript, TypeScript files - check for JSDoc
            elif file_extension in ["js", "ts"]:
                try:
                    with open(absolute_path, encoding="utf-8") as f:
                        content = f.read()

                        # Simple JSDoc detection
                        if "/**" in content and "*/" in content:
                            doc_file = DocumentationFile(
                                path=file_path,
                                name=file_data["name"],
                                doc_type=DocumentType.DOCSTRING,
                                content=content,
                                file_id=file_id,
                                metadata={
                                    "extension": file_extension,
                                    "source_type": "javascript"
                                    if file_extension == "js"
                                    else "typescript",
                                },
                            )
                            result.append(doc_file)
                except Exception as e:
                    logger.warning(f"Error reading file {absolute_path}: {e}")

            # For Java, C, C++ files
            elif file_extension in ["java", "c", "cpp", "h", "hpp"]:
                try:
                    with open(absolute_path, encoding="utf-8") as f:
                        content = f.read()

                        # Simple Javadoc/Doxygen detection
                        if "/**" in content and "*/" in content:
                            doc_file = DocumentationFile(
                                path=file_path,
                                name=file_data["name"],
                                doc_type=DocumentType.DOCSTRING,
                                content=content,
                                file_id=file_id,
                                metadata={
                                    "extension": file_extension,
                                    "source_type": file_extension,
                                },
                            )
                            result.append(doc_file)
                except Exception as e:
                    logger.warning(f"Error reading file {absolute_path}: {e}")

        return result
