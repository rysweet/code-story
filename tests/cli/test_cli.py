import pytest
from typer.testing import CliRunner


def test_cli_app_is_typer_instance():
    """
    If codestory.cli.app exists, it should expose a Typer app instance.
    """
    app_mod = pytest.importorskip("codestory.cli.app")
    import typer

    assert isinstance(app_mod.app, typer.Typer)


def test_cli_main_exits_zero():
    """
    Running the CLI app with no subcommands should exit 0 (help shown).
    """
    app_mod = pytest.importorskip("codestory.cli.app")
    runner = CliRunner()
    result = runner.invoke(app_mod.app)
    assert result.exit_code == 0
    assert "CodeStory command-line interface" in result.output
