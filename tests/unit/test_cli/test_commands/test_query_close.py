import pytest
import warnings

import click
from click.testing import CliRunner

from src.codestory.cli.commands.query import run_query

@pytest.mark.filterwarnings("error")
def test_run_query_no_resource_warning(monkeypatch):
    """Ensure running the query command does not emit ResourceWarning (e.g., unclosed aiohttp socket)."""
    # Patch require_service_available to no-op
    monkeypatch.setattr("src.codestory.cli.commands.query.require_service_available", lambda: None)
    # Patch ServiceClient to a dummy with execute_query returning a simple result
    class DummyClient:
        def execute_query(self, query_string, parameters=None):
            return {"records": [{"foo": "bar"}]}
        def close(self):
            pass
    dummy_console = type("Console", (), {"print": lambda self, *a, **k: None})()
    ctx_obj = {"client": DummyClient(), "console": dummy_console}

    runner = CliRunner()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("error")
        result = runner.invoke(
            run_query,
            ["MATCH (n) RETURN n"],
            obj=ctx_obj,
        )
    assert result.exit_code == 0
    assert not w, f"Unexpected warnings: {w}"