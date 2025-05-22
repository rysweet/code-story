#!/usr/bin/env python
"""Script to test the filesystem step inside the container environment."""

import logging
import time
import uuid

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory_filesystem.step import process_filesystem

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def test_filesystem_step():
    """Test the process_filesystem function directly."""
    print("=" * 80)
    print("TESTING FILESYSTEM STEP DIRECTLY IN CONTAINER")
    print("=" * 80)

    # Create a job ID for testing
    job_id = f"test-container-{uuid.uuid4()}"
    repository_path = "/repositories/code-story"

    print(f"Testing with repository_path: {repository_path}")
    print(f"Job ID: {job_id}")

    try:
        # Test Neo4j connection first
        settings = get_settings()
        print(f"Neo4j URI: {settings.neo4j.uri}")
        print(f"Neo4j Database: {settings.neo4j.database}")

        # Create connection with container hostname
        neo4j = Neo4jConnector(
            uri=settings.neo4j.uri,
            username=settings.neo4j.username,
            password=settings.neo4j.password.get_secret_value(),
            database=settings.neo4j.database,
        )

        try:
            # Test connection with a simple query
            result = neo4j.execute_query("MATCH (n) RETURN count(n) as count")
            print(f"Neo4j connection test: {result}")

            # Create a test node to verify write access
            test_node = neo4j.create_node(
                label="TestNode",
                properties={
                    "name": f"test-{job_id}",
                    "timestamp": time.time(),
                },
            )
            print(f"Created test node: {test_node}")
        finally:
            # Ensure connection is closed
            neo4j.close()

        # Create a mock self object for the bound method
        class MockTask:
            def __init__(self):
                self.request = type(
                    "obj", (object,), {"id": f"mock-task-{uuid.uuid4()}"}
                )

        mock_self = MockTask()

        # Now call the process_filesystem function directly
        print("Calling process_filesystem directly...")
        print(f"Repository path: {repository_path}")
        print(f"Job ID: {job_id}")

        # Process just a few files for testing
        result = process_filesystem(
            self=mock_self,
            repository_path=repository_path,
            job_id=job_id,
            ignore_patterns=[
                "node_modules/",
                ".git/",
                "__pycache__/",
                "*.pyc",
                "*.pyo",
                "venv/",
                ".venv/",
            ],
            max_depth=1,  # Limit depth for testing
        )

        print(f"Function result: {result}")
        return result

    except Exception as e:
        print(f"Error in container test: {e}")
        import traceback

        traceback.print_exc()
        return {"status": "FAILED", "error": str(e)}


if __name__ == "__main__":
    # Run the test
    print("Starting container filesystem step test...")
    result = test_filesystem_step()
    print("\nSummary:")
    print(f"Container test result: {result}")
