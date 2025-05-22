#!/usr/bin/env python
"""Run the test directly without using pytest's collection."""

import sys
import os
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.integration.test_ingestion_pipeline.test_filesystem_integration import (
    test_filesystem_step_run,
)


# Create fixtures ourselves
def create_sample_repo():
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple directory structure
        repo_dir = Path(temp_dir) / "sample_repo"
        repo_dir.mkdir()

        # Create some directories
        (repo_dir / "src").mkdir()
        (repo_dir / "src" / "main").mkdir()
        (repo_dir / "src" / "test").mkdir()
        (repo_dir / "docs").mkdir()

        # Create some files
        (repo_dir / "README.md").write_text("# Sample Repository")
        (repo_dir / "src" / "main" / "app.py").write_text(
            "def main():\n    print('Hello, world!')"
        )
        (repo_dir / "src" / "test" / "test_app.py").write_text(
            "def test_main():\n    assert True"
        )
        (repo_dir / "docs" / "index.md").write_text("# Documentation")

        # Add some files that should be ignored
        (repo_dir / ".git").mkdir()
        (repo_dir / ".git" / "config").write_text("# Git config")
        (repo_dir / "src" / "__pycache__").mkdir()
        (repo_dir / "src" / "__pycache__" / "app.cpython-310.pyc").write_text(
            "# Bytecode"
        )

        return str(repo_dir)


def create_neo4j_connector():
    """Create a Neo4j connector for testing."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector

    # Use direct connection parameters to connect to the test Neo4j instance
    connector = Neo4jConnector(
        uri="bolt://localhost:"
        + (
            os.environ.get("CI") == "true" and "7687" or "7688"
        ),  # Port defined in docker-compose.test.yml
        username="neo4j",
        password="password",
        database="codestory-test",  # Database defined in docker-compose.test.yml
    )

    # Clear the database before each test - this is a WRITE operation
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True, params={})
        print("Successfully connected to Neo4j and cleared the database")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {str(e)}")
        raise

    return connector


if __name__ == "__main__":
    try:
        sample_repo = create_sample_repo()
        neo4j_connector = create_neo4j_connector()

        print("Running test_filesystem_step_run directly...")
        test_filesystem_step_run(sample_repo, neo4j_connector)

        print("Test completed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if "neo4j_connector" in locals():
            neo4j_connector.close()
