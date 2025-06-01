"""Command-line interface for configuration management."""
import json
import sys
from typing import Any

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from .exceptions import ConfigurationError, SettingNotFoundError
from .export import create_env_template, export_to_json, export_to_toml, settings_to_dict
from .settings import get_settings, refresh_settings
from .writer import get_config_value, update_config

app = typer.Typer(name='config', help='Configuration management commands', no_args_is_help=True)
console = Console()

@app.command('get')
def get_setting(setting_path: str=typer.Argument(..., help="Setting path in dot notation (e.g., 'neo4j.uri')"), format: str=typer.Option('plain', '--format', '-f', help='Output format (plain, json, yaml)')) -> None:
    """Get a configuration setting value."""
    try:
        value = get_config_value(setting_path)
        if format == 'plain':
            console.print(value)
        elif format == 'json':
            json_data = {setting_path: value}
            console.print(json.dumps(json_data, indent=2))
        else:
            console.print(f'{setting_path} = {value}')
    except SettingNotFoundError as e:
        console.print(f'[bold red]Error:[/] {e.message}')
        sys.exit(1)
    except Exception as e:
        console.print(f'[bold red]Error:[/] {e!s}')
        sys.exit(1)

@app.command('set')
def set_setting(setting_path: str=typer.Argument(..., help="Setting path in dot notation (e.g., 'neo4j.uri')"), value: str=typer.Argument(..., help='Value to set'), persist: str=typer.Option('env', '--persist', '-p', help='Where to persist the change (env, toml, none)')) -> None:
    """Set a configuration setting value."""
    try:
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value
        persist_to = None if persist.lower() == 'none' else persist.lower()
        update_config(setting_path, parsed_value, persist_to=persist_to)
        console.print(f'[bold green]Success:[/] Updated {setting_path} = {parsed_value}')
        if persist_to:
            console.print(f'Change persisted to {persist_to}')
        else:
            console.print('[yellow]Note:[/] Change is in-memory only and will be lost when the application restarts')
    except ConfigurationError as e:
        console.print(f'[bold red]Error:[/] {e.message}')
        if e.details:
            console.print(e.details)
        sys.exit(1)
    except Exception as e:
        console.print(f'[bold red]Error:[/] {e!s}')
        sys.exit(1)

@app.command('list')
def list_settings(section: str | None=typer.Option(None, '--section', '-s', help="Section to list (e.g., 'neo4j')"), format: str=typer.Option('table', '--format', '-f', help='Output format (table, json, toml)'), include_secrets: bool=typer.Option(False, '--include-secrets', help='Include secret values (default: redacted)')) -> None:
    """List configuration settings."""
    settings = get_settings()
    settings_dict = settings_to_dict(settings, redact_secrets=not include_secrets)
    if section:
        if section not in settings_dict:
            console.print(f"[bold red]Error:[/] Section '{section}' not found")
            valid_sections = list(settings_dict.keys())
            console.print(f"Valid sections: {', '.join(valid_sections)}")
            sys.exit(1)
        settings_dict = {section: settings_dict[section]}
    if format == 'json':
        console.print(json.dumps(settings_dict, indent=2))
    elif format == 'toml':
        console.print(export_to_toml(redact_secrets=not include_secrets))
    else:
        for section_name, section_values in settings_dict.items():
            table = Table(title=f'[bold]{section_name}[/]')
            table.add_column('Setting', style='cyan')
            table.add_column('Value', style='green')
            if isinstance(section_values, dict):
                for key, value in section_values.items():
                    if isinstance(value, dict):
                        value_str = json.dumps(value, indent=2)
                        table.add_row(key, value_str)
                    else:
                        table.add_row(key, str(value))
            else:
                table.add_row('value', str(section_values))
            console.print(table)
            console.print('')

@app.command('export')
def export_config(format: str=typer.Option('env', '--format', '-f', help='Output format (env, json, toml)'), output: str | None=typer.Option(None, '--output', '-o', help='Output file path (default: stdout)'), include_secrets: bool=typer.Option(False, '--include-secrets', help='Include secret values (default: redacted)')) -> None:
    """Export configuration to various formats."""
    try:
        if format == 'env':
            result = create_env_template(output_path=output)
            if not output:
                console.print(result)
        elif format == 'json':
            result = export_to_json(output_path=output, redact_secrets=not include_secrets)
            if not output:
                parsed = json.loads(result)
                syntax = Syntax(json.dumps(parsed, indent=2), 'json', theme='monokai', line_numbers=True)
                console.print(syntax)
        elif format == 'toml':
            result = export_to_toml(output_path=output, redact_secrets=not include_secrets)
            if not output:
                syntax = Syntax(result, 'toml', theme='monokai', line_numbers=True)
                console.print(syntax)
        else:
            console.print(f'[bold red]Error:[/] Unknown format: {format}')
            console.print('Valid formats: env, json, toml')
            sys.exit(1)
        if output:
            console.print(f'[bold green]Success:[/] Configuration exported to {output}')
    except Exception as e:
        console.print(f'[bold red]Error:[/] {e!s}')
        sys.exit(1)

@app.command('refresh')
def refresh_config() -> None:
    """Refresh configuration from all sources."""
    try:
        refresh_settings()
        console.print('[bold green]Success:[/] Configuration refreshed from all sources')
    except Exception as e:
        console.print(f'[bold red]Error:[/] {e!s}')
        sys.exit(1)
if __name__ == '__main__':
    app()