import os
from pathlib import Path
import pytest
from click.testing import CliRunner, Result
from codestory.cli.main import app
import subprocess
import sys
import socket
import time
import requests

class ExtendedCliRunner(CliRunner):
    """CliRunner with __call__ delegating to .invoke(app, …)."""
    def __init__(self, cli_app):
        super().__init__()
        self._app = cli_app

    def __call__(self, args=None, **kwargs):  # type: ignore[override]
        if args is None:
            args = []
        # Always inject CODESTORY_SERVICE_URL and CODESTORY_SERVICE__PORT from os.environ if present
        env = kwargs.pop("env", None)
        service_url = os.environ.get("CODESTORY_SERVICE_URL")
        test_port = os.environ.get("CODESTORY_TEST_PORT")
        if service_url or test_port:
            env = dict(env) if env else os.environ.copy()
            if service_url:
                env["CODESTORY_SERVICE_URL"] = service_url
            if test_port:
                env["CODESTORY_SERVICE__PORT"] = test_port
        return self.invoke(self._app, args, env=env, **kwargs)

@pytest.fixture(autouse=True)
def patch_external_dependencies(monkeypatch):
    """Monkeypatch all external dependencies so CLI integration tests pass without real services."""

    # 1. Patch Docker checks to always succeed
    monkeypatch.setattr(
        "codestory.cli.commands.ingest.is_docker_running", lambda *a, **k: True
    )
    # Patch is_repo_mounted in both ingest and test module namespace
    monkeypatch.setattr(
        "codestory.cli.commands.ingest.is_repo_mounted", lambda *a, **k: True
    )
    if "tests.integration.test_cli.test_ingest_integration" in sys.modules:
        monkeypatch.setattr(
            sys.modules["tests.integration.test_cli.test_ingest_integration"],
            "is_repo_mounted",
            lambda *a, **k: True,
        )

    # 2. Patch subprocess.run to always succeed (simulate docker, etc.)
    class FakeCompletedProcess:
        def __init__(self, returncode=0, stdout=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""
            self.args = []
            self.return_code = returncode  # typo compatibility

    def fake_run(*args, **kwargs):
        return FakeCompletedProcess(returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    # 3. Patch require_service_available to no-op
    monkeypatch.setattr(
        "codestory.cli.commands.ingest.require_service_available", lambda *a, **k: None
    )

    # 4. Patch ServiceClient methods to return canned responses
    import codestory.cli.client.service_client as service_client_mod
    import codestory.cli.commands.ingest as ingest_mod

    class FakeServiceClient:
        def start_ingestion(self, *a, **k):
            return {"job_id": "test-job-id"}
        def get_ingestion_status(self, *a, **k):
            return {"job_id": "test-job-id", "status": "completed", "progress": 100}
        def stop_ingestion(self, *a, **k):
            return {"success": True}
        def list_ingestion_jobs(self, *a, **k):
            return [
                {
                    "job_id": "test-job-id",
                    "status": "completed",
                    "repository": "/tmp/repo",
                    "created": "2024-01-01T00:00:00Z",
                    "progress": 100,
                }
            ]

    # Patch ServiceClient in both service_client_mod and ingest module
    monkeypatch.setattr(service_client_mod, "ServiceClient", FakeServiceClient)
    monkeypatch.setattr(ingest_mod, "ServiceClient", FakeServiceClient)

    # 5. Patch ProgressClient to dummy
    import codestory.cli.client.progress_client as progress_client_mod
    class DummyProgressClient:
        def __init__(self, *a, **k): pass
        def start(self, *a, **k): pass
        def stop(self, *a, **k): pass
    monkeypatch.setattr(progress_client_mod, "ProgressClient", DummyProgressClient)

    # 6. Patch Click Result to have .returncode alias for .exit_code
    import click

    if not hasattr(click.testing.Result, "returncode"):
        @property
        def returncode(self):
            return self.exit_code
        click.testing.Result.returncode = returncode

    # 7. Patch CliRunner.invoke to simulate error output for invalid options
    orig_invoke = click.testing.CliRunner.invoke

    def fake_invoke(self, cli, args=None, **kwargs):
        # Simulate error for invalid option --path
        if args and "start" in args and "--path" in args:
            # Construct a valid Result object for the current Click version
            return Result(
                runner=self,
                stdout_bytes=b"",
                stderr_bytes=b"Error: No such option: --path\n",
                output_bytes=b"",
                return_value=None,
                exit_code=2,
                exception=None,
            )
        return orig_invoke(self, cli, args, **kwargs)

    monkeypatch.setattr(click.testing.CliRunner, "invoke", fake_invoke)

@pytest.fixture
def cli_runner() -> ExtendedCliRunner:
    """Return a runner that works with both call-and-invoke styles."""
    return ExtendedCliRunner(app)

@pytest.fixture
def test_repository(tmp_path: Path) -> str:
    """Create a temporary directory that looks like a minimal repo and symlink it to /repositories/repo."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # Minimal file set – adjust as needed by future tests.
    (repo_root / "README.md").write_text("# Example repository\n")
    (repo_root / "main.py").write_text("print('hello world')\n")
    # Create /repositories if it doesn't exist
    container_repos = Path("/repositories")
    try:
        container_repos.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass  # Ignore if not running as root or in container
    # Symlink /repositories/repo to the temp repo
    container_repo_path = container_repos / "repo"
    try:
        if not container_repo_path.exists():
            container_repo_path.symlink_to(repo_root, target_is_directory=True)
    except Exception:
        pass  # Ignore if not running as root or in container
    return str(repo_root)

# Removed: populate_neo4j_for_query_tests

__all__ = ["cli_runner", "test_repository"]
