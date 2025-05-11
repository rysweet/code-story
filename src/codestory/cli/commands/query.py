"""
Query commands for the Code Story CLI.
"""

import json
from typing import Dict, Any, Optional, List

import click
# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    import click as rich_click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ..client import ServiceClient, ServiceError


@click.command(help="Execute a Cypher query or MCP tool call.")
@click.argument("query_string")
@click.option("--json", "output_json", is_flag=True, help="Output raw JSON.")
@click.option("--param", "-p", multiple=True, help="Query parameters in KEY=VALUE format.")
@click.pass_context
def query(
    ctx: click.Context, 
    query_string: str, 
    output_json: bool = False,
    param: List[str] = None,
) -> None:
    """
    Execute a Cypher query or MCP tool call.
    
    QUERY_STRING is the Cypher query or MCP tool call to execute.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]
    
    # Parse parameters
    parameters = {}
    if param:
        for p in param:
            try:
                key, value = p.split("=", 1)
                # Try to parse value as JSON
                try:
                    parameters[key] = json.loads(value)
                except json.JSONDecodeError:
                    parameters[key] = value
            except ValueError:
                console.print(f"[bold red]Error:[/] Invalid parameter format: {p}")
                console.print("Parameters must be in KEY=VALUE format.")
                return
    
    # Execute query
    console.print(f"Executing query: [cyan]{query_string}[/]")
    if parameters:
        console.print(f"With parameters: [blue]{parameters}[/]")
    
    try:
        result = client.execute_query(query_string, parameters)
        
        if output_json:
            # Output raw JSON
            console.print(json.dumps(result, indent=2))
            return
        
        # Output formatted result
        _display_query_result(console, result)
    
    except ServiceError as e:
        console.print(f"[bold red]Query failed:[/] {str(e)}")


def _display_query_result(console: Console, result: Dict[str, Any]) -> None:
    """
    Display formatted query results.
    
    Args:
        console: Rich console
        result: Query result data
    """
    # Handle different result types
    if "records" in result:
        # Cypher query result
        records = result["records"]
        
        if not records:
            console.print("[yellow]No results found.[/]")
            return
        
        # Get columns from first record
        columns = list(records[0].keys())
        
        # Create table
        table = Table(title="Query Results")
        
        for column in columns:
            table.add_column(column, style="cyan")
        
        # Add rows
        for record in records:
            row = []
            for column in columns:
                value = record.get(column)
                row.append(_format_value(value))
            
            table.add_row(*row)
        
        console.print(table)
        console.print(f"[green]{len(records)} record(s) returned[/]")
    
    elif "results" in result:
        # MCP tool call result
        results = result["results"]
        
        if isinstance(results, list):
            # List of items
            for i, item in enumerate(results, 1):
                panel = Panel(
                    _format_object(item),
                    title=f"Result {i}",
                    border_style="cyan"
                )
                console.print(panel)
        else:
            # Single result object
            panel = Panel(
                _format_object(results),
                title="Result",
                border_style="cyan"
            )
            console.print(panel)
    
    elif "error" in result:
        # Error result
        console.print(f"[bold red]Error:[/] {result['error']}")
    
    else:
        # Unknown result format
        console.print(json.dumps(result, indent=2))


def _format_value(value: Any) -> str:
    """
    Format a value for display in a table cell.
    
    Args:
        value: Value to format
        
    Returns:
        Formatted string representation
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2)
    elif value is None:
        return "[dim]NULL[/]"
    else:
        return str(value)


def _format_object(obj: Dict[str, Any]) -> str:
    """
    Format an object for display in a panel.
    
    Args:
        obj: Object to format
        
    Returns:
        Formatted string representation
    """
    if isinstance(obj, dict):
        if "code" in obj:
            # Format code with syntax highlighting
            lang = obj.get("language", "text")
            return Syntax(obj["code"], lang, theme="monokai", line_numbers=True)
        
        # Format as JSON
        return json.dumps(obj, indent=2)
    else:
        return str(obj)