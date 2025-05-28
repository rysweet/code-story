"""Query commands for the Code Story CLI."""

import contextlib
import json
from typing import Any

import click

# Import rich_click if available, otherwise create a stub
with contextlib.suppress(ImportError):
    pass
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ..client import ServiceClient, ServiceError
from ..require_service_available import require_service_available


@click.group(help="Execute queries and explore the Code Story graph.")
def query() -> None:
    """Command group for query operations."""
    pass


@query.command(name="run", help="Execute a Cypher query or MCP tool call.")
@click.argument("query_string")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv", "tree", "auto"]),
    default="auto",
    help="Output format for the query results.",
)
@click.option("--output", "-o", type=click.Path(), help="Save results to a file.")
@click.option("--param", "-p", multiple=True, help="Query parameters in KEY=VALUE format.")
@click.option("--color/--no-color", default=True, help="Enable/disable colored output.")
@click.option("--limit", "-n", type=int, help="Limit number of results.")
@click.pass_context
def run_query(
    ctx: click.Context,
    query_string: str,
    format: str = "auto",
    output: str | None = None,
    param: list[str] | None = None,
    color: bool = True,
    limit: int | None = None,
) -> None:
    """
    Execute a Cypher query or MCP tool call.

    QUERY_STRING is the Cypher query or MCP tool call to execute.
    """
    require_service_available()

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

    # Determine if query is Cypher or MCP
    query_type = (
        "cypher"
        if query_string.strip()
        .upper()
        .startswith(("MATCH", "CREATE", "MERGE", "RETURN", "DELETE", "REMOVE", "SET", "WITH"))
        else "mcp"
    )

    # Execute query
    if not output:  # Only show query text when not outputting to file
        console.print(f"Executing [magenta]{query_type}[/] query: [cyan]{query_string}[/]")
        if parameters:
            console.print(f"With parameters: [blue]{parameters}[/]")

    try:
        # Add limit to Cypher query if specified and is a Cypher query
        if limit is not None and query_type == "cypher" and "LIMIT" not in query_string.upper():
            # Simple regex-free approach - might need improvement for complex queries
            if "RETURN" in query_string:
                parts = query_string.split("RETURN")
                query_string = f"{parts[0]} RETURN {parts[1]} LIMIT {limit}"
            else:
                query_string = f"{query_string} LIMIT {limit}"

        result = client.execute_query(query_string, parameters)

        # Determine output format if auto
        if format == "auto":
            if "records" in result and isinstance(result["records"], list):
                format = "table"
            elif "results" in result and isinstance(result["results"], dict):
                format = "tree"
            else:
                format = "json"

        # Output results
        if format == "json":
            output_text = json.dumps(result, indent=2)
            if not output:
                console.print(output_text)

        elif format == "csv":
            output_text = _results_to_csv(result)
            if not output:
                console.print(output_text)

        elif format == "tree":
            if not output:
                _display_results_as_tree(console, result, color)
            else:
                # Can't save tree to file, fallback to JSON
                output_text = json.dumps(result, indent=2)

        else:  # table
            if not output:
                _display_query_result(console, result, color, limit)
            else:
                # Can't save table to file, fallback to CSV
                output_text = _results_to_csv(result)

        # Save to file if requested
        if output:
            with open(output, "w") as f:
                f.write(output_text)
            console.print(f"Results saved to [green]{output}[/]")

            # Print summary
            if "records" in result:
                record_count = len(result["records"])
                console.print(f"[green]{record_count} record(s) written to file[/]")

    except ServiceError as e:
        console.print(f"[bold red]Query failed:[/] {e!s}")


@query.command(name="explore", help="Interactive query explorer for the graph.")
@click.option("--limit", "-n", type=int, default=10, help="Default limit for queries.")
@click.pass_context
def explore_query(ctx: click.Context, limit: int = 10) -> None:
    """Launch an interactive query explorer."""
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # Start with a summary of the graph
    console.print("[bold]Graph Explorer[/]")
    console.print("Running initial queries to explore the graph structure...")

    # Count nodes by type
    try:
        node_count_query = (
            "MATCH (n) RETURN labels(n) as type, count(n) as count ORDER BY count DESC"
        )
        result = client.execute_query(node_count_query)

        if result.get("records"):
            table = Table("Node Types in Graph")
            table.add_column("Type", style="cyan")
            table.add_column("Count", style="green", justify="right")

            for record in result["records"]:
                node_type = record.get("type", ["Unknown"])[0]
                count = record.get("count", 0)
                table.add_row(node_type, str(count))

            console.print(table)

        # Get sample of nodes for each main type
        node_types = [r.get("type", ["Unknown"])[0] for r in result["records"][:5]]

        for node_type in node_types:
            sample_query = f"MATCH (n:{node_type}) RETURN n LIMIT {limit}"
            console.print(f"\n[bold]Sample of [cyan]{node_type}[/] nodes:[/]")

            try:
                sample_result = client.execute_query(sample_query)
                _display_query_result(console, sample_result, True, limit)
            except ServiceError:
                console.print(f"[yellow]Could not query {node_type} nodes.[/]")

        # Show relationship types
        rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
        rel_result = client.execute_query(rel_query)

        if rel_result.get("records"):
            table = Table("Relationship Types in Graph")
            table.add_column("Type", style="magenta")
            table.add_column("Count", style="green", justify="right")

            for record in rel_result["records"]:
                rel_type = record.get("type", "Unknown")
                count = record.get("count", 0)
                table.add_row(rel_type, str(count))

            console.print(table)

        # Show common query examples
        console.print("\n[bold]Example queries you can run:[/]")
        console.print(
            '* [cyan]codestory query run "MATCH (n:Class) RETURN n.name, n.path LIMIT 5"[/]'
        )
        console.print(
            '* [cyan]codestory query run "MATCH (n)-[r:IMPORTS]->(m) '
            'RETURN n.name, m.name LIMIT 5"[/]'
        )
        console.print(
            "* [cyan]codestory query run \"MATCH (n:Function) WHERE n.name CONTAINS "
            "'main' RETURN n LIMIT 5\"[/]"
        )

    except ServiceError as e:
        console.print(f"[bold red]Query failed:[/] {e!s}")


