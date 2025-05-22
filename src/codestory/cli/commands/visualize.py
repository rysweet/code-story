"""
Visualization commands for the Code Story CLI.
"""

import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import click

# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    pass
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..client import ServiceClient
from ..require_service_available import require_service_available


@click.group(help="Generate and manage visualizations of the Code Story graph.")
def visualize():
    """Command group for visualization operations."""
    pass


@visualize.command(
    name="generate", help="Generate a visualization of the Code Story graph."
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path. If not specified, a file will be created in the current directory.",
)
@click.option(
    "--open-browser/--no-browser",
    "open_browser",
    default=True,
    help="Open the visualization in a browser automatically.",
)
@click.option(
    "--type",
    "viz_type",
    type=click.Choice(["force", "hierarchy", "radial", "sankey"]),
    default="force",
    help="Type of visualization to generate.",
)
@click.option(
    "--theme",
    type=click.Choice(["light", "dark", "auto"]),
    default="auto",
    help="Color theme for the visualization.",
)
@click.option("--title", help="Custom title for the visualization.")
@click.pass_context
def generate(
    ctx: click.Context,
    output: str | None = None,
    open_browser: bool = True,
    viz_type: str = "force",
    theme: str = "auto",
    title: str | None = None,
) -> None:
    """
    Generate a visualization of the Code Story graph.
    """
    require_service_available()

    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # For storing the output path
    output_path = None

    # Show spinner while generating visualization
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Generating graph visualization..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Generating", total=None)

        try:
            # Generate visualization with options
            params: dict[str, Any] = {
                "type": viz_type,
                "theme": theme,
            }

            if title:
                params["title"] = title

            html_content = client.generate_visualization(params)

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

        except Exception as e:
            console.print(f"[bold red]Error:[/] {e!s}")
            console.print("[bold red]The Code Story service must be running.[/]")
            console.print("Starting service automatically...")

            # Try to start the service
            import subprocess
            import time

            try:
                # Start the service in the background
                subprocess.Popen(
                    ["codestory", "service", "start"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Wait for service to start (up to 10 seconds)
                service_started = False
                for _ in range(10):
                    time.sleep(1)
                    try:
                        client = ctx.obj["client"]
                        # Try a request to see if service is responsive
                        html_content = client.generate_visualization(params)
                        service_started = True
                        break
                    except Exception:
                        console.print("[yellow]Waiting for service to start...[/]")

                if not service_started:
                    raise Exception("Failed to start the service automatically")

                # Determine output path
                if output:
                    output_path = os.path.abspath(output)
                else:
                    # Create a file in the current directory
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    output_path = os.path.abspath(f"codestory-graph-{timestamp}.html")

                # Ensure directory exists
                os.makedirs(
                    os.path.dirname(os.path.abspath(output_path)), exist_ok=True
                )

                # Write visualization to file
                with open(output_path, "w") as f:
                    f.write(html_content)

            except Exception as start_error:
                console.print(f"[bold red]Failed to start service:[/] {start_error!s}")
                console.print(
                    "[bold red]Please start the service manually:[/] codestory service start"
                )
                return

    # Show success message
    if output_path:
        console.print(
            Panel.fit(
                f"[bold green]Visualization generated successfully![/]\n\n"
                f"📊 File saved to: [cyan]{output_path}[/]\n"
                f"🔍 Type: [magenta]{viz_type}[/]\n"
                f"🎨 Theme: [magenta]{theme}[/]",
                title="Graph Visualization",
                border_style="green",
            )
        )

        # Open in browser if requested
        if open_browser:
            webbrowser.open(f"file://{output_path}")
            console.print("[dim]Visualization opened in browser...[/]")
        else:
            console.print(
                "\nTo view the visualization, open the HTML file in a web browser."
            )
            console.print(f"Or run: [cyan]open {output_path}[/]")


@visualize.command(name="list", help="List previously generated visualizations.")
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Maximum number of visualizations to list.",
)
@click.pass_context
def list_visualizations(ctx: click.Context, limit: int = 10) -> None:
    """
    List previously generated visualizations.
    """
    console: Console = ctx.obj["console"]

    # Find HTML files in the current directory that match the pattern
    pattern = "codestory-graph-*.html"
    files = sorted(Path(".").glob(pattern), key=os.path.getmtime, reverse=True)

    if not files:
        console.print("[yellow]No visualizations found in the current directory.[/]")
        console.print("Generate one with: [cyan]codestory visualize generate[/]")
        return

    # Limit the number of files
    files = files[:limit]

    # Print list of files
    console.print("[bold]Recently generated visualizations:[/]")
    for i, file in enumerate(files, 1):
        size = os.path.getsize(file) / 1024  # KB
        modified = datetime.fromtimestamp(os.path.getmtime(file))
        console.print(
            f"{i}. [cyan]{file}[/] [{modified.strftime('%Y-%m-%d %H:%M:%S')}] [{size:.1f} KB]"
        )


@visualize.command(name="open", help="Open a previously generated visualization.")
@click.argument("path", type=click.Path(exists=True))
@click.pass_context
def open_visualization(ctx: click.Context, path: str) -> None:
    """
    Open a previously generated visualization.
    """
    console: Console = ctx.obj["console"]

    # Verify it's an HTML file
    if not path.lower().endswith(".html"):
        console.print("[bold red]Error:[/] File must be an HTML file.")
        return

    # Get absolute path
    abs_path = os.path.abspath(path)

    # Open in browser
    console.print(f"Opening [cyan]{abs_path}[/] in browser...")
    webbrowser.open(f"file://{abs_path}")


@visualize.command(name="help", help="Show information about visualization features.")
@click.pass_context
def viz_help(ctx: click.Context) -> None:
    """
    Show information about visualization features.
    """
    console: Console = ctx.obj["console"]

    help_text = """
    # Code Story Graph Visualization

    The visualization feature allows you to create interactive, browser-based visualizations
    of your code graph. These visualizations help you understand the structure and relationships
    in your codebase.

    ## Visualization Types

    - **Force** (default): A force-directed graph where nodes repel each other and edges act like springs.
      Best for showing relationships between components.

    - **Hierarchy**: A tree-like visualization showing inheritance and containment relationships.
      Useful for understanding class hierarchies and module organization.

    - **Radial**: A circular layout with the most connected nodes in the center.
      Good for identifying central components in your codebase.

    - **Sankey**: A flow diagram showing dependencies between components.
      Helpful for understanding data flow and module dependencies.

    ## Usage Tips

    - In the visualization, you can:
      - Zoom in/out with the mouse wheel
      - Click and drag nodes to reposition them
      - Hover over nodes to see details
      - Click on nodes to highlight connections
      - Search for specific nodes using the search box

    - For large codebases, use filters to focus on specific parts of the graph

    - The dark theme works best for presentations, while the light theme is better for documentation

    ## Related Commands

    - `codestory query`: Run Cypher queries to explore the graph
    - `codestory ask`: Ask natural language questions about the code
    """

    console.print(
        Panel(
            Markdown(help_text),
            title="Visualization Help",
            border_style="blue",
            expand=False,
        )
    )
