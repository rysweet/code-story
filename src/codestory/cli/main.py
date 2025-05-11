"""
Main CLI application for Code Story.
"""

import os
import sys
from typing import Optional

import click

# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    import click as rich_click

    # Create fake attributes to avoid errors
    rich_click.USE_RICH_MARKUP = False
    rich_click.SHOW_ARGUMENTS = False
    rich_click.GROUP_ARGUMENTS_OPTIONS = False
    rich_click.STYLE_ERRORS_SUGGESTION = ""
    rich_click.ERRORS_SUGGESTION = ""
from rich.console import Console

from codestory.config import get_settings

from .client import ServiceClient, ServiceError

# Set up Rich for Click
rich_click.USE_RICH_MARKUP = True
rich_click.SHOW_ARGUMENTS = True
rich_click.GROUP_ARGUMENTS_OPTIONS = True
rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"
rich_click.ERRORS_SUGGESTION = (
    "Try running the command with --help to see available options."
)

# Create console
console = Console()


@click.group(
    help="[bold]Code Story[/bold] - A tool for exploring and documenting codebases."
)
@click.version_option()
@click.option(
    "--service-url",
    help="URL of the Code Story service.",
    envvar="CODESTORY_SERVICE_URL",
)
@click.option(
    "--api-key",
    help="API key for authentication.",
    envvar="CODESTORY_API_KEY",
)
@click.pass_context
def app(
    ctx: click.Context, service_url: Optional[str] = None, api_key: Optional[str] = None
) -> None:
    """
    Code Story CLI application.

    This tool provides commands for interacting with the Code Story service,
    including ingestion, querying, and visualization of codebases.
    """
    # Create context object to store shared state
    ctx.ensure_object(dict)

    # Create service client
    settings = get_settings()

    if service_url:
        base_url = service_url
    else:
        base_url = f"http://localhost:{settings.service.port}/v1"

    client = ServiceClient(
        base_url=base_url,
        api_key=api_key,
        console=console,
        settings=settings,
    )

    # Store in context
    ctx.obj["client"] = client
    ctx.obj["console"] = console
    ctx.obj["settings"] = settings


# Register commands later to avoid circular imports
def register_commands():
    """Register all CLI commands."""
    from .commands import ask, config, ingest, query, service, ui, visualize

    # Register command groups
    app.add_command(ingest.ingest)
    app.add_command(ask.ask)
    app.add_command(config.config)
    app.add_command(query.query)
    app.add_command(service.service)
    app.add_command(ui.ui)
    app.add_command(visualize.visualize)

    # Aliases for common commands
    app.add_command(ingest.ingest, name="in")
    app.add_command(query.run_query, name="q")  # Alias for query run
    app.add_command(config.config, name="cfg")
    app.add_command(service.status, name="st")
    app.add_command(ask.ask, name="gs")  # Graph search
    app.add_command(visualize.generate, name="vz")  # Alias for visualize generate

    # Additional aliases from the spec
    app.add_command(service.start_service, name="ss")  # Service start
    app.add_command(service.stop_service, name="sx")  # Service stop
    app.add_command(ingest.stop_job, name="is")  # Ingest stop
    app.add_command(ingest.list_jobs, name="ij")  # Ingest jobs
    app.add_command(config.show_config, name="cfs")  # Config show


# Register commands after app is defined
register_commands()


def main() -> None:
    """
    Entry point for the CLI application.
    """
    try:
        app()
    except ServiceError as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/] {str(e)}")
        console.print_exception(show_locals=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