@query.command(name="export", help="Export query results to a file.")
@click.argument("query_string")
@click.argument("output_path", type=click.Path())
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Output format.",
)
@click.option("--param", "-p", multiple=True, help="Query parameters in KEY=VALUE format.")
@click.pass_context
def export_query(
    ctx: click.Context,
    query_string: str,
    output_path: str,
    format: str = "json",
    param: list[str] | None = None,
) -> None:
    """
    Export query results to a file.

    QUERY_STRING is the Cypher query or MCP tool call to execute.
    OUTPUT_PATH is the path to save the results to.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # Parse parameters
    parameters = {}
    if param:
        for p in param:
            try:
                key, value = p.split("=", 1)
                try:
                    parameters[key] = json.loads(value)
                except json.JSONDecodeError:
                    parameters[key] = value
            except ValueError:
                console.print(f"[bold red]Error:[/] Invalid parameter format: {p}")
                return

    try:
        console.print(f"Executing query and exporting results to [cyan]{output_path}[/]...")
        result = client.execute_query(query_string, parameters)

        with open(output_path, "w") as f:
            if format == "json":
                json.dump(result, f, indent=2)
            else:  # csv
                f.write(_results_to_csv(result))

        # Print summary
        if "records" in result:
            record_count = len(result["records"])
            console.print(f"[green]{record_count} record(s) exported to [cyan]{output_path}[/]")

    except ServiceError as e:
        console.print(f"[bold red]Export failed:[/] {e!s}")
    except OSError as e:
        console.print(f"[bold red]Failed to write file:[/] {e!s}")


def _display_query_result(
    console: Console,
    result: dict[str, Any],
    color: bool = True,
    limit: int | None = None,
) -> None:
    """
    Display formatted query results.

    Args:
        console: Rich console
        result: Query result data
        color: Whether to use colored output
        limit: Maximum number of records to display
    """
    # Handle different result types
    if "records" in result:
        # Cypher query result
        records = result["records"]

        if not records:
            console.print("[yellow]No results found.[/]" if color else "No results found.")
            return

        # Apply limit if specified
        if limit is not None and len(records) > limit:
            total_records = len(records)
            records = records[:limit]
            truncated = True
        else:
            total_records = len(records)
            truncated = False

        # Get columns from first record
        columns = list(records[0].keys())

        # Create table
        table = Table("Query Results", highlight=color, border_style="cyan" if color else None)

        for column in columns:
            table.add_column(column, style="cyan" if color else None)

        # Add rows
        for record in records:
            row = []
            for column in columns:
                value = record.get(column)
                row.append(_format_value(value, color))

            table.add_row(*row)

        console.print(table)

        # Show record count
        if truncated:
            if color:
                console.print(
                    f"[green]{len(records)} of {total_records} record(s) shown[/] "
                    f"([yellow]limit={limit}[/])"
                )
            else:
                console.print(f"{len(records)} of {total_records} record(s) shown (limit={limit})")
        else:
            if color:
                console.print(f"[green]{total_records} record(s) returned[/]")
            else:
                console.print(f"{total_records} record(s) returned")

    elif "results" in result:
        # MCP tool call result
        results = result["results"]

        if isinstance(results, list):
            # List of items
            if limit is not None and len(results) > limit:
                results = results[:limit]
                if color:
                    console.print(f"[yellow]Showing {limit} of {len(results)} results[/]")
                else:
                    console.print(f"Showing {limit} of {len(results)} results")

            for i, item in enumerate(results, 1):
                panel = Panel(
                    _format_object(item, color),
                    title=f"Result {i}",
                    border_style="cyan" if color else None,
                )
                console.print(panel)
        else:
            # Single result object
            panel = Panel(
                _format_object(results, color),
                title="Result",
                border_style="cyan" if color else None,
            )
            console.print(panel)

    elif "error" in result:
        # Error result
        if color:
            console.print(f"[bold red]Error:[/] {result['error']}")
        else:
            console.print(f"Error: {result['error']}")

    else:
        # Unknown result format
        console.print(json.dumps(result, indent=2))


def _display_results_as_tree(console: Console, result: dict[str, Any], color: bool = True) -> None:
    """
    Display query results as a tree.

    Args:
        console: Rich console
        result: Query result data
        color: Whether to use colored output
    """
    from rich.tree import Tree

    if "records" in result:
        # Cypher query results
        records = result["records"]

        if not records:
            console.print("[yellow]No results found.[/]" if color else "No results found.")
            return

        tree = Tree("Query Results", style="bold cyan" if color else None)

        for i, record in enumerate(records, 1):
            record_tree = tree.add(f"Record {i}")

            for key, value in record.items():
                if isinstance(value, dict):
                    # Node or relationship
                    node_tree = record_tree.add(key, style="magenta" if color else None)
                    for prop_key, prop_value in value.items():
                        node_tree.add(f"{prop_key}: {_format_value(prop_value, color)}")
                elif isinstance(value, list):
                    # List value
                    list_tree = record_tree.add(key, style="blue" if color else None)
                    for j, item in enumerate(value):
                        list_tree.add(f"[{j}] {_format_value(item, color)}")
                else:
                    # Simple value
                    record_tree.add(f"{key}: {_format_value(value, color)}")

        console.print(tree)

    elif "results" in result:
        # MCP tool call results
        results = result["results"]

        tree = Tree("Query Results", style="bold cyan" if color else None)

        if isinstance(results, list):
            for i, item in enumerate(results, 1):
                item_tree = tree.add(f"Result {i}")
                _add_result_to_tree(item_tree, item, color)
        else:
            _add_result_to_tree(tree, results, color)

        console.print(tree)

    else:
        # Unknown format
        console.print(json.dumps(result, indent=2))


def _add_result_to_tree(tree: Any, item: Any, color: bool = True) -> None:
    """Add a result item to a tree."""
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, dict):
                subtree = tree.add(key, style="magenta" if color else None)
                _add_result_to_tree(subtree, value, color)
            elif isinstance(value, list):
                subtree = tree.add(key, style="blue" if color else None)
                for i, list_item in enumerate(value):
                    list_subtree = subtree.add(f"[{i}]")
                    _add_result_to_tree(list_subtree, list_item, color)
            else:
                tree.add(f"{key}: {_format_value(value, color)}")
    elif isinstance(item, list):
        for i, list_item in enumerate(item):
            list_tree = tree.add(f"[{i}]")
            _add_result_to_tree(list_tree, list_item, color)
    else:
        tree.add(_format_value(item, color))


def _results_to_csv(result: dict[str, Any]) -> str:
    """
    Convert query results to CSV format.

    Args:
        result: Query result data

    Returns:
        CSV formatted string
    """
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)

    if result.get("records"):
        records = result["records"]

        # Get columns from first record
        columns = list(records[0].keys())

        # Write header
        writer.writerow(columns)

        # Write records
        for record in records:
            row = []
            for column in columns:
                value = record.get(column)
                if isinstance(value, dict | list):
                    # Serialize complex values
                    row.append(json.dumps(value))
                elif value is None:
                    row.append("")
                else:
                    row.append(str(value))

            writer.writerow(row)

    elif "results" in result:
        # MCP tool call results
        results = result["results"]

        if isinstance(results, list) and results and isinstance(results[0], dict):
            # Try to extract common keys for a table
            columns = set()
            for item in results:
                if isinstance(item, dict):
                    columns.update(item.keys())

            columns = sorted(columns)

            # Write header
            writer.writerow(columns)

            # Write rows
            for item in results:
                if isinstance(item, dict):
                    row = []
                    for column in columns:
                        value = item.get(column)
                        if isinstance(value, dict | list):
                            row.append(json.dumps(value))
                        elif value is None:
                            row.append("")
                        else:
                            row.append(str(value))

                    writer.writerow(row)
        else:
            # Can't format as CSV
            writer.writerow(["results"])
            writer.writerow([json.dumps(results)])

    else:
        # Can't format as CSV
        writer.writerow(["result"])
        writer.writerow([json.dumps(result)])

    return output.getvalue()


def _format_value(value: Any, color: bool = True) -> str:
    """
    Format a value for display.

    Args:
        value: Value to format
        color: Whether to use colored output

    Returns:
        Formatted string representation
    """
    if isinstance(value, dict | list):
        return json.dumps(value, indent=2)
    elif value is None:
        return "[dim]NULL[/]" if color else "NULL"
    else:
        return str(value)


def _format_object(obj: Any, color: bool = True) -> str:
    """
    Format an object for display in a panel.

    Args:
        obj: Object to format
        color: Whether to use colored output

    Returns:
        Formatted string representation
    """
    if isinstance(obj, dict):
        if "code" in obj:
            # Format code with syntax highlighting
            lang = obj.get("language", "text")
            if color:
                return Syntax(obj["code"], lang, theme="monokai", line_numbers=True)
            else:
                return obj["code"]

        # Format as JSON
        return json.dumps(obj, indent=2)
    elif isinstance(obj, list):
        # Format as JSON
        return json.dumps(obj, indent=2)
    else:
        return str(obj)
