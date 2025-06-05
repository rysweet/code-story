import os
import time
import socket
import pytest

import docker
import uuid

NEO4J_IMAGE = "neo4j:5.22-community"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "test"
NEO4J_AUTH = f"{NEO4J_USER}/{NEO4J_PASSWORD}"

def get_free_port():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def wait_for_bolt(host, port, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(1)
    raise RuntimeError(f"Bolt port {port} on {host} did not become available in {timeout} seconds.")

@pytest.fixture(scope="session", autouse=True)
def neo4j_container():
    """
    Session-scoped fixture to run a Neo4j container for integration tests.
    Exports NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD as environment variables.
    """
    client = docker.from_env()
    name = f"cs-neo4j-{uuid.uuid4()}"
    # Clean up any stale cs-neo4j containers
    for c in client.containers.list(all=True, filters={"ancestor": NEO4J_IMAGE}):
        try:
            try:
                c.reload()
            except docker.errors.NotFound:
                continue
            try:
                c.remove(force=True)
            except docker.errors.NotFound:
                continue
            except docker.errors.APIError:
                pass
        except Exception:
            pass
    bolt_port = get_free_port()
    http_port = get_free_port()
    container = client.containers.run(
        NEO4J_IMAGE,
        detach=True,
        ports={f"7687/tcp": bolt_port, f"7474/tcp": http_port},
        environment={"NEO4J_AUTH": NEO4J_AUTH},
        auto_remove=True,
        name=name,
    )
    try:
        wait_for_bolt("localhost", bolt_port, timeout=60)
        os.environ["NEO4J_URI"] = f"bolt://localhost:{bolt_port}"
        os.environ["NEO4J_USER"] = NEO4J_USER
        os.environ["NEO4J_PASSWORD"] = NEO4J_PASSWORD
        yield
    finally:
        try:
            container.remove(force=True)
        except docker.errors.APIError as e:
            if hasattr(e, "status_code") and e.status_code in (404, 409):
                pass
            else:
                raise
        except Exception:
            pass