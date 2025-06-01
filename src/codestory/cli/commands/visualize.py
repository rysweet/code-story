from typing import Any

'Visualization commands for the Code Story CLI.'
import contextlib
import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click

with contextlib.suppress(ImportError):
    pass
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..require_service_available import require_service_available

if TYPE_CHECKING:
    from rich.console import Console

    from ..client import ServiceClient

@click.group(help='Generate and manage visualizations of the Code Story graph.')
def visualize() -> None:
    """Command group for visualization operations."""
    pass

@visualize.command(name='generate', help='Generate a visualization of the Code Story graph.')
@click.option('--output', '-o', type=click.Path(), help='Output file path. If not specified, a file will be created in the current directory.')
@click.option('--open-browser/--no-browser', 'open_browser', default=True, help='Open the visualization in a browser automatically.')
@click.option('--type', 'viz_type', type=click.Choice(['force', 'hierarchy', 'radial', 'sankey']), default='force', help='Type of visualization to generate.')
@click.option('--theme', type=click.Choice(['light', 'dark', 'auto']), default='auto', help='Color theme for the visualization.')
@click.option('--title', help='Custom title for the visualization.')
@click.pass_context
def generate(ctx: click.Context, output: str | None=None, open_browser: bool=True, viz_type: str='force', theme: str='auto', title: str | None=None) -> None:
    """Generate a visualization of the Code Story graph."""
    require_service_available()
    client: ServiceClient = ctx.obj['client']
    console: Console = ctx.obj['console']
    output_path = None
    with Progress(SpinnerColumn(), TextColumn('[bold green]Generating graph visualization...'), console=console, transient=True) as progress:
        progress.add_task('Generating', total=None)
        try:
            params: dict[str, Any] = {'type': viz_type, 'theme': theme}
            if title:
                params['title'] = title
            html_content = client.generate_visualization(params)
            if output:
                output_path = os.path.abspath(output)
            else:
                timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                output_path = os.path.abspath(f'codestory-graph-{timestamp}.html')
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(html_content)
        except Exception as e:
            console.print(f'[bold red]Error:[/] {e!s}')
            console.print('[bold red]The Code Story service must be running.[/]')
            console.print('Starting service automatically...')
            import subprocess
            import time
            try:
                subprocess.Popen(['codestory', 'service', 'start'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                service_started = False
                for _ in range(10):
                    time.sleep(1)
                    try:
                        client = ctx.obj['client']
                        html_content = client.generate_visualization(params)
                        service_started = True
                        break
                    except Exception:
                        console.print('[yellow]Waiting for service to start...[/]')
                if not service_started:
                    raise Exception('Failed to start the service automatically')
                if output:
                    output_path = os.path.abspath(output)
                else:
                    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                    output_path = os.path.abspath(f'codestory-graph-{timestamp}.html')
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, 'w') as f:
                    f.write(html_content)
            except Exception as start_error:
                console.print(f'[bold red]Failed to start service:[/] {start_error!s}')
                console.print('[bold red]Please start the service manually:[/] codestory service start')
                return
    if output_path:
        console.print(Panel.fit(f'[bold green]Visualization generated successfully![/]\n\n📊 File saved to: [cyan]{output_path}[/]\n🔍 Type: [magenta]{viz_type}[/]\n🎨 Theme: [magenta]{theme}[/]', title='Graph Visualization', border_style='green'))
        if open_browser:
            webbrowser.open(f'file://{output_path}')
            console.print('[dim]Visualization opened in browser...[/]')
        else:
            console.print('\nTo view the visualization, open the HTML file in a web browser.')
            console.print(f'Or run: [cyan]open {output_path}[/]')

@visualize.command(name='list', help='List previously generated visualizations.')
@click.option('--limit', '-n', type=int, default=10, help='Maximum number of visualizations to list.')
@click.pass_context
def list_visualizations(ctx: click.Context, limit: int=10) -> None:
    """List previously generated visualizations."""
    console: Console = ctx.obj['console']
    pattern = 'codestory-graph-*.html'
    files = sorted(Path('.').glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        console.print('[yellow]No visualizations found in the current directory.[/]')
        console.print('Generate one with: [cyan]codestory visualize generate[/]')
        return
    files = files[:limit]
    console.print('[bold]Recently generated visualizations:[/]')
    for i, file in enumerate(files, 1):
        size = os.path.getsize(file) / 1024
        modified = datetime.fromtimestamp(os.path.getmtime(file))
        console.print(f"{i}. [cyan]{file}[/] [{modified.strftime('%Y-%m-%d %H:%M:%S')}] [{size:.1f} KB]")

@visualize.command(name='open', help='Open a previously generated visualization.')
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
def open_visualization(ctx: click.Context, path: str) -> None:
    """Open a previously generated visualization."""
    console: Console = ctx.obj['console']
    if not path.lower().endswith('.html'):
        console.print('[bold red]Error:[/] File must be an HTML file.')
        return
    abs_path = os.path.abspath(path)
    console.print(f'Opening [cyan]{abs_path}[/] in browser...')
    webbrowser.open(f'file://{abs_path}')

@visualize.command(name='help', help='Show information about visualization features.')
@click.pass_context
def viz_help(ctx: click.Context) -> None:
    """Show information about visualization features."""
    console: Console = ctx.obj['console']
    help_text = '\n    # Code Story Graph Visualization\n\n    The visualization feature allows you to create interactive, browser-based visualizations\n    of your code graph. These visualizations help you understand the structure and relationships\n    in your codebase.\n\n    ## Visualization Types\n\n    - **Force** (default): A force-directed graph where nodes repel each other \n      and edges act like springs.\n      Best for showing relationships between components.\n\n    - **Hierarchy**: A tree-like visualization showing inheritance and containment relationships.\n      Useful for understanding class hierarchies and module organization.\n\n    - **Radial**: A circular layout with the most connected nodes in the center.\n      Good for identifying central components in your codebase.\n\n    - **Sankey**: A flow diagram showing dependencies between components.\n      Helpful for understanding data flow and module dependencies.\n\n    ## Usage Tips\n\n    - In the visualization, you can:\n      - Zoom in/out with the mouse wheel\n      - Click and drag nodes to reposition them\n      - Hover over nodes to see details\n      - Click on nodes to highlight connections\n      - Search for specific nodes using the search box\n\n    - For large codebases, use filters to focus on specific parts of the graph\n\n    - The dark theme works best for presentations, while the light theme is better for documentation\n\n    ## Related Commands\n\n    - `codestory query`: Run Cypher queries to explore the graph\n    - `codestory ask`: Ask natural language questions about the code\n    '
    console.print(Panel(Markdown(help_text), title='Visualization Help', border_style='blue', expand=False))