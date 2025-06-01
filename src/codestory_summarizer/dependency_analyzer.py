from typing import Any

'Dependency analyzer for building and analyzing code dependency graphs.\n\nThis module provides functionality for building a directed acyclic graph (DAG)\nof code dependencies by querying the Neo4j database for AST and filesystem nodes.\n'
import logging

from codestory.graphdb.neo4j_connector import Neo4jConnector

from .models import DependencyGraph, NodeData, NodeType

logger = logging.getLogger(__name__)

class DependencyAnalyzer:
    """Builds and analyzes the DAG of code dependencies.

    This class queries the Neo4j database to build a dependency graph
    of code elements, identifying leaf nodes for initial processing and
    establishing the overall processing order.
    """

    def __init__(self: Any, connector: Neo4jConnector) -> None:
        """Initialize the dependency analyzer.

        Args:
            connector: Neo4j database connector
        """
        self.connector = connector
        self.graph = DependencyGraph()

    def build_dependency_graph(self: Any, repository_path: str) -> DependencyGraph:
        """Build a dependency graph for the repository.

        Args:
            repository_path: Path to the repository to analyze

        Returns:
            DependencyGraph: Graph of code dependencies
        """
        logger.info(f'Building dependency graph for repository: {repository_path}')
        self.graph = DependencyGraph()
        repo_node = self._get_repository_node(repository_path)
        if not repo_node:
            logger.error(f'Repository not found: {repository_path}')
            return self.graph
        self.graph.add_node(repo_node)
        self._load_filesystem_hierarchy(repo_node.id)
        self._load_ast_nodes()
        self._calculate_directory_dependencies()
        self._calculate_file_dependencies()
        self._calculate_class_dependencies()
        logger.info(f'Dependency graph built with {self.graph.total_count} nodes')
        logger.info(f'Found {len(self.graph.leaf_nodes)} leaf nodes and {len(self.graph.root_nodes)} root nodes')
        return self.graph

    def _get_repository_node(self: Any, repository_path: str) -> NodeData | None:
        """Get the repository node from Neo4j.

        Args:
            repository_path: Path to the repository

        Returns:
            NodeData | None: Repository node if found, None otherwise
        """
        query = '\n        MATCH (r:Repository)\n        WHERE r.path = $path OR r.name = $name\n        RETURN ID(r) as id, r.name as name, r.path as path\n        LIMIT 1\n        '
        repo_name = repository_path.strip('/').split('/')[-1]
        results = self.connector.execute_query(query, params={'path': repository_path, 'name': repo_name})
        if not results or len(results) == 0:
            return None
        result = results[0]
        return NodeData(id=str(result['id']), name=result['name'], type=NodeType.REPOSITORY, path=result['path'], properties={'name': result['name'], 'path': result['path']})

    def _load_filesystem_hierarchy(self: Any, repository_id: str) -> None:
        """Load the filesystem hierarchy from Neo4j.

        Args:
            repository_id: ID of the repository node
        """
        logger.info('Loading filesystem hierarchy')
        dir_query = '\n        MATCH (r:Repository)-[:CONTAINS*]->(d:Directory)\n        OPTIONAL MATCH (parent)-[:CONTAINS]->(d)\n        RETURN ID(d) as id, d.name as name, d.path as path, ID(parent) as parent_id\n        '
        dirs = self.connector.execute_query(dir_query)
        for dir_data in dirs:
            dir_node = NodeData(id=str(dir_data['id']), name=dir_data['name'], type=NodeType.DIRECTORY, path=dir_data['path'], properties={'name': dir_data['name'], 'path': dir_data['path']})
            if dir_data['parent_id'] is not None:
                parent_id = str(dir_data['parent_id'])
                dir_node.dependencies.add(parent_id)
                if parent_id in self.graph.nodes:
                    self.graph.nodes[parent_id].dependents.add(dir_node.id)
            self.graph.add_node(dir_node)
        file_query = '\n        MATCH (d:Directory)-[:CONTAINS]->(f:File)\n        RETURN ID(f) as id, f.name as name, f.path as path,\n               f.extension as extension, ID(d) as parent_id\n        '
        files = self.connector.execute_query(file_query)
        for file_data in files:
            file_node = NodeData(id=str(file_data['id']), name=file_data['name'], type=NodeType.FILE, path=file_data['path'], properties={'name': file_data['name'], 'path': file_data['path'], 'extension': file_data['extension']})
            if file_data['parent_id'] is not None:
                parent_id = str(file_data['parent_id'])
                file_node.dependencies.add(parent_id)
                if parent_id in self.graph.nodes:
                    self.graph.nodes[parent_id].dependents.add(file_node.id)
            self.graph.add_node(file_node)

    def _load_ast_nodes(self: Any) -> None:
        """Load AST nodes from Neo4j.

        This includes classes, functions, and methods.
        """
        logger.info('Loading AST nodes')
        class_query = '\n        MATCH (f:File)-[:CONTAINS]->(c:Class)\n        RETURN ID(c) as id, c.name as name, c.qualified_name as qualified_name, ID(f) as file_id\n        '
        classes = self.connector.execute_query(class_query)
        for class_data in classes:
            class_node = NodeData(id=str(class_data['id']), name=class_data['name'], type=NodeType.CLASS, properties={'name': class_data['name'], 'qualified_name': class_data['qualified_name']})
            if class_data['file_id'] is not None:
                file_id = str(class_data['file_id'])
                class_node.dependencies.add(file_id)
                if file_id in self.graph.nodes:
                    self.graph.nodes[file_id].dependents.add(class_node.id)
            self.graph.add_node(class_node)
        func_query = '\n        MATCH (parent)-[:CONTAINS]->(f:Function)\n        RETURN ID(f) as id, f.name as name, f.qualified_name as qualified_name,\n               labels(parent) as parent_labels, ID(parent) as parent_id\n        '
        funcs = self.connector.execute_query(func_query)
        for func_data in funcs:
            parent_labels = func_data['parent_labels']
            node_type = NodeType.METHOD if 'Class' in parent_labels else NodeType.FUNCTION
            func_node = NodeData(id=str(func_data['id']), name=func_data['name'], type=node_type, properties={'name': func_data['name'], 'qualified_name': func_data['qualified_name']})
            if func_data['parent_id'] is not None:
                parent_id = str(func_data['parent_id'])
                func_node.dependencies.add(parent_id)
                if parent_id in self.graph.nodes:
                    self.graph.nodes[parent_id].dependents.add(func_node.id)
            self.graph.add_node(func_node)

    def _calculate_directory_dependencies(self: Any) -> None:
        """Calculate directory dependencies.

        A directory depends on its parent directory.
        """
        pass

    def _calculate_file_dependencies(self: Any) -> None:
        """Calculate file dependencies.

        A file depends on:
        1. Its parent directory
        2. Files it imports or includes
        """
        logger.info('Calculating file dependencies')
        import_query = '\n        MATCH (f1:File)-[:IMPORTS]->(f2:File)\n        RETURN ID(f1) as file_id, ID(f2) as import_id\n        '
        imports = self.connector.execute_query(import_query)
        for import_data in imports:
            file_id = str(import_data['file_id'])
            import_id = str(import_data['import_id'])
            if file_id in self.graph.nodes and import_id in self.graph.nodes:
                self.graph.nodes[file_id].dependencies.add(import_id)
                self.graph.nodes[import_id].dependents.add(file_id)

    def _calculate_class_dependencies(self: Any) -> None:
        """Calculate class dependencies.

        A class depends on:
        1. Its parent file
        2. Classes it inherits from
        """
        logger.info('Calculating class dependencies')
        inherit_query = '\n        MATCH (c1:Class)-[:INHERITS_FROM]->(c2:Class)\n        RETURN ID(c1) as class_id, ID(c2) as parent_id\n        '
        inherits = self.connector.execute_query(inherit_query)
        for inherit_data in inherits:
            class_id = str(inherit_data['class_id'])
            parent_id = str(inherit_data['parent_id'])
            if class_id in self.graph.nodes and parent_id in self.graph.nodes:
                self.graph.nodes[class_id].dependencies.add(parent_id)
                self.graph.nodes[parent_id].dependents.add(class_id)