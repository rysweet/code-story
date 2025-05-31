from typing import Any, Dict, Set, Optional

'Path matcher for resolving references to filesystem paths.\n\nThis module provides functionality for matching references in documentation\nto actual filesystem paths in the repository.\n'
import logging
import os
from codestory.graphdb.neo4j_connector import Neo4jConnector

logger = logging.getLogger(__name__)

class PathMatcher:
    """Matches documentation references to filesystem paths.

    This class helps resolve references in documentation to actual
    filesystem paths or entities in the repository.
    """

    connector: Neo4jConnector
    repository_path: str
    path_cache: Dict[str, Optional[str]]
    file_paths: Set[str]
    dir_paths: Set[str]
    class_names: Set[str]
    qualified_class_names: Set[str]
    func_names: Set[str]
    qualified_func_names: Set[str]

    def __init__(self, connector: Neo4jConnector, repository_path: str) -> None:
        """Initialize the path matcher.

        Args:
            connector: Neo4j database connector
            repository_path: Path to the repository
        """
        self.connector = connector
        self.repository_path = repository_path
        self.path_cache: Dict[str, Optional[str]] = {}
        self._load_repository_structure()

    def _load_repository_structure(self) -> None:
        """Load repository structure from Neo4j."""
        query = '\n        MATCH (f:File)\n        RETURN f.path as path\n        '
        files = self.connector.run_query(query, fetch_all=True)  # type: ignore[attr-defined]
        self.file_paths = {record['path'] for record in files}
        query = '\n        MATCH (d:Directory)\n        RETURN d.path as path\n        '
        dirs = self.connector.run_query(query, fetch_all=True)  # type: ignore[attr-defined]
        self.dir_paths = {record['path'] for record in dirs}
        query = '\n        MATCH (c:Class)\n        RETURN c.name as name, c.qualified_name as qualified_name\n        '
        classes = self.connector.run_query(query, fetch_all=True)  # type: ignore[attr-defined]
        self.class_names = {record['name'] for record in classes}
        self.qualified_class_names = {record['qualified_name'] for record in classes if record['qualified_name']}
        query = '\n        MATCH (f:Function)\n        RETURN f.name as name, f.qualified_name as qualified_name\n        '
        funcs = self.connector.run_query(query, fetch_all=True)  # type: ignore[attr-defined]
        self.func_names = {record['name'] for record in funcs}
        self.qualified_func_names = {record['qualified_name'] for record in funcs if record['qualified_name']}

    def match_path(self, path_reference: str) -> Optional[str]:
        """Match a path reference to an actual path.

        Args:
            path_reference: Path reference from documentation

        Returns:
            Actual path if found, None otherwise
        """
        if path_reference in self.path_cache:
            return self.path_cache[path_reference]
        if path_reference in self.file_paths:
            self.path_cache[path_reference] = path_reference
            return path_reference
        if path_reference in self.dir_paths:
            self.path_cache[path_reference] = path_reference
            return path_reference
        basename = os.path.basename(path_reference)
        matching_paths = [p for p in self.file_paths if p.endswith(f'/{basename}')]
        if len(matching_paths) == 1:
            self.path_cache[path_reference] = matching_paths[0]
            return matching_paths[0]
        elif len(matching_paths) > 1:
            dir_components = os.path.dirname(path_reference).split('/')
            dir_components = [c for c in dir_components if c]
            if dir_components:
                filtered_paths: list[str] = []
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
                    shortest = min(filtered_paths, key=len)
                    self.path_cache[path_reference] = shortest
                    return shortest
            shortest = min(matching_paths, key=len)
            self.path_cache[path_reference] = shortest
            return shortest
        if '.' in basename:
            ext = basename.split('.')[-1]
            matching_paths = [p for p in self.file_paths if p.endswith(f'.{ext}')]
            if matching_paths:
                self.path_cache[path_reference] = matching_paths[0]
                return matching_paths[0]
        self.path_cache[path_reference] = None
        return None

    def match_class(self, class_reference: str) -> Optional[str]:
        """Match a class reference to an actual class.

        Args:
            class_reference: Class reference from documentation

        Returns:
            Neo4j ID of the class if found, None otherwise
        """
        if class_reference in self.class_names:
            query = '\n            MATCH (c:Class)\n            WHERE c.name = $name\n            RETURN ID(c) as id\n            '
            result = self.connector.run_query(query, parameters={'name': class_reference}, fetch_one=True)  # type: ignore[attr-defined]
            if result:
                return str(result['id'])
        if class_reference in self.qualified_class_names:
            query = '\n            MATCH (c:Class)\n            WHERE c.qualified_name = $name\n            RETURN ID(c) as id\n            '
            result = self.connector.run_query(query, parameters={'name': class_reference}, fetch_one=True)  # type: ignore[attr-defined]
            if result:
                return str(result['id'])
        query = '\n        MATCH (c:Class)\n        WHERE c.qualified_name ENDS WITH $name\n        RETURN ID(c) as id\n        '
        result = self.connector.run_query(query, parameters={'name': class_reference}, fetch_one=True)  # type: ignore[attr-defined]
        if result:
            return str(result['id'])
        return None

    def match_function(self, function_reference: str) -> Optional[str]:
        """Match a function reference to an actual function.

        Args:
            function_reference: Function reference from documentation

        Returns:
            Neo4j ID of the function if found, None otherwise
        """
        function_reference = function_reference.rstrip('()')
        if function_reference in self.func_names:
            query = '\n            MATCH (f:Function)\n            WHERE f.name = $name\n            RETURN ID(f) as id\n            UNION\n            MATCH (m:Method)\n            WHERE m.name = $name\n            RETURN ID(m) as id\n            '
            result = self.connector.run_query(query, parameters={'name': function_reference}, fetch_one=True)  # type: ignore[attr-defined]
            if result:
                return str(result['id'])
        if function_reference in self.qualified_func_names:
            query = '\n            MATCH (f:Function)\n            WHERE f.qualified_name = $name\n            RETURN ID(f) as id\n            UNION\n            MATCH (m:Method)\n            WHERE m.qualified_name = $name\n            RETURN ID(m) as id\n            '
            result = self.connector.run_query(query, parameters={'name': function_reference}, fetch_one=True)  # type: ignore[attr-defined]
            if result:
                return str(result['id'])
        query = '\n        MATCH (f:Function)\n        WHERE f.qualified_name ENDS WITH $name\n        RETURN ID(f) as id\n        UNION\n        MATCH (m:Method)\n        WHERE m.qualified_name ENDS WITH $name\n        RETURN ID(m) as id\n        '
        result = self.connector.run_query(query, parameters={'name': function_reference}, fetch_one=True)  # type: ignore[attr-defined]
        if result:
            return str(result['id'])
        return None