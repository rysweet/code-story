"""Utilities for extracting code content to summarize.

This module provides functionality for extracting code content and context
for summarization from the Neo4j database.
"""

import logging
import os

from codestory.graphdb.neo4j_connector import Neo4jConnector

from ..models import NodeData, NodeType

# Set up logging
logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extracts code content and context for summarization.

    This class queries the Neo4j database to extract code content and
    relevant context for summarization of different node types.
    """

    def __init__(
        self, connector: Neo4jConnector, repository_path: str | None = None
    ):
        """Initialize the content extractor.

        Args:
            connector: Neo4j database connector
            repository_path: Optional path to the repository root
        """
        self.connector = connector
        self.repository_path = repository_path
        self.cache: dict[str, str] = {}  # Cache file contents

    def extract_content(self, node: NodeData) -> dict[str, str | list[str]]:
        """Extract content for a node based on its type.

        Args:
            node: Node to extract content for

        Returns:
            dict containing content and context for the node
        """
        node_type = node.type

        if node_type == NodeType.REPOSITORY:
            return self._extract_repository_content(node)
        elif node_type == NodeType.DIRECTORY:
            return self._extract_directory_content(node)
        elif node_type == NodeType.FILE:
            return self._extract_file_content(node)
        elif node_type == NodeType.CLASS:
            return self._extract_class_content(node)
        elif node_type in (NodeType.FUNCTION, NodeType.METHOD):
            return self._extract_function_content(node)
        else:
            logger.warning(f"Unsupported node type: {node_type}")
            return {"content": "", "context": []}

    def _extract_repository_content(
        self, node: NodeData
    ) -> dict[str, str | list[str]]:
        """Extract content for a repository node.

        Args:
            node: Repository node

        Returns:
            dict with repository overview
        """
        # Get repository metadata
        repo_name = node.name
        repo_path = node.path or self.repository_path

        # Get README content if available
        readme_content = self._get_readme_content(repo_path)

        # Get directory and file counts
        dir_query = """
        MATCH (r:Repository)-[:CONTAINS*]->(d:Directory)
        WHERE ID(r) = $repo_id
        RETURN COUNT(d) as dir_count
        """

        dir_result = self.connector.execute_query(
            dir_query, params={"repo_id": int(node.id)}
        )

        dir_count = dir_result[0]["dir_count"] if dir_result else 0

        file_query = """
        MATCH (r:Repository)-[:CONTAINS*]->(d:Directory)-[:CONTAINS]->(f:File)
        WHERE ID(r) = $repo_id
        RETURN COUNT(f) as file_count
        """

        file_result = self.connector.execute_query(
            file_query, params={"repo_id": int(node.id)}
        )

        file_count = file_result[0]["file_count"] if file_result else 0

        # Get list of top-level directories
        top_dirs_query = """
        MATCH (r:Repository)-[:CONTAINS]->(d:Directory)
        WHERE ID(r) = $repo_id
        RETURN d.name as name, d.path as path
        """

        top_dirs = self.connector.execute_query(
            top_dirs_query, params={"repo_id": int(node.id)}
        )

        top_level_dirs = [f"{d['name']} ({d['path']})" for d in top_dirs]

        # Prepare repository context information
        context = [
            f"Repository: {repo_name}",
            f"Path: {repo_path}",
            f"Contains {dir_count} directories and {file_count} files",
            f"Top-level directories: {', '.join(top_level_dirs)}",
        ]

        # Combine README and context
        if readme_content:
            context.append(f"README contents:\n{readme_content}")

        return {"content": f"Repository: {repo_name}", "context": context}

    def _extract_directory_content(
        self, node: NodeData
    ) -> dict[str, str | list[str]]:
        """Extract content for a directory node.

        Args:
            node: Directory node

        Returns:
            dict with directory contents
        """
        dir_name = node.name
        dir_path = node.path

        # Get files in the directory
        files_query = """
        MATCH (d:Directory)-[:CONTAINS]->(f:File)
        WHERE ID(d) = $dir_id
        RETURN f.name as name, f.path as path
        """

        files = self.connector.execute_query(
            files_query, params={"dir_id": int(node.id)}
        )

        file_list = [f"{f['name']} ({f['path']})" for f in files]

        # Get subdirectories
        subdirs_query = """
        MATCH (d:Directory)-[:CONTAINS]->(sub:Directory)
        WHERE ID(d) = $dir_id
        RETURN sub.name as name, sub.path as path
        """

        subdirs = self.connector.execute_query(
            subdirs_query, params={"dir_id": int(node.id)}
        )

        subdir_list = [f"{d['name']} ({d['path']})" for d in subdirs]

        # Prepare directory context
        context = [
            f"Directory: {dir_name}",
            f"Path: {dir_path}",
            f"Contains {len(files)} files and {len(subdirs)} subdirectories",
        ]

        if file_list:
            context.append(f"Files: {', '.join(file_list)}")

        if subdir_list:
            context.append(f"Subdirectories: {', '.join(subdir_list)}")

        return {"content": f"Directory: {dir_path}", "context": context}

    def _extract_file_content(self, node: NodeData) -> dict[str, str | list[str]]:
        """Extract content for a file node.

        Args:
            node: File node

        Returns:
            dict with file content
        """
        file_name = node.name
        file_path = node.path or ""
        file_extension = node.properties.get("extension", "")

        # Skip binary files
        binary_extensions = {
            "png",
            "jpg",
            "jpeg",
            "gif",
            "ico",
            "svg",
            "pdf",
            "doc",
            "docx",
            "xls",
            "xlsx",
            "ppt",
            "pptx",
            "zip",
            "tar",
            "gz",
            "tgz",
            "rar",
            "7z",
            "exe",
            "dll",
            "so",
            "dylib",
            "o",
            "obj",
            "pyc",
            "pyo",
            "pyd",
        }

        if file_extension in binary_extensions:
            return {
                "content": f"Binary file: {file_path}",
                "context": [f"Binary file of type: {file_extension}"],
            }

        # Get file content
        context = [
            f"File: {file_name}",
            f"Path: {file_path}",
            f"Type: {file_extension}",
        ]

        if self.repository_path and file_path:
            absolute_path = os.path.join(self.repository_path, file_path)

            if absolute_path in self.cache:
                content = self.cache[absolute_path]
            else:
                try:
                    with open(absolute_path, encoding="utf-8") as f:
                        content = f.read()
                    self.cache[absolute_path] = content
                except Exception as e:
                    logger.warning(f"Error reading file {absolute_path}: {e}")
                    content = f"Error reading file: {e}"
        else:
            # If repository path is not provided, get content from Neo4j
            content_query = """
            MATCH (f:File)
            WHERE ID(f) = $file_id
            RETURN f.content as content
            """

            content_results = self.connector.execute_query(
                content_query, params={"file_id": int(node.id)}
            )
            content_item = content_results[0] if content_results else {}

            content = content_item.get("content", "")

        # Add any additional context information
        # (we already initialized context above)

        # Try to get imports or includes if relevant
        if file_extension in {"py", "js", "ts", "java", "cpp", "c", "h", "hpp"}:
            imports_query = """
            MATCH (f:File)-[:IMPORTS]->(i:File)
            WHERE ID(f) = $file_id
            RETURN i.name as name, i.path as path
            """

            imports = self.connector.execute_query(
                imports_query, params={"file_id": int(node.id)}
            )

            if imports:
                import_list = [f"{i['name']} ({i['path']})" for i in imports]
                context.append(f"Imports: {', '.join(import_list)}")

        return {"content": content, "context": context}

    def _extract_class_content(
        self, node: NodeData
    ) -> dict[str, str | list[str]]:
        """Extract content for a class node.

        Args:
            node: Class node

        Returns:
            dict with class content
        """
        class_name = node.name
        qualified_name = node.properties.get("qualified_name", class_name)

        # Get the file containing this class
        file_query = """
        MATCH (f:File)-[:CONTAINS]->(c:Class)
        WHERE ID(c) = $class_id
        RETURN f.path as file_path, ID(f) as file_id
        """

        file_results = self.connector.execute_query(
            file_query, params={"class_id": int(node.id)}
        )
        file_result = file_results[0] if file_results and len(file_results) > 0 else None

        file_path = file_result.get("file_path") if file_result else None

        # Get class content from file
        class_content = ""
        if file_path and self.repository_path:
            absolute_path = os.path.join(self.repository_path, file_path)

            try:
                if absolute_path in self.cache:
                    file_content = self.cache[absolute_path]
                else:
                    with open(absolute_path, encoding="utf-8") as f:
                        file_content = f.read()
                    self.cache[absolute_path] = file_content

                # Extract class definition (simple approach - may need refinement for complex cases)
                lines = file_content.split("\n")
                class_start = -1
                class_end = -1
                brace_level = 0

                for i, line in enumerate(lines):
                    if f"class {class_name}" in line and class_start == -1:
                        class_start = i

                    if class_start != -1:
                        # Count braces for languages like Java, C++
                        brace_level += line.count("{") - line.count("}")

                        # For Python, look for lower indentation level
                        if "}" in line and brace_level == 0:
                            class_end = i
                            break

                        # For Python, empty line followed by no indentation might mean end of class
                        if (
                            i > class_start
                            and line.strip() == ""
                            and i + 1 < len(lines)
                            and not lines[i + 1].startswith(" ")
                        ):
                            class_end = i
                            break

                if class_start != -1:
                    if class_end == -1:
                        class_end = len(lines)

                    class_content = "\n".join(lines[class_start : class_end + 1])

            except Exception as e:
                logger.warning(
                    f"Error extracting class content for {class_name} from {absolute_path}: {e}"
                )

        # Get parent classes
        parent_query = """
        MATCH (c:Class)-[:INHERITS_FROM]->(p:Class)
        WHERE ID(c) = $class_id
        RETURN p.name as name
        """

        parents = self.connector.execute_query(
            parent_query, params={"class_id": int(node.id)}
        )

        parent_classes = [p["name"] for p in parents]

        # Get methods
        method_query = """
        MATCH (c:Class)-[:CONTAINS]->(m:Method)
        WHERE ID(c) = $class_id
        RETURN m.name as name
        """

        methods = self.connector.execute_query(
            method_query, params={"class_id": int(node.id)}
        )

        method_list = [m["name"] for m in methods]

        # Prepare class context
        context = [f"Class: {qualified_name}", f"Defined in file: {file_path}"]

        if parent_classes:
            context.append(f"Inherits from: {', '.join(parent_classes)}")

        if method_list:
            context.append(f"Methods: {', '.join(method_list)}")

        return {
            "content": class_content if class_content else f"Class: {qualified_name}",
            "context": context,
        }

    def _extract_function_content(
        self, node: NodeData
    ) -> dict[str, str | list[str]]:
        """Extract content for a function or method node.

        Args:
            node: Function or method node

        Returns:
            dict with function content
        """
        func_name = node.name
        qualified_name = node.properties.get("qualified_name", func_name)
        node_type = node.type

        # Get the container (file or class) of this function
        container_query = """
        MATCH (container)-[:CONTAINS]->(func)
        WHERE ID(func) = $func_id
        RETURN ID(container) as container_id, labels(container) as container_labels
        """

        container_results = self.connector.execute_query(
            container_query, params={"func_id": int(node.id)}
        )
        # Extract first result if results exist, otherwise None
        have_results = container_results and len(container_results) > 0
        container_result = container_results[0] if have_results else None

        container_labels = (
            container_result.get("container_labels", []) if container_result else []
        )

        # Get the file path
        file_path = None

        if "Class" in container_labels:
            # Function is a method in a class
            file_query = """
            MATCH (f:File)-[:CONTAINS]->(c:Class)-[:CONTAINS]->(m)
            WHERE ID(m) = $func_id
            RETURN f.path as file_path, ID(f) as file_id, c.name as class_name
            """

            file_results = self.connector.execute_query(
                file_query, params={"func_id": int(node.id)}
            )
            file_result = file_results[0] if file_results and len(file_results) > 0 else None

            if file_result:
                file_path = file_result.get("file_path")
                class_name = file_result.get("class_name", "")
                if file_path and class_name:
                    qualified_name = f"{class_name}.{func_name}"
        else:
            # Function is directly in a file
            file_query = """
            MATCH (f:File)-[:CONTAINS]->(func)
            WHERE ID(func) = $func_id
            RETURN f.path as file_path, ID(f) as file_id
            """

            file_results = self.connector.execute_query(
                file_query, params={"func_id": int(node.id)}
            )
            file_result = file_results[0] if file_results and len(file_results) > 0 else None

            if file_result:
                file_path = file_result.get("file_path")

        # Get function content from file
        func_content = ""
        if file_path and self.repository_path is not None:
            absolute_path = os.path.join(self.repository_path, file_path)

            try:
                if absolute_path in self.cache:
                    file_content = self.cache[absolute_path]
                else:
                    with open(absolute_path, encoding="utf-8") as f:
                        file_content = f.read()
                    self.cache[absolute_path] = file_content

                # Extract function/method definition (simple approach)
                lines = file_content.split("\n")
                func_start = -1
                func_end = -1
                brace_level = 0

                for i, line in enumerate(lines):
                    if (
                        f"def {func_name}" in line
                        or f"function {func_name}" in line
                        or f"{func_name} = function" in line
                        or f"{func_name}(" in line
                    ) and func_start == -1:
                        func_start = i

                    if func_start != -1:
                        # Count braces for languages like Java, C++
                        brace_level += line.count("{") - line.count("}")

                        # For Python, look for lower indentation level
                        if "}" in line and brace_level == 0:
                            func_end = i
                            break

                        # For Python, empty line followed by no indentation might end function
                        if (i > func_start and line.strip() == "" and
                            i + 1 < len(lines) and not lines[i + 1].startswith(" ")):
                            func_end = i
                            break

                if func_start != -1:
                    if func_end == -1:
                        func_end = len(lines)

                    func_content = "\n".join(lines[func_start : func_end + 1])

            except Exception as e:
                logger.warning(
                    f"Error extracting function content for {func_name} from {absolute_path}: {e}"
                )

        # Prepare function context
        context = [
            f"{'Method' if node_type == NodeType.METHOD else 'Function'}: {qualified_name}",
            f"Defined in file: {file_path}",
        ]

        return {
            "content": func_content if func_content else f"Function: {qualified_name}",
            "context": context,
        }

    def _get_readme_content(self, repo_path: str | None = None) -> str:
        """Get README content from the repository.

        Args:
            repo_path: Repository path

        Returns:
            README content if found, empty string otherwise
        """
        if not repo_path:
            return ""

        # Try common README filenames
        readme_filenames = ["README.md", "README.txt", "README", "readme.md"]

        for filename in readme_filenames:
            try:
                filepath = os.path.join(repo_path, filename)
                if os.path.exists(filepath):
                    with open(filepath, encoding="utf-8") as f:
                        return f.read()
            except Exception as e:
                logger.warning(f"Error reading README {filepath}: {e}")

        return ""
