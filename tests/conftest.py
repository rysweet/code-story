# --- Self-contained integration test fixture template for all required services ---

import pytest
import os
import time
from testcontainers.neo4j import Neo4jContainer
from testcontainers.redis import RedisContainer
from testcontainers.core.container import DockerContainer
import docker
from pathlib import Path

import pytest

def _running_integration_tests(config: pytest.Config) -> bool:
    """
    Return True if the current pytest invocation is intended to
    run integration tests.  Works for:
      • no -m flag          → treat as full run  (True)
      • -m "integration"    → integration only  (True)
      • -m "slow and integration"              (True)
      • -m "not integration"                   (False)
      • -m "unit"                              (False)
    """
    expr = (config.getoption("-m") or "").strip()
    if not expr:
        return True                       # full run
    if "not integration" in expr:
        return False
    return "integration" in expr

@pytest.fixture(scope="session")
def neo4j_container():
    with Neo4jContainer("neo4j:5.22") as neo4j:
        uri = neo4j.get_connection_url()
        os.environ["NEO4J_URI"] = uri
        os.environ["NEO4J__URI"] = uri
        os.environ["NEO4J_USERNAME"] = "neo4j"
        os.environ["NEO4J__USERNAME"] = "neo4j"
        os.environ["NEO4J_PASSWORD"] = "password"
        os.environ["NEO4J__PASSWORD"] = "password"
        os.environ["NEO4J_DATABASE"] = "neo4j"
        os.environ["NEO4J__DATABASE"] = "neo4j"
        yield neo4j

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        uri = f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
        os.environ["REDIS_URI"] = uri
        os.environ["REDIS__URI"] = uri
        yield redis

@pytest.fixture(scope="session")
def celery_worker_container(request):
    # Only start the worker container for integration tests
    if not _running_integration_tests(request.config):
        yield None
        return

    image_tag = "code-story-worker:latest"
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    # Build image if absent
    client = docker.from_env()
    try:
        client.images.get(image_tag)
    except docker.errors.ImageNotFound:
        dockerfile = PROJECT_ROOT / "Dockerfile.worker"
        client.images.build(
            path=str(PROJECT_ROOT),
            dockerfile=str(dockerfile),
            tag=image_tag,
            rm=True,
        )

    worker = DockerContainer(image_tag).with_name("codestory-worker")
    worker.with_env("CELERY_TASK_ALWAYS_EAGER", "true")
    worker.with_env("CELERY_TASK_STORE_EAGER_RESULT", "true")
    worker.start()
    # Wait for the worker to be ready (implement a health check if needed)
    time.sleep(10)
    yield worker
    worker.stop()

@pytest.fixture(autouse=True, scope="session")
def all_services(request, neo4j_container, redis_container, celery_worker_container):
    # Only activate for integration tests
    if not _running_integration_tests(request.config):
        yield
        return
    # This fixture ensures all services are up for the test session
    yield
    # Cleanup is handled by the context managers above
import subprocess

import pytest

