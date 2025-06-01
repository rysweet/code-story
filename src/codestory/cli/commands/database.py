"""Database commands for the Code Story CLI."""
from typing import Any

import click
from rich.panel import Panel
from rich.prompt import Confirm

from ..client import ServiceError


@click.group(name='database', help='Manage the graph database.', short_help='Manage the graph database')
def database() -> None:
    """Database commands group."""
    pass

@database.command(name='clear', help='Clear all data from the Neo4j database.', short_help='Clear all data from the database')
@click.option('--force', is_flag=True, help='Force clearing without confirmation.')
@click.pass_context
def clear_database(ctx: Any, force: bool) -> None:
    """Clear all data from the Neo4j database.

    Args:
        ctx: Click context
        force: Whether to skip the confirmation prompt
    """
    client = ctx.obj['client']
    console = ctx.obj['console']
    if not force:
        confirmed = Confirm.ask('[yellow]Warning:[/yellow] This will delete all nodes and relationships from the database. Continue?', default=False)
        if not confirmed:
            console.print('[yellow]Operation cancelled.[/yellow]')
            return
    try:
        console.print('Clearing database...')
        result = client.clear_database(confirm=True)
        console.print(Panel.fit(f"[green]Database cleared successfully.[/green]\n[dim]Timestamp: {result.get('timestamp', 'unknown')}[/dim]", title='Database Clear', border_style='green'))
    except ServiceError as e:
        console.print(f'[bold red]Error:[/bold red] {e}')