"""
Command modules for the Code Story CLI.
"""

import os
import sys
from importlib import import_module
from typing import Any, Dict, Type

# List of command modules to import
_COMMANDS = [
    "ask",
    "config",
    "ingest",
    "query",
    "service",
    "ui",
    "visualize",
]

# Dictionary to store imported modules
_imported_modules = {}


def _import_module(name: str) -> Any:
    """
    Import a command module.

    Args:
        name: Name of the module to import

    Returns:
        Imported module
    """
    if name not in _imported_modules:
        module_path = f"codestory.cli.commands.{name}"
        _imported_modules[name] = import_module(module_path)

    return _imported_modules[name]


# Import all command modules
for cmd in _COMMANDS:
    try:
        globals()[cmd] = _import_module(cmd)
    except ImportError as e:
        print(f"Error importing command module {cmd}: {e}", file=sys.stderr)

__all__ = _COMMANDS
