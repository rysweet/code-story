from typing import Any
'Base test class for pipeline integration tests.\n\nThis module provides a base test class with common functionality for\nintegration tests related to the ingestion pipeline.\n'
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
    def setup_test_env(self: Any, neo4j_connector: Any, redis_client: Any, celery_app: Any) -> None:
        """Set up the test environment.

        This fixture sets up the test environment with Neo4j, Redis, and Celery
        configured properly. It also creates a temporary repository for testing.

        The fixture is automatically used by all test methods in this class.
        """
        self.neo4j_connector = neo4j_connector
        self.redis_client = redis_client
        self.celery_app = celery_app
        try:
            from codestory_blarify.step import run_blarify
            from codestory_docgrapher.step import run_docgrapher
            from codestory_filesystem.step import process_filesystem
            from codestory_summarizer.step import run_summarizer
            task_names = ['codestory_filesystem.step.process_filesystem', 'codestory_blarify.step.run_blarify', 'codestory_summarizer.step.run_summarizer', 'codestory_docgrapher.step.run_docgrapher']
            for task_name in task_names:
                if task_name not in self.celery_app.tasks:
                    import logging
                    logging.warning(f'Task {task_name} not registered with Celery app')
                    module_name = task_name.rsplit('.', 1)[0]
                    print(f'Attempting to register module: {module_name}')
                    self.celery_app.autodiscover_tasks([module_name], force=True)
        except ImportError as e:
            import logging
            logging.warning(f'Could not import some pipeline tasks: {e}')
        self.repo_dir = self.create_test_repository()
        yield
        if hasattr(self, 'repo_dir') and self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)

    def create_test_repository(self: Any) -> Any:
        """Create a test repository with some files.

        Returns:
            str: Path to the created repository
        """
        repo_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(repo_dir, 'src/package'), exist_ok=True)
        Path(os.path.join(repo_dir, 'src/package/__init__.py')).touch()
        with open(os.path.join(repo_dir, 'src/package/module.py'), 'w') as f:
            f.write('\ndef hello_world():\n    """Print hello world.\n    \n    Returns:\n        str: A greeting\n    """\n    return "Hello, world!"\n\nclass Calculator:\n    """A simple calculator class."""\n    \n    def add(self, a, b):\n        """Add two numbers.\n        \n        Args:\n            a: First number\n            b: Second number\n            \n        Returns:\n            The sum of a and b\n        """\n        return a + b\n')
        with open(os.path.join(repo_dir, 'README.md'), 'w') as f:
            f.write('# Test Repository\n            \nThis is a test repository for pipeline integration tests.\n\n## Features\n\n- Module with functions and classes\n- Documentation in docstrings\n- Simple README\n')
        return repo_dir

    def wait_for_node_in_db(self: Any, query: Any, params: Any=None, timeout: Any=15) -> Any:
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
            if result and result[0].get('count', 0) > 0:
                return True
            time.sleep(0.5)
        return False

    def create_filesystem_nodes(self: Any) -> None:
        """Create filesystem nodes directly in Neo4j.

        This is useful for tests that need a filesystem structure
        but don't want to run the filesystem step.
        """
        repo_name = os.path.basename(self.repo_dir)
        repo_query = '\n        CREATE (r:Repository {name: $name, path: $path})\n        RETURN r\n        '
        self.neo4j_connector.execute_query(repo_query, params={'name': repo_name, 'path': self.repo_dir}, write=True)
        file_query = '\n        MATCH (r:Repository {path: $repo_path})\n        CREATE (f:File {name: $name, path: $path})\n        CREATE (r)-[:CONTAINS]->(f)\n        RETURN f\n        '
        self.neo4j_connector.execute_query(file_query, params={'repo_path': self.repo_dir, 'name': 'README.md', 'path': 'README.md'}, write=True)
        dir_query = '\n        MATCH (r:Repository {path: $repo_path})\n        CREATE (d:Directory {name: $name, path: $path})\n        CREATE (r)-[:CONTAINS]->(d)\n        RETURN d\n        '
        self.neo4j_connector.execute_query(dir_query, params={'repo_path': self.repo_dir, 'name': 'src', 'path': 'src'}, write=True)
        subdir_query = '\n        MATCH (parent:Directory {path: $parent_path})\n        CREATE (d:Directory {name: $name, path: $path})\n        CREATE (parent)-[:CONTAINS]->(d)\n        RETURN d\n        '
        self.neo4j_connector.execute_query(subdir_query, params={'parent_path': 'src', 'name': 'package', 'path': 'src/package'}, write=True)
        nested_file_query = '\n        MATCH (d:Directory {path: $dir_path})\n        CREATE (f:File {name: $name, path: $path})\n        CREATE (d)-[:CONTAINS]->(f)\n        RETURN f\n        '
        self.neo4j_connector.execute_query(nested_file_query, params={'dir_path': 'src/package', 'name': 'module.py', 'path': 'src/package/module.py'}, write=True)
        self.neo4j_connector.execute_query(nested_file_query, params={'dir_path': 'src/package', 'name': '__init__.py', 'path': 'src/package/__init__.py'}, write=True)