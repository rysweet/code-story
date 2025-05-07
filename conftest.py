# conftest.py for Code Story
"""Pytest configuration for Code Story project."""

# Set the default fixture loop scope for pytest-asyncio to 'function' to resolve deprecation warning
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest to set the default asyncio fixture loop scope to 'function'."""
    config.option.asyncio_default_fixture_loop_scope = "function"
