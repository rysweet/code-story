"""Dependency analyzer for building and analyzing code dependency graphs.

This module provides functionality for building a directed acyclic graph (DAG)
of code dependencies by querying the Neo4j database for AST and filesystem nodes.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from src.codestory.graphdb.neo4j_connector import Neo4jConnector
from .models import DependencyGraph, NodeData, NodeType, ProcessingStatus

# Set up logging
logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Builds and analyzes the DAG of code dependencies.
    
    This class queries the Neo4j database to build a dependency graph
    of code elements, identifying leaf nodes for initial processing and
    establishing the overall processing order.
    """
    
    def __init__(self, connector: Neo4jConnector):
        """Initialize the dependency analyzer.
        
        Args:
            connector: Neo4j database connector
        """
        self.connector = connector
        self.graph = DependencyGraph()
    
    def build_dependency_graph(self, repository_path: str) -> DependencyGraph:
        """Build a dependency graph for the repository.
        
        Args:
            repository_path: Path to the repository to analyze
            
        Returns:
            DependencyGraph: Graph of code dependencies
        """
        logger.info(f"Building dependency graph for repository: {repository_path}")
        
        # Reset the graph
        self.graph = DependencyGraph()
        
        # Find the repository node
        repo_node = self._get_repository_node(repository_path)
        if not repo_node:
            logger.error(f"Repository not found: {repository_path}")
            return self.graph
        
        # Add the repository node to the graph
        self.graph.add_node(repo_node)
        
        # Load filesystem hierarchy (directories and files)
        self._load_filesystem_hierarchy(repo_node.id)
        
        # Load AST nodes (classes, functions, etc.)
        self._load_ast_nodes()
        
        # Calculate additional relationships
        self._calculate_directory_dependencies()
        self._calculate_file_dependencies()
        self._calculate_class_dependencies()
        
        logger.info(f"Dependency graph built with {self.graph.total_count} nodes")
        logger.info(f"Found {len(self.graph.leaf_nodes)} leaf nodes and {len(self.graph.root_nodes)} root nodes")
        
        return self.graph
    
    def _get_repository_node(self, repository_path: str) -> Optional[NodeData]:
        """Get the repository node from Neo4j.
        
        Args:
            repository_path: Path to the repository
            
        Returns:
            Optional[NodeData]: Repository node if found, None otherwise
        """
        # Query for the repository node
        query = """
        MATCH (r:Repository)
        WHERE r.path = $path OR r.name = $name
        RETURN ID(r) as id, r.name as name, r.path as path
        LIMIT 1
        """
        
        # Extract repository name from path (last part)
        repo_name = repository_path.strip("/").split("/")[-1]
        
        result = self.connector.run_query(
            query,
            parameters={
                "path": repository_path,
                "name": repo_name
            },
            fetch_one=True
        )
        
        if not result:
            return None
        
        return NodeData(
            id=str(result["id"]),
            name=result["name"],
            type=NodeType.REPOSITORY,
            path=result["path"],
            properties={
                "name": result["name"],
                "path": result["path"]
            }
        )
    
    def _load_filesystem_hierarchy(self, repository_id: str) -> None:
        """Load the filesystem hierarchy from Neo4j.
        
        Args:
            repository_id: ID of the repository node
        """
        logger.info("Loading filesystem hierarchy")
        
        # Get directories and their parent relationships
        dir_query = """
        MATCH (r:Repository)-[:CONTAINS*]->(d:Directory)
        OPTIONAL MATCH (parent)-[:CONTAINS]->(d)
        RETURN ID(d) as id, d.name as name, d.path as path, ID(parent) as parent_id
        """
        
        dirs = self.connector.run_query(dir_query, fetch_all=True)
        
        # Process directories
        for dir_data in dirs:
            dir_node = NodeData(
                id=str(dir_data["id"]),
                name=dir_data["name"],
                type=NodeType.DIRECTORY,
                path=dir_data["path"],
                properties={
                    "name": dir_data["name"],
                    "path": dir_data["path"]
                }
            )
            
            # Set up dependency relationship with parent
            if dir_data["parent_id"] is not None:
                parent_id = str(dir_data["parent_id"])
                dir_node.dependencies.add(parent_id)
                
                # Add the parent if not already added
                if parent_id in self.graph.nodes:
                    self.graph.nodes[parent_id].dependents.add(dir_node.id)
            
            self.graph.add_node(dir_node)
        
        # Get files and their parent directories
        file_query = """
        MATCH (d:Directory)-[:CONTAINS]->(f:File)
        RETURN ID(f) as id, f.name as name, f.path as path, f.extension as extension, ID(d) as parent_id
        """
        
        files = self.connector.run_query(file_query, fetch_all=True)
        
        # Process files
        for file_data in files:
            file_node = NodeData(
                id=str(file_data["id"]),
                name=file_data["name"],
                type=NodeType.FILE,
                path=file_data["path"],
                properties={
                    "name": file_data["name"],
                    "path": file_data["path"],
                    "extension": file_data["extension"]
                }
            )
            
            # Set up dependency relationship with parent directory
            if file_data["parent_id"] is not None:
                parent_id = str(file_data["parent_id"])
                file_node.dependencies.add(parent_id)
                
                # Add the parent if not already added
                if parent_id in self.graph.nodes:
                    self.graph.nodes[parent_id].dependents.add(file_node.id)
            
            self.graph.add_node(file_node)
    
    def _load_ast_nodes(self) -> None:
        """Load AST nodes from Neo4j.
        
        This includes classes, functions, and methods.
        """
        logger.info("Loading AST nodes")
        
        # Get class nodes
        class_query = """
        MATCH (f:File)-[:CONTAINS]->(c:Class)
        RETURN ID(c) as id, c.name as name, c.qualified_name as qualified_name, ID(f) as file_id
        """
        
        classes = self.connector.run_query(class_query, fetch_all=True)
        
        # Process classes
        for class_data in classes:
            class_node = NodeData(
                id=str(class_data["id"]),
                name=class_data["name"],
                type=NodeType.CLASS,
                properties={
                    "name": class_data["name"],
                    "qualified_name": class_data["qualified_name"]
                }
            )
            
            # Set up dependency relationship with file
            if class_data["file_id"] is not None:
                file_id = str(class_data["file_id"])
                class_node.dependencies.add(file_id)
                
                # Update file node
                if file_id in self.graph.nodes:
                    self.graph.nodes[file_id].dependents.add(class_node.id)
            
            self.graph.add_node(class_node)
        
        # Get function and method nodes
        func_query = """
        MATCH (parent)-[:CONTAINS]->(f:Function)
        RETURN ID(f) as id, f.name as name, f.qualified_name as qualified_name, 
               labels(parent) as parent_labels, ID(parent) as parent_id
        """
        
        funcs = self.connector.run_query(func_query, fetch_all=True)
        
        # Process functions and methods
        for func_data in funcs:
            # Determine if this is a method (parent is a class) or a function
            parent_labels = func_data["parent_labels"]
            node_type = NodeType.METHOD if "Class" in parent_labels else NodeType.FUNCTION
            
            func_node = NodeData(
                id=str(func_data["id"]),
                name=func_data["name"],
                type=node_type,
                properties={
                    "name": func_data["name"],
                    "qualified_name": func_data["qualified_name"]
                }
            )
            
            # Set up dependency relationship with parent
            if func_data["parent_id"] is not None:
                parent_id = str(func_data["parent_id"])
                func_node.dependencies.add(parent_id)
                
                # Update parent node
                if parent_id in self.graph.nodes:
                    self.graph.nodes[parent_id].dependents.add(func_node.id)
            
            self.graph.add_node(func_node)
    
    def _calculate_directory_dependencies(self) -> None:
        """Calculate directory dependencies.
        
        A directory depends on its parent directory.
        """
        # This is already handled in _load_filesystem_hierarchy()
        pass
    
    def _calculate_file_dependencies(self) -> None:
        """Calculate file dependencies.
        
        A file depends on:
        1. Its parent directory
        2. Files it imports or includes
        """
        logger.info("Calculating file dependencies")
        
        # Get file import relationships
        import_query = """
        MATCH (f1:File)-[:IMPORTS]->(f2:File)
        RETURN ID(f1) as file_id, ID(f2) as import_id
        """
        
        imports = self.connector.run_query(import_query, fetch_all=True)
        
        # Process imports
        for import_data in imports:
            file_id = str(import_data["file_id"])
            import_id = str(import_data["import_id"])
            
            if file_id in self.graph.nodes and import_id in self.graph.nodes:
                # Add import as a dependency
                self.graph.nodes[file_id].dependencies.add(import_id)
                self.graph.nodes[import_id].dependents.add(file_id)
    
    def _calculate_class_dependencies(self) -> None:
        """Calculate class dependencies.
        
        A class depends on:
        1. Its parent file
        2. Classes it inherits from
        """
        logger.info("Calculating class dependencies")
        
        # Get class inheritance relationships
        inherit_query = """
        MATCH (c1:Class)-[:INHERITS_FROM]->(c2:Class)
        RETURN ID(c1) as class_id, ID(c2) as parent_id
        """
        
        inherits = self.connector.run_query(inherit_query, fetch_all=True)
        
        # Process inheritance
        for inherit_data in inherits:
            class_id = str(inherit_data["class_id"])
            parent_id = str(inherit_data["parent_id"])
            
            if class_id in self.graph.nodes and parent_id in self.graph.nodes:
                # Add parent class as a dependency
                self.graph.nodes[class_id].dependencies.add(parent_id)
                self.graph.nodes[parent_id].dependents.add(class_id)