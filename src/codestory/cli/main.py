"""Main CLI application for Code Story."""

import sys

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


class CodeStoryCommandGroup(DYMGroup):
    """Custom command group that shows help when a command fails."""
    
    def __call__(self, *args, **kwargs):
        """Override to catch and customize error handling."""
        try:
            return super().__call__(*args, **kwargs)
        except click.exceptions.UsageError as e:
            # Get the context
            ctx = getattr(e, 'ctx', None)
            if ctx is None:
                ctx = click.Context(self)
            
            # Show full help first
            formatter = ctx.make_formatter()
            self.format_help(ctx, formatter)
            ctx.terminal_width = formatter.width
            click.echo(formatter.getvalue().rstrip('\n'))
            click.echo('')  # Add a blank line
            
            # Then show the error with custom formatting
            error_msg = str(e)
            # Add suggestions for command-not-found errors if not already present
            if "No such command" in error_msg and "Did you mean" not in error_msg:
                cmd_name = error_msg.split("'")[1] if "'" in error_msg else ""
                if cmd_name:
                    # Find similar commands
                    commands = list(self.commands.keys())
                    similar = [cmd for cmd in commands if (
                        cmd.startswith(cmd_name[:1]) or
                        cmd_name.lower() in cmd.lower()
                    )]
                    
                    if similar:
                        error_msg += f"\n\nDid you mean one of these?\n    {', '.join(similar)}"
            
            # Show the error with custom formatting
            click.echo(f"Error: {error_msg}", err=True)
            
            # Exit with the same code
            ctx.exit(e.exit_code)

@click.group(
    cls=CodeStoryCommandGroup,
    help="[bold]Code Story[/bold] - A tool for exploring and documenting codebases.",
    invoke_without_command=True,
    max_suggestions=5,
    cutoff=0.5
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
    ctx: click.Context, service_url: str | None = None, api_key: str | None = None
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
    
    # Enhanced aliases for better suggestions and direct command access
    # Add common top-level commands as direct aliases
    app.add_command(service.status, name="status")  # Direct alias for "service status"
    app.add_command(service.start_service, name="start")  # Direct alias for "service start"
    app.add_command(service.stop_service, name="stop")  # Direct alias for "service stop"
    app.add_command(config.show_config, name="show")  # Direct alias for "config show"


# Register commands after app is defined
register_commands()


# Create a wrapper function that will intercept UsageError exceptions
def _wrap_click_command(cmd):
    """Create a wrapper around a Click command to intercept UsageError exceptions."""
    original_main = cmd.main
    
    def wrapped_main(*args, **kwargs):
        try:
            return original_main(*args, **kwargs)
        except click.exceptions.UsageError as e:
            # Extract relevant context information
            ctx = getattr(e, 'ctx', None)
            
            # Get appropriate help text
            if ctx and ctx.command:
                # Get help text for the specific command context
                help_text = ctx.get_help()
            else:
                # Fallback to general app help when we don't have a specific command context
                ctx = click.Context(app)
                help_text = app.get_help(ctx)
            
            # Format the error message
            error_msg = str(e)
            
            # Check if we're dealing with an invalid command
            if "No such command" in error_msg:
                # Extract the command name that wasn't found
                cmd_name = error_msg.split("'")[1] if "'" in error_msg else ""
                if cmd_name:
                    # Find similar commands (already registered and common aliases)
                    commands = list(app.commands.keys())
                    similar = [cmd for cmd in commands if (
                        cmd.startswith(cmd_name[:1]) or  # Starts with same letter
                        any(cmd_name == alias for alias in ["status", "start", "stop", "config"]) or  # Common aliases
                        cmd_name.lower() in cmd.lower()  # Contains the text
                    )]
                    
                    # Add suggestions if not already provided by DYMGroup
                    if similar and "Did you mean" not in error_msg:
                        error_msg += f"\n\nDid you mean one of these?\n    {', '.join(similar)}"
                        
            # For invalid option errors, provide more context
            elif "no such option" in error_msg.lower() or "invalid value" in error_msg.lower():
                if ctx and ctx.command:
                    # We already have the help text above, but we could add more specific hints here
                    pass
            
            # Display everything in the right order
            console.print(help_text)
            console.print("\n")  # Spacing
            console.print(f"[bold red]Error:[/] {error_msg}")
            sys.exit(e.exit_code)
    
    return wrapped_main

# Apply the wrapper to the Click app
app.main = _wrap_click_command(app)

def main() -> None:
    """Entry point for the CLI application."""
    # Save the original error callback for restoration later
    original_error_callback = click.exceptions.UsageError.show
    
    # Define our custom error handler
    def custom_error_callback(self, file=None):
        """Custom error formatter that shows error first, then suggestions, then help."""
        # Get the context
        ctx = getattr(self, 'ctx', None)
        
        # Get appropriate help text
        if ctx and ctx.command:
            # Get help text for the specific command context
            help_text = ctx.get_help()
        else:
            # Fallback to general app help when we don't have a specific command context
            ctx = click.Context(app)
            help_text = app.get_help(ctx)
        
        # Format the error message first
        error_msg = str(self)
        
        # Check if we're dealing with an invalid command
        suggestions = ""
        if "No such command" in error_msg:
            # Extract the command name that wasn't found
            cmd_name = error_msg.split("'")[1] if "'" in error_msg else ""
            if cmd_name:
                # Find commands to search in
                commands = []
                
                # Get the current command context to find available subcommands
                if ctx and hasattr(ctx, 'command') and hasattr(ctx.command, 'commands'):
                    # For subcommand errors, use the parent command's subcommands
                    commands = list(ctx.command.commands.keys())
                else:
                    # For top-level errors, use app's commands
                    commands = list(app.commands.keys())
                
                # Find similar commands
                similar = [cmd for cmd in commands if (
                    cmd.startswith(cmd_name[:1]) or  # Starts with same letter
                    cmd_name.lower() in cmd.lower() or  # Contains the text
                    any(cmd_name == alias for alias in ["status", "start", "stop", "config"])  # Common aliases
                )]
                
                # Add suggestions separately
                if similar and "Did you mean" not in error_msg:
                    suggestions = f"\nDid you mean one of these?\n    {', '.join(similar)}"
        
        # Display in the requested order: 1) error, 2) suggestions, 3) help
        console.print(f"[bold red]Error:[/] {error_msg}")
        
        # Show suggestions if any
        if suggestions:
            console.print(suggestions)
            console.print("")  # Add spacing
            
        # Finally display the help text
        console.print(help_text)
    
    try:
        # Replace the error handler
        click.exceptions.UsageError.show = custom_error_callback
        
        # Run the app with our enhanced error handling
        app()
    except ServiceError as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/] {e!s}")
        console.print_exception(show_locals=False)
        sys.exit(1)
    finally:
        # Restore the original error handler
        click.exceptions.UsageError.show = original_error_callback




if __name__ == "__main__":
    main()
