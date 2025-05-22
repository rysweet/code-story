"""Base test class for pipeline integration tests.

This module provides a base test class with common functionality for
integration tests related to the ingestion pipeline.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest


class BasePipelineTest:
    """Base class for pipeline integration tests.
    
    This class provides common setup and teardown functionality for
    integration tests that work with the ingestion pipeline.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_env(self, neo4j_connector, redis_client, celery_app):
        """Set up the test environment.
        
        This fixture sets up the test environment with Neo4j, Redis, and Celery
        configured properly. It also creates a temporary repository for testing.
        
        The fixture is automatically used by all test methods in this class.
        """
        # Store fixtures for use in tests
        self.neo4j_connector = neo4j_connector
        self.redis_client = redis_client
        self.celery_app = celery_app
        
        # Import step tasks to ensure they're registered
        try:
            from codestory_blarify.step import run_blarify
            from codestory_docgrapher.step import run_docgrapher
            from codestory_filesystem.step import process_filesystem
            from codestory_summarizer.step import run_summarizer
            
            # Verify that key tasks are registered
            task_names = [
                "codestory_filesystem.step.process_filesystem",
                "codestory_blarify.step.run_blarify",
                "codestory_summarizer.step.run_summarizer",
                "codestory_docgrapher.step.run_docgrapher"
            ]
            
            for task_name in task_names:
                if task_name not in self.celery_app.tasks:
                    import logging
                    logging.warning(f"Task {task_name} not registered with Celery app")
                    
                    # Register module manually if task not found
                    module_name = task_name.rsplit(".", 1)[0]
                    print(f"Attempting to register module: {module_name}")
                    self.celery_app.autodiscover_tasks([module_name], force=True)
        except ImportError as e:
            import logging
            logging.warning(f"Could not import some pipeline tasks: {e}")
        
        # Create temporary repository for testing
        self.repo_dir = self.create_test_repository()
        
        # Run the test
        yield
        
        # Clean up temporary repository
        if hasattr(self, 'repo_dir') and self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
    
    def create_test_repository(self):
        """Create a test repository with some files.
        
        Returns:
            str: Path to the created repository
        """
        repo_dir = tempfile.mkdtemp()
        
        # Create sample Python files
        os.makedirs(os.path.join(repo_dir, "src/package"), exist_ok=True)
        
        # Create __init__.py files
        Path(os.path.join(repo_dir, "src/package/__init__.py")).touch()
        
        # Create a module file
        with open(os.path.join(repo_dir, "src/package/module.py"), "w") as f:
            f.write("""
def hello_world():
    \"\"\"Print hello world.
    
    Returns:
        str: A greeting
    \"\"\"
    return "Hello, world!"

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def add(self, a, b):
        \"\"\"Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            The sum of a and b
        \"\"\"
        return a + b
""")
        
        # Create a README
        with open(os.path.join(repo_dir, "README.md"), "w") as f:
            f.write("""# Test Repository
            
This is a test repository for pipeline integration tests.

## Features

- Module with functions and classes
- Documentation in docstrings
- Simple README
""")
        
        return repo_dir

    def wait_for_node_in_db(self, query, params=None, timeout=15):
        """Wait for a node to appear in the database.
        
        Args:
            query: Neo4j query to find the node
            params: Query parameters
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if node was found, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.neo4j_connector.execute_query(query, params=params)
            if result and result[0].get("count", 0) > 0:
                return True
            time.sleep(0.5)  # Small delay between checks
        return False

    def create_filesystem_nodes(self):
        """Create filesystem nodes directly in Neo4j.
        
        This is useful for tests that need a filesystem structure
        but don't want to run the filesystem step.
        """
        # Create repository node
        repo_name = os.path.basename(self.repo_dir)
        repo_query = """
        CREATE (r:Repository {name: $name, path: $path})
        RETURN r
        """
        self.neo4j_connector.execute_query(
            repo_query, 
            params={"name": repo_name, "path": self.repo_dir},
            write=True
        )
        
        # Create the README.md file node linked to repository
        file_query = """
        MATCH (r:Repository {path: $repo_path})
        CREATE (f:File {name: $name, path: $path})
        CREATE (r)-[:CONTAINS]->(f)
        RETURN f
        """
        self.neo4j_connector.execute_query(
            file_query,
            params={
                "repo_path": self.repo_dir,
                "name": "README.md",
                "path": "README.md",
            },
            write=True
        )
        
        # Create directory nodes
        dir_query = """
        MATCH (r:Repository {path: $repo_path})
        CREATE (d:Directory {name: $name, path: $path})
        CREATE (r)-[:CONTAINS]->(d)
        RETURN d
        """
        self.neo4j_connector.execute_query(
            dir_query,
            params={
                "repo_path": self.repo_dir,
                "name": "src",
                "path": "src",
            },
            write=True
        )
        
        # Create subdirectory linked to parent directory
        subdir_query = """
        MATCH (parent:Directory {path: $parent_path})
        CREATE (d:Directory {name: $name, path: $path})
        CREATE (parent)-[:CONTAINS]->(d)
        RETURN d
        """
        self.neo4j_connector.execute_query(
            subdir_query,
            params={
                "parent_path": "src",
                "name": "package",
                "path": "src/package",
            },
            write=True
        )
        
        # Create file linked to subdirectory
        nested_file_query = """
        MATCH (d:Directory {path: $dir_path})
        CREATE (f:File {name: $name, path: $path})
        CREATE (d)-[:CONTAINS]->(f)
        RETURN f
        """
        self.neo4j_connector.execute_query(
            nested_file_query,
            params={
                "dir_path": "src/package",
                "name": "module.py",
                "path": "src/package/module.py",
            },
            write=True
        )
        
        # Also create the __init__.py file
        self.neo4j_connector.execute_query(
            nested_file_query,
            params={
                "dir_path": "src/package",
                "name": "__init__.py",
                "path": "src/package/__init__.py",
            },
            write=True
        )