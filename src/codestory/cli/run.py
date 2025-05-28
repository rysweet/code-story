#!/usr/bin/env python3
"""
Entry point for Code Story CLI.

This module provides a clean entry point for the CLI without circular imports.
It imports the main function from the main module and calls it if the script
is run directly.
"""

from typing import Any
import sys

from codestory.cli.main import main


def run() -> Any:
    """Run the CLI application with proper exit code."""
    return main()


if __name__ == "__main__":
    sys.exit(run())