@pytest.fixture(scope="session", autouse=True)
def cleanup_docker_containers():
    """Remove any conflicting containers before the test session starts."""
    container_names = [
        "codestory-neo4j",
        "codestory-redis",
        "codestory-worker",
        "codestory-service",
    ]
    for name in container_names:
        try:
            subprocess.run(
                ["docker", "rm", "-f", name],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass
"""Shared test fixtures and configuration for the codestory project."""
import os
import socket
import subprocess
import time
from collections.abc import Generator
from typing import Any

import pytest
import redis
from neo4j import GraphDatabase

os.environ["CODESTORY_TEST_ENV"] = "true"
os.environ["NEO4J_DATABASE"] = "neo4j"


# (test_databases, _wait_for_neo4j, _wait_for_redis removed: now managed by testcontainers)


@pytest.fixture
def neo4j_connector() -> None:
    """Create a Neo4j connector for testing with automatic cleanup."""
    from codestory.graphdb.neo4j_connector import Neo4jConnector
    from codestory.graphdb.schema import initialize_schema

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    connector = Neo4jConnector(
        uri=uri,
        username=username,
        password=password,
        database=database,
    )
    try:
        connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        initialize_schema(connector, force=True)
        yield connector
    finally:
        try:
            connector.execute_query("MATCH (n) DETACH DELETE n", write=True)
        except Exception:
            pass
        connector.close()


@pytest.fixture
def redis_client() -> None:
    """Create a Redis client for testing with automatic cleanup."""
    redis_url = os.getenv("REDIS_URI", "redis://localhost:6379/0")
    client = redis.Redis.from_url(redis_url)
    try:
        client.flushdb()
        yield client
    finally:
        try:
            client.flushdb()
        except Exception:
            pass
        client.close()


def pytest_configure(config: Any) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "docker: marks tests that require Docker")
    config.addinivalue_line("markers", "neo4j: marks tests that require Neo4j")
    config.addinivalue_line("markers", "redis: marks tests that require Redis")
def is_azure_openai_available() -> bool:
    """Check if Azure OpenAI credentials and endpoint are available and reachable."""
    key = os.environ.get("AZURE_OPENAI_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not key or not endpoint:
        return False
    # Try to resolve and connect to the endpoint host
    try:
        host = endpoint.replace("https://", "").replace("http://", "").split("/")[0]
        socket.create_connection((host, 443), timeout=2).close()
        return True
    except Exception:
        return False

@pytest.fixture(autouse=True)
def skip_if_azure_openai_unavailable(request):
    """Skip tests marked azure_openai if Azure OpenAI is not available."""
    if "azure_openai" in request.keywords and not is_azure_openai_available():
        pytest.skip("Azure OpenAI service or credentials not available")

def pytest_collection_modifyitems(session, config, items):
    """Sort tests so non-integration tests run first, and auto-mark integration tests by path."""
    def is_integration(item):
        # Mark if test is already marked or path contains /integration/
        if "integration" in item.keywords:
            return True
        if "/integration/" in str(item.fspath):
            # Auto-mark if not already
            if "integration" not in item.keywords:
                item.add_marker(pytest.mark.integration)
            return True
        return False

    # Stable sort: non-integration first, then integration, preserving per-module order
    items.sort(key=lambda item: (is_integration(item), str(item.fspath), item.name))

import os
import pytest
from testcontainers.neo4j import Neo4jContainer

@pytest.fixture(scope="session", autouse=True)
def neo4j_container(request):
    """Spin up a Neo4j container for the test session and set NEO4J_URI env vars, but only for integration tests."""
    # Skip container startup unless integration tests are being run
    if not _running_integration_tests(request.config):
        yield None
        return
    with Neo4jContainer("neo4j:5.22") as neo4j:
        uri = neo4j.get_connection_url()
        os.environ["NEO4J_URI"] = uri
        os.environ["NEO4J__URI"] = uri
        os.environ["NEO4J_USERNAME"] = "neo4j"
        os.environ["NEO4J__USERNAME"] = "neo4j"
        os.environ["NEO4J_PASSWORD"] = "password"
        os.environ["NEO4J__PASSWORD"] = "password"
        os.environ["NEO4J_DATABASE"] = "neo4j"
        os.environ["NEO4J__DATABASE"] = "neo4j"
        yield uri

import os
import pytest
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session", autouse=True)
def redis_container(request):
    """Spin up a Redis container for the test session and set REDIS_URI env vars, but only for integration tests."""
    # Skip container startup unless integration tests are being run
    if not _running_integration_tests(request.config):
        yield None
        return
    with RedisContainer("redis:7-alpine") as redis:
        uri = f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
        os.environ["REDIS_URI"] = uri
        os.environ["REDIS__URI"] = uri
        yield uri
