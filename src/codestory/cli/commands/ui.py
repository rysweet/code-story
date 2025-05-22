"""
UI commands for the Code Story CLI.
"""

import click

# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    pass
from rich.console import Console

from ..client import ServiceClient, ServiceError
from ..require_service_available import require_service_available


@click.command(help="Open the Code Story GUI in a browser.")
@click.pass_context
def ui(ctx: click.Context) -> None:
    """
    Open the Code Story GUI in a browser.
    """
    require_service_available()

    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Opening Code Story GUI in browser...")

    try:
        # Check if service is running
        client.check_service_health()

        # Open the UI
        client.open_ui()
        console.print("[green]GUI opened in browser.[/]")

    except ServiceError as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        console.print("[yellow]Is the Code Story service running?[/]")
        console.print("Try starting it with: [cyan]codestory service start[/]")
