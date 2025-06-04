import pytest
import docker

def test_docker_client_closed_no_resourcewarning():
    """
    Ensure that creating and closing a Docker client does not emit ResourceWarning.
    This simulates the fixture pattern used in CLI integration tests.
    """
    with pytest.warns(None) as record:
        client = docker.from_env()
        try:
            client.ping()
        finally:
            client.close()
    # Assert no ResourceWarning was raised
    for warning in record:
        assert not isinstance(warning.message, ResourceWarning), f"Unexpected ResourceWarning: {warning.message}"