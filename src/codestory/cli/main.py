"""Main CLI application for Code Story."""

import sys
from typing import Optional, Union

import click
from click_didyoumean import DYMGroup

# Import rich_click if available, otherwise create a stub with click
rich_click_module = None
try:
    import rich_click as rich_click_module
except ImportError:
    # Create fake attributes on click module for fallback
    import click as _click_for_rich

    # Add required rich_click attributes to click module
    _click_for_rich.USE_RICH_MARKUP = False
    _click_for_rich.SHOW_ARGUMENTS = False
    _click_for_rich.GROUP_ARGUMENTS_OPTIONS = False
    _click_for_rich.STYLE_ERRORS_SUGGESTION = ""
    _click_for_rich.ERRORS_SUGGESTION = ""

    # Set our module variable
    rich_click_module = _click_for_rich
from rich.console import Console

from codestory.config import get_settings

from .client import ServiceClient, ServiceError

# Set up Rich for Click
rich_click_module.USE_RICH_MARKUP = True
rich_click_module.SHOW_ARGUMENTS = True
rich_click_module.GROUP_ARGUMENTS_OPTIONS = True
rich_click_module.STYLE_ERRORS_SUGGESTION = "yellow italic"
rich_click_module.ERRORS_SUGGESTION = (
    "Try running the command with --help to see available options."
)

# Create console
console = Console()


@click.group(
    cls=DYMGroup,
    help="[bold]Code Story[/bold] - A tool for exploring and documenting codebases.",
    invoke_without_command=True,
    max_suggestions=3,
    cutoff=0.6
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
    ctx: click.Context, service_url: Union[str, None] = None, api_key: Union[str, None] = None
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

    base_url = service_url if service_url else f"http://localhost:{settings.service.port}/v1"

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
    
    # If no command is invoked, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


# Register commands later to avoid circular imports
def register_commands() -> None:
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
    """Entry point for the CLI application."""
    try:
        # Add custom error handler for Click errors
        with custom_error_handler():
            app()
    except ServiceError as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/] {e!s}")
        console.print_exception(show_locals=False)
        sys.exit(1)


class custom_error_handler:
    """Custom context manager to handle Click errors more gracefully.
    
    This handler ensures that when a command is not found or used incorrectly,
    more helpful error messages are displayed along with suggestions.
    
    Note: Since Click's error handling changed over versions, this uses a more
    compatible approach by modifying how Click.Context.fail behaves rather than
    patching internal functions.
    """
    def __enter__(self):
        # Save the original Click Context.fail method
        self._original_fail = click.Context.fail
        
        # Create a new fail method that adds help suggestion
        def custom_fail(self_ctx, message):
            # Check if this is a command not found error (already handled by DYMGroup)
            if "No such command" in message or "Did you mean" in message:
                return self._original_fail(self_ctx, message)
            
            # For other errors, show the message and suggest help
            if not message.endswith("--help"):
                if not message.endswith("."):
                    message += "."
                message += " Try '--help' for more information."
            
            return self._original_fail(self_ctx, message)
        
        # Replace the method
        click.Context.fail = custom_fail
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the original method
        click.Context.fail = self._original_fail
        return False  # Allow exceptions to propagate


if __name__ == "__main__":
    main()
