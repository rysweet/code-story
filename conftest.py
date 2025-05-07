# conftest.py for Code Story
import pytest

# Set the default fixture loop scope for pytest-asyncio to 'function' to resolve deprecation warning
pytest_plugins = []

def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"
