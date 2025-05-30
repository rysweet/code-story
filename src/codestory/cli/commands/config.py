"""Configuration commands for the Code Story CLI."""

import contextlib
import json
import os
import sys
import tempfile
from typing import Any

import click

# Import rich_click if available, otherwise create a stub
with contextlib.suppress(ImportError):
    pass
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.tree import Tree

from ..client import ServiceClient, ServiceError


@click.group(help="Manage Code Story configuration.")
def config() -> Any:
    """Command group for configuration operations."""
    pass


@config.command(name="show", help="Show current configuration.")
@click.option("--sensitive", is_flag=True, help="Include sensitive values.")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "tree"]),
    default="table",
    help="Output format.",
)
@click.pass_context
def show_config(ctx: click.Context, sensitive: bool = False, format: str = "table") -> None:
    """Show current configuration."""
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Getting current configuration...")

    try:
        config_data = client.get_config(include_sensitive=sensitive)

        if format == "json":
            # Output raw JSON
            console.print(json.dumps(config_data, indent=2))
        elif format == "tree":
            # Output as tree
            tree = Tree("[bold]Configuration[/]")
            _build_config_tree(tree, config_data)
            console.print(tree)
        else:
            # Output as table
            _display_config_table(console, config_data, sensitive)

    except ServiceError as e:
        console.print(f"[bold red]Failed to get configuration:[/] {e!s}")
        sys.exit(1)


@config.command(name="set", help="Update configuration values.")
@click.argument("key_value_pairs", nargs=-1)
@click.option("--no-confirm", is_flag=True, help="Don't ask for confirmation.")
@click.pass_context
def set_config(ctx: click.Context, key_value_pairs: list[str], no_confirm: bool = False) -> None:
    """
    Update configuration values.

    KEY_VALUE_PAIRS are the configuration keys and values to update in the format KEY=VALUE.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # Parse key-value pairs
    updates = {}
    for pair in key_value_pairs:
        try:
            key, value = pair.split("=", 1)
            # Try to parse value as JSON
            try:
                updates[key] = json.loads(value)
            except json.JSONDecodeError:
                updates[key] = value
        except ValueError:
            console.print(f"[bold red]Error:[/] Invalid format: {pair}")
            console.print("Key-value pairs must be in the format KEY=VALUE.")
            return

    if not updates:
        console.print("[yellow]No updates specified.[/]")
        return

    # Show what will be updated
    console.print("The following configuration values will be updated:")
    for key, value in updates.items():
        console.print(f"  [cyan]{key}[/] = [green]{value}[/]")

    # Confirm updates
    if not no_confirm and not Confirm.ask("Proceed with updates?"):
        console.print("[yellow]Update cancelled.[/]")
        return

    # Apply updates
    try:
        console.print("Updating configuration...")
        result = client.update_config(updates)

        console.print("[green]Configuration updated successfully.[/]")

        # Show updated configuration
        _display_config_table(console, result, sensitive=False)

    except ServiceError as e:
        console.print(f"[bold red]Failed to update configuration:[/] {e!s}")
        sys.exit(1)


@config.command(name="edit", help="Edit configuration in an editor.")
@click.pass_context
def edit_config(ctx: click.Context) -> None:
    """Edit configuration in an editor."""
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # Get current configuration
    try:
        config_data = client.get_config(include_sensitive=True)
    except ServiceError as e:
        console.print(f"[bold red]Failed to get configuration:[/] {e!s}")
        sys.exit(1)

    # Create temporary file with configuration
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False) as temp_file:
        json.dump(config_data, temp_file, indent=2)
        temp_file_path = temp_file.name

    # Open editor
    editor = os.environ.get("EDITOR", "vim")
    console.print(f"Opening configuration in {editor}...")

    try:
        click.edit(filename=temp_file_path, editor=editor)

        # Read updated configuration
        with open(temp_file_path) as f:
            try:
                updated_config = json.load(f)
            except json.JSONDecodeError as e:
                console.print(f"[bold red]Error parsing JSON:[/] {e!s}")
                console.print("Configuration not updated.")
                return

        # Apply updates
        console.print("Updating configuration...")
        client.update_config(updated_config)

        console.print("[green]Configuration updated successfully.[/]")

        # Clean up
        os.unlink(temp_file_path)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        console.print("Configuration not updated.")

        # Clean up
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def _display_config_table(
    console: Console, config_data: dict[str, Any], sensitive: bool = False
) -> None:
    """
    Display configuration as a table.

    Args:
        console: Rich console
        config_data: Configuration data
        sensitive: Whether to show sensitive values
    """
    table = Table(title="Configuration", show_lines=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Type", style="magenta")

    # Flatten config data for table display
    flat_config = _flatten_dict(config_data)

    for key, value in sorted(flat_config.items()):
        # Check if sensitive
        is_sensitive = "password" in key.lower() or "secret" in key.lower() or "key" in key.lower()

        if is_sensitive and not sensitive:
            # Mask sensitive values
            formatted_value = "********"
        else:
            # Format value
            formatted_value = _format_value_for_table(value)

        # Get value type
        value_type = type(value).__name__ if value is not None else "None"

        table.add_row(key, formatted_value, value_type)

    console.print(table)


def _flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """
    Flatten a nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key for nested items
        sep: Separator for keys

    Returns:
        Flattened dictionary
    """
    items: list[Any] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


def _build_config_tree(tree: Tree, config_data: dict[str, Any], sensitive: bool = False) -> None:
    """
    Build a tree representation of configuration data.

    Args:
        tree: Rich tree to add nodes to
        config_data: Configuration data
        sensitive: Whether to show sensitive values
    """
    for key, value in sorted(config_data.items()):
        if isinstance(value, dict):
            # Create subtree for nested values
            subtree = tree.add(f"[bold blue]{key}[/]")
            _build_config_tree(subtree, value, sensitive)
        else:
            # Check if sensitive
            is_sensitive = (
                "password" in key.lower() or "secret" in key.lower() or "key" in key.lower()
            )

            if is_sensitive and not sensitive:
                # Mask sensitive values
                formatted_value = "********"
            else:
                # Format value
                formatted_value = _format_value_for_tree(value)

            tree.add(f"[cyan]{key}[/]: {formatted_value}")


def _format_value_for_table(value: Any) -> str:
    """
    Format a value for display in a table cell.

    Args:
        value: Value to format

    Returns:
        Formatted string representation
    """
    if isinstance(value, dict | list):
        return json.dumps(value)
    elif value is None:
        return "[dim]null[/]"
    elif isinstance(value, bool):
        return str(value).lower()
    else:
        return str(value)


def _format_value_for_tree(value: Any) -> str:
    """
    Format a value for display in a tree node.

    Args:
        value: Value to format

    Returns:
        Formatted string representation
    """
    if isinstance(value, dict | list):
        return f"[yellow]{json.dumps(value)}[/]"
    elif value is None:
        return "[dim]null[/]"
    elif isinstance(value, bool):
        return f"[green]{str(value).lower()}[/]"
    elif isinstance(value, int | float):
        return f"[green]{value}[/]"
    else:
        return f'[green]"{value}"[/]'
