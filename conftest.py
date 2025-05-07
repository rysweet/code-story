"""Pytest configuration for Code Story project.

This file sets the default fixture loop scope for pytest-asyncio to 'function'.
"""

pytest_plugins = []

def pytest_configure(config):
    """Configure pytest to set the default asyncio fixture loop scope to 'function'."""
    config.option.asyncio_default_fixture_loop_scope = "function"
