"""Path matcher for resolving references to filesystem paths.

This module provides functionality for matching references in documentation
to actual filesystem paths in the repository.
"""

import logging
import os
import re
from typing import Dict, List, Optional, Set, Tuple

from codestory.graphdb.neo4j_connector import Neo4jConnector

logger = logging.getLogger(__name__)


class PathMatcher:
    """Matches documentation references to filesystem paths.

    This class helps resolve references in documentation to actual
    filesystem paths or entities in the repository.
    """

    def __init__(self, connector: Neo4jConnector, repository_path: str):
        """Initialize the path matcher.

        Args:
            connector: Neo4j database connector
            repository_path: Path to the repository
        """
        self.connector = connector
        self.repository_path = repository_path
        self.path_cache = {}

        # Load repository structure for faster matching
        self._load_repository_structure()

    def _load_repository_structure(self) -> None:
        """Load repository structure from Neo4j."""
        # Get all file paths
        query = """
        MATCH (f:File)
        RETURN f.path as path
        """

        files = self.connector.run_query(query, fetch_all=True)
        self.file_paths = {record["path"] for record in files}

        # Get all directory paths
        query = """
        MATCH (d:Directory)
        RETURN d.path as path
        """

        dirs = self.connector.run_query(query, fetch_all=True)
        self.dir_paths = {record["path"] for record in dirs}

        # Get all class names
        query = """
        MATCH (c:Class)
        RETURN c.name as name, c.qualified_name as qualified_name
        """

        classes = self.connector.run_query(query, fetch_all=True)
        self.class_names = {record["name"] for record in classes}
        self.qualified_class_names = {
            record["qualified_name"] for record in classes if record["qualified_name"]
        }

        # Get all function names
        query = """
        MATCH (f:Function)
        RETURN f.name as name, f.qualified_name as qualified_name
        """

        funcs = self.connector.run_query(query, fetch_all=True)
        self.func_names = {record["name"] for record in funcs}
        self.qualified_func_names = {
            record["qualified_name"] for record in funcs if record["qualified_name"]
        }

    def match_path(self, path_reference: str) -> Optional[str]:
        """Match a path reference to an actual path.

        Args:
            path_reference: Path reference from documentation

        Returns:
            Actual path if found, None otherwise
        """
        # Check cache first
        if path_reference in self.path_cache:
            return self.path_cache[path_reference]

        # Try exact match first
        if path_reference in self.file_paths:
            self.path_cache[path_reference] = path_reference
            return path_reference

        if path_reference in self.dir_paths:
            self.path_cache[path_reference] = path_reference
            return path_reference

        # Try to find file by basename
        basename = os.path.basename(path_reference)
        matching_paths = [p for p in self.file_paths if p.endswith(f"/{basename}")]

        if len(matching_paths) == 1:
            # Unambiguous match
            self.path_cache[path_reference] = matching_paths[0]
            return matching_paths[0]
        elif len(matching_paths) > 1:
            # Multiple matches, try to find the best one
            # Check if any match contains directory components from the reference
            dir_components = os.path.dirname(path_reference).split("/")
            dir_components = [c for c in dir_components if c]

            if dir_components:
                # Filter matches by directory components
                filtered_paths = []
                for p in matching_paths:
                    p_dir = os.path.dirname(p)
                    match = True
                    for comp in dir_components:
                        if comp not in p_dir:
                            match = False
                            break
                    if match:
                        filtered_paths.append(p)

                if len(filtered_paths) == 1:
                    self.path_cache[path_reference] = filtered_paths[0]
                    return filtered_paths[0]
                elif len(filtered_paths) > 1:
                    # Still ambiguous, return the shortest path
                    shortest = min(filtered_paths, key=len)
                    self.path_cache[path_reference] = shortest
                    return shortest

            # No directory components or still ambiguous, return the shortest path
            shortest = min(matching_paths, key=len)
            self.path_cache[path_reference] = shortest
            return shortest

        # Try to match by extension
        if "." in basename:
            ext = basename.split(".")[-1]
            matching_paths = [p for p in self.file_paths if p.endswith(f".{ext}")]

            if matching_paths:
                # Return any one file with matching extension
                self.path_cache[path_reference] = matching_paths[0]
                return matching_paths[0]

        # No match found
        self.path_cache[path_reference] = None
        return None

    def match_class(self, class_reference: str) -> Optional[str]:
        """Match a class reference to an actual class.

        Args:
            class_reference: Class reference from documentation

        Returns:
            Neo4j ID of the class if found, None otherwise
        """
        # Check if the class exists by name
        if class_reference in self.class_names:
            query = """
            MATCH (c:Class)
            WHERE c.name = $name
            RETURN ID(c) as id
            """

            result = self.connector.run_query(
                query, parameters={"name": class_reference}, fetch_one=True
            )

            if result:
                return str(result["id"])

        # Check if the class exists by qualified name
        if class_reference in self.qualified_class_names:
            query = """
            MATCH (c:Class)
            WHERE c.qualified_name = $name
            RETURN ID(c) as id
            """

            result = self.connector.run_query(
                query, parameters={"name": class_reference}, fetch_one=True
            )

            if result:
                return str(result["id"])

        # Try partial match on qualified name
        query = """
        MATCH (c:Class)
        WHERE c.qualified_name ENDS WITH $name
        RETURN ID(c) as id
        """

        result = self.connector.run_query(
            query, parameters={"name": class_reference}, fetch_one=True
        )

        if result:
            return str(result["id"])

        return None

    def match_function(self, function_reference: str) -> Optional[str]:
        """Match a function reference to an actual function.

        Args:
            function_reference: Function reference from documentation

        Returns:
            Neo4j ID of the function if found, None otherwise
        """
        # Remove parentheses if present
        function_reference = function_reference.rstrip("()")

        # Check if the function exists by name
        if function_reference in self.func_names:
            query = """
            MATCH (f:Function)
            WHERE f.name = $name
            RETURN ID(f) as id
            UNION
            MATCH (m:Method)
            WHERE m.name = $name
            RETURN ID(m) as id
            """

            result = self.connector.run_query(
                query, parameters={"name": function_reference}, fetch_one=True
            )

            if result:
                return str(result["id"])

        # Check if the function exists by qualified name
        if function_reference in self.qualified_func_names:
            query = """
            MATCH (f:Function)
            WHERE f.qualified_name = $name
            RETURN ID(f) as id
            UNION
            MATCH (m:Method)
            WHERE m.qualified_name = $name
            RETURN ID(m) as id
            """

            result = self.connector.run_query(
                query, parameters={"name": function_reference}, fetch_one=True
            )

            if result:
                return str(result["id"])

        # Try partial match on qualified name
        query = """
        MATCH (f:Function)
        WHERE f.qualified_name ENDS WITH $name
        RETURN ID(f) as id
        UNION
        MATCH (m:Method)
        WHERE m.qualified_name ENDS WITH $name
        RETURN ID(m) as id
        """

        result = self.connector.run_query(
            query, parameters={"name": function_reference}, fetch_one=True
        )

        if result:
            return str(result["id"])

        return None
