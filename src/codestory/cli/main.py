"""Main CLI application for Code Story."""
import sys
import types
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
    cast,
)

import click
from click_didyoumean import DYMGroup  # type: ignore[import-untyped]
from rich.console import Console

from codestory.config import get_settings

from .client import ServiceClient, ServiceError

# Import version from main package
try:
    from codestory import __version__
except ImportError:
    __version__ = "0.0.0"


def print_version(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """Print version and exit."""
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"Code Story CLI v{__version__}")
    ctx.exit()


class _RichClickAttrs(Protocol):
    USE_RICH_MARKUP: bool
    SHOW_ARGUMENTS: bool
    GROUP_ARGUMENTS_OPTIONS: bool
    STYLE_ERRORS_SUGGESTION: str
    ERRORS_SUGGESTION: str


rich_click_module: Optional[types.ModuleType] = None
try:
    import rich_click as rich_click_module
except ImportError:
    import click as _click_for_rich

    _click_for_rich_typed = cast("_RichClickAttrs", _click_for_rich)
    _click_for_rich_typed.USE_RICH_MARKUP = False
    _click_for_rich_typed.SHOW_ARGUMENTS = False
    _click_for_rich_typed.GROUP_ARGUMENTS_OPTIONS = False
    _click_for_rich_typed.STYLE_ERRORS_SUGGESTION = ""
    _click_for_rich_typed.ERRORS_SUGGESTION = ""
    rich_click_module = _click_for_rich
if rich_click_module is not None:
    rich_click_typed = cast("_RichClickAttrs", rich_click_module)
    rich_click_typed.USE_RICH_MARKUP = True
    rich_click_typed.SHOW_ARGUMENTS = True
    rich_click_typed.GROUP_ARGUMENTS_OPTIONS = True
    rich_click_typed.STYLE_ERRORS_SUGGESTION = "yellow italic"
    rich_click_typed.ERRORS_SUGGESTION = (
        "Try running the command with --help to see available options."
    )
console: Console = Console()


class CodeStoryCommandGroup(DYMGroup):
    """Custom command group that shows help when a command fails."""

    def __call__(self: Any, *args: Any, **kwargs: Any) -> Any:
        """Override to catch and customize error handling."""
        try:
            return super().__call__(*args, **kwargs)
        except click.exceptions.UsageError as e:
            ctx: Optional[click.Context] = getattr(e, "ctx", None)
            if ctx is None:
                ctx = click.Context(self)
            formatter = ctx.make_formatter()
            self.format_help(ctx, formatter)
            ctx.terminal_width = formatter.width
            click.echo(formatter.getvalue().rstrip("\n"))
            click.echo("")
            error_msg: str = str(e)
            if "No such command" in error_msg and "Did you mean" not in error_msg:
                cmd_name: str = error_msg.split("'")[1] if "'" in error_msg else ""
                if cmd_name:
                    commands: List[str] = list(self.commands.keys())
                    similar: List[str] = [
                        cmd
                        for cmd in commands
                        if cmd.startswith(cmd_name[:1])
                        or cmd_name.lower() in cmd.lower()
                    ]
                    if similar:
                        error_msg += (
                            f"\n\nDid you mean one of these?\n    {', '.join(similar)}"
                        )
            click.echo(f"Error: {error_msg}", err=True)
            ctx.exit(e.exit_code)


