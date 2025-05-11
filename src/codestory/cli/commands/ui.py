"""
UI commands for the Code Story CLI.
"""

import click

# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    import click as rich_click
from rich.console import Console

from ..client import ServiceClient, ServiceError


@click.command(help="Open the Code Story GUI in a browser.")
@click.pass_context
def ui(ctx: click.Context) -> None:
    """
    Open the Code Story GUI in a browser.
    """
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
        console.print(f"[bold red]Error:[/] {str(e)}")
        console.print("[yellow]Is the Code Story service running?[/]")
        console.print("Try starting it with: [cyan]codestory service start[/]")
