import pytest
import subprocess

@pytest.fixture(autouse=True, scope="session")
def mock_docker_compose(monkeypatch):
    """Monkeypatch subprocess.run to neutralize docker-compose and docker compose calls."""

    original_run = subprocess.run

    def fake_run(*args, **kwargs):
        # args[0] can be a list or a string
        cmd = args[0]
        if (
            (isinstance(cmd, str) and "docker-compose" in cmd)
            or (isinstance(cmd, (list, tuple)) and (
                "docker-compose" in cmd or (len(cmd) >= 2 and cmd[0] == "docker" and cmd[1] == "compose"))
            )
        ):
            return subprocess.CompletedProcess(cmd, 0)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)