@click.group(
    cls=CodeStoryCommandGroup,
    help="[bold]Code Story[/bold] - A tool for exploring and documenting codebases.",
    invoke_without_command=True,
    max_suggestions=5,
    cutoff=0.5,
)
@click.option(
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show version and exit.",
)
@click.option(
    "--service-url",
    help="URL of the Code Story service.",
    envvar="CODESTORY_SERVICE_URL",
)
@click.option(
    "--api-key", help="API key for authentication.", envvar="CODESTORY_API_KEY"
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
    ctx.ensure_object(dict)
    settings = get_settings()
    base_url: str = (
        service_url if service_url else f"http://localhost:{settings.service.port}/v1"
    )
    client = ServiceClient(
        base_url=base_url, api_key=api_key, console=console, settings=settings
    )
    ctx.obj["client"] = client
    ctx.obj["console"] = console
    ctx.obj["settings"] = settings
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


def register_commands() -> None:
    """Register all CLI commands."""
    from .commands import ask, config, database, ingest, query, service, ui, visualize

    app.add_command(ingest.ingest)
    app.add_command(ask.ask)
    app.add_command(config.config)
    app.add_command(database.database)
    app.add_command(query.query)
    app.add_command(service.service)
    app.add_command(ui.ui)
    app.add_command(visualize.visualize)
    app.add_command(ingest.ingest, name="in")
    app.add_command(query.run_query, name="q")
    app.add_command(config.config, name="cfg")
    app.add_command(service.status, name="st")
    app.add_command(ask.ask, name="gs")
    app.add_command(visualize.generate, name="vz")
    app.add_command(database.database, name="db")
    app.add_command(service.start_service, name="ss")
    app.add_command(service.stop_service, name="sx")
    app.add_command(ingest.stop_job, name="is")
    app.add_command(ingest.list_jobs, name="ij")
    app.add_command(config.show_config, name="cfs")
    app.add_command(database.clear_database, name="dbc")
    app.add_command(service.status, name="status")
    app.add_command(service.start_service, name="start")
    app.add_command(service.stop_service, name="stop")
    app.add_command(config.show_config, name="show")
    app.add_command(database.clear_database, name="clear")


register_commands()


def _wrap_click_command(cmd: click.Command) -> Callable[..., Any]:
    """Create a wrapper around a Click command to intercept UsageError exceptions."""
    original_main: Callable[..., Any] = cmd.main

    def wrapped_main(*args: Any, **kwargs: Any) -> Any:
        try:
            return original_main(*args, **kwargs)
        except click.exceptions.UsageError as e:
            ctx: Optional[click.Context] = getattr(e, "ctx", None)
            help_text: str
            if ctx and ctx.command:
                help_text = ctx.get_help()
            else:
                ctx = click.Context(app)
                help_text = app.get_help(ctx)
            error_msg: str = str(e)
            if "No such command" in error_msg:
                cmd_name: str = error_msg.split("'")[1] if "'" in error_msg else ""
                if cmd_name:
                    commands: List[str] = list(app.commands.keys())
                    similar: List[str] = [
                        cmd
                        for cmd in commands
                        if cmd.startswith(cmd_name[:1])
                        or any(
                            cmd_name == alias
                            for alias in ["status", "start", "stop", "config"]
                        )
                        or cmd_name.lower() in cmd.lower()
                    ]
                    if similar and "Did you mean" not in error_msg:
                        error_msg += (
                            f"\n\nDid you mean one of these?\n    {', '.join(similar)}"
                        )
            elif (
                "no such option" in error_msg.lower()
                or "invalid value" in error_msg.lower()
            ):
                if ctx and ctx.command:
                    pass
            console.print(help_text)
            console.print("\n")
            console.print(f"[bold red]Error:[/] {error_msg}")
            sys.exit(e.exit_code)

    return wrapped_main


app.main = _wrap_click_command(app)


def main() -> None:
    """Entry point for the CLI application."""
    original_error_callback = click.exceptions.UsageError.show

    def custom_error_callback(
        self: click.exceptions.UsageError, file: Optional[IO[Any]] = None
    ) -> None:
        """Custom error formatter that shows error first, then suggestions, then help."""
        ctx: Optional[click.Context] = getattr(self, "ctx", None)
        help_text: str
        if ctx and ctx.command:
            help_text = ctx.get_help()
        else:
            ctx = click.Context(app)
            help_text = app.get_help(ctx)
        error_msg: str = str(self)
        suggestions: str = ""
        if "No such command" in error_msg:
            cmd_name: str = error_msg.split("'")[1] if "'" in error_msg else ""
            if cmd_name:
                commands: List[str] = []
                if ctx and hasattr(ctx, "command") and hasattr(ctx.command, "commands"):
                    commands = list(ctx.command.commands.keys())
                else:
                    commands = list(app.commands.keys())
                similar: List[str] = [
                    cmd
                    for cmd in commands
                    if cmd.startswith(cmd_name[:1])
                    or cmd_name.lower() in cmd.lower()
                    or any(
                        cmd_name == alias
                        for alias in ["status", "start", "stop", "config"]
                    )
                ]
                if similar and "Did you mean" not in error_msg:
                    suggestions = (
                        f"\nDid you mean one of these?\n    {', '.join(similar)}"
                    )
        console.print(f"[bold red]Error:[/] {error_msg}")
        if suggestions:
            console.print(suggestions)
            console.print("")
        console.print(help_text)

    try:
        click.exceptions.UsageError.show = custom_error_callback  # type: ignore[method-assign]
        app()
    except ServiceError as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/] {e!s}")
        console.print_exception(show_locals=False)
        sys.exit(1)
    finally:
        click.exceptions.UsageError.show = original_error_callback  # type: ignore[method-assign]


if __name__ == "__main__":
    main()
