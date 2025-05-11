"""
Visualization commands for the Code Story CLI.
"""

import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    import click as rich_click
from rich.console import Console

from ..client import ServiceClient, ServiceError


@click.command(help="Generate a visualization of the Code Story graph.")
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path. If not specified, a temporary file will be created."
)
@click.option(
    "--open", "open_browser",
    is_flag=True,
    help="Open the visualization in a browser."
)
@click.pass_context
def visualize(ctx: click.Context, output: Optional[str] = None, open_browser: bool = False) -> None:
    """
    Generate a visualization of the Code Story graph.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]
    
    console.print("Generating graph visualization...")
    
    try:
        # Generate visualization
        html_content = client.generate_visualization()
        
        # Determine output path
        if output:
            output_path = os.path.abspath(output)
        else:
            # Create a file in the current directory
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = os.path.abspath(f"codestory-graph-{timestamp}.html")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Write visualization to file
        with open(output_path, "w") as f:
            f.write(html_content)
        
        console.print(f"Visualization saved to: [green]{output_path}[/]")
        
        # Open in browser if requested
        if open_browser:
            webbrowser.open(f"file://{output_path}")
            console.print("[green]Visualization opened in browser.[/]")
    
    except ServiceError as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        console.print("[yellow]Is the Code Story service running?[/]")
        console.print("Try starting it with: [cyan]codestory service start[/]")