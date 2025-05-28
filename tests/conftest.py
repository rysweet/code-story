"""Shared test fixtures and configuration for the codestory project."""

import os
import subprocess
import time
from collections.abc import Generator
from typing import Any

import pytest
import redis
from neo4j import GraphDatabase

# Test environment setup
os.environ["CODESTORY_TEST_ENV"] = "true"
os.environ["NEO4J_DATABASE"] = "testdb"


@pytest.fixture(scope="session")
def test_databases() -> Generator[dict[str, Any], None, None]:
    """Start test databases (Neo4j and Redis) for the entire test session.
    
    This fixture manages the lifecycle of test databases, starting them
    at the beginning of the test session and cleaning them up at the end.
    
    Yields:
        Dictionary with database connection information
    """
    # Skip database setup in CI if not needed
    if os.environ.get("SKIP_DATABASE_TESTS") == "true":
        pytest.skip("Database tests are disabled")
    
    print("Starting test databases...")
    
    try:
        # Start only the database services from docker-compose.test.yml
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.test.yml", "up", "-d", "neo4j", "redis"],
            capture_output=True,
            text=True,
            check=True,
            timeout=180  # 3 minutes timeout
        )
        print(f"Databases started: {result.stdout}")
        
        # Wait for databases to be ready
        print("Waiting for databases to be ready...")
        _wait_for_neo4j()
        _wait_for_redis()
        
        # Set environment variables for tests
        db_info = {
            "neo4j_uri": "bolt://localhost:7688",
            "neo4j_username": "neo4j", 
            "neo4j_password": "password",
            "neo4j_database": "testdb",
            "redis_url": "redis://localhost:6380/0"
        }
        
        # Export as environment variables for other tests
        os.environ["NEO4J__URI"] = db_info["neo4j_uri"]
        os.environ["NEO4J__USERNAME"] = db_info["neo4j_username"]
        os.environ["NEO4J__PASSWORD"] = db_info["neo4j_password"]
        os.environ["NEO4J__DATABASE"] = db_info["neo4j_database"]
        os.environ["REDIS__URI"] = db_info["redis_url"]
        
        yield db_info
        
    except subprocess.TimeoutExpired:
        pytest.fail("Timeout waiting for test databases to start")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start test databases: {e.stderr}")
    finally:
        print("Stopping test databases...")
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.test.yml", "down"],
            capture_output=True,
            text=True
        )


def _wait_for_neo4j(max_retries: int = 30, retry_delay: float = 2.0) -> None:
    """Wait for Neo4j to be ready for connections."""
    for i in range(max_retries):
        try:
            # Try to connect to Neo4j without specifying a database initially
            driver = GraphDatabase.driver(
                "bolt://localhost:7688",
                auth=("neo4j", "password")
            )
            with driver.session(database="neo4j") as session:  # Use default neo4j database for health check
                session.run("RETURN 1")
            driver.close()
            print("Neo4j is ready!")
            return
        except Exception as e:
            if i == max_retries - 1:
                raise RuntimeError(f"Neo4j failed to start within {max_retries * retry_delay}s: {e}")
            print(f"Waiting for Neo4j... ({i+1}/{max_retries})")
            time.sleep(retry_delay)


def _wait_for_redis(max_retries: int = 30, retry_delay: float = 1.0) -> None:
    """Wait for Redis to be ready for connections."""
    for i in range(max_retries):
        try:
            # Try to connect to Redis
            r = redis.Redis(host='localhost', port=6380, db=0)
            r.ping()
            print("Redis is ready!")
            return
        except Exception as e:
            if i == max_retries - 1:
                raise RuntimeError(f"Redis failed to start within {max_retries * retry_delay}s: {e}")
            print(f"Waiting for Redis... ({i+1}/{max_retries})")
            time.sleep(retry_delay)


@pytest.fixture
def neo4j_connector(test_databases):
    """Create a Neo4j connector for testing with automatic cleanup."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    from codestory.graphdb.schema import initialize_schema
    
    db_info = test_databases
    connector = Neo4jConnector(
        uri=db_info["neo4j_uri"],
        username=db_info["neo4j_username"],
        password=db_info["neo4j_password"],
        database=db_info["neo4j_database"]
    )
    
    try:
        # Clear database before each test
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        
        # Initialize schema with force=True to clear any existing constraints/indexes
        initialize_schema(connector, force=True)
        
        yield connector
    finally:
        # Clean up after each test
        try:
            connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        except Exception:
            # Ignore cleanup errors
            pass
        connector.close()


@pytest.fixture
def redis_client(test_databases):
    """Create a Redis client for testing with automatic cleanup."""
    db_info = test_databases
    client = redis.Redis.from_url(db_info["redis_url"])
    
    try:
        # Clear Redis before each test
        client.flushdb()
        yield client
    finally:
        # Clean up after each test
        try:
            client.flushdb()
        except Exception:
            # Ignore cleanup errors
            pass
        client.close()


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "docker: marks tests that require Docker")
    config.addinivalue_line("markers", "neo4j: marks tests that require Neo4j")
    config.addinivalue_line("markers", "redis: marks tests that require Redis")