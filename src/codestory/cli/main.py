"""Code Story CLI main entry point."""

import typer
from rich.console import Console

from src.codestory.config.cli import app as config_app

app = typer.Typer(
    name="codestory",
    help="Code Story - A system to convert codebases into richly-linked knowledge graphs",
    no_args_is_help=True,
)

# Add subcommands
app.add_typer(config_app, name="config")

console = Console()


@app.callback()
def callback():
    """Code Story CLI - Convert codebases into richly-linked knowledge graphs."""
    pass


@app.command("version")
def version():
    """Show the version of Code Story."""
    from src.codestory import __version__
    console.print(f"Code Story version {__version__}")


if __name__ == "__main__":
    app()