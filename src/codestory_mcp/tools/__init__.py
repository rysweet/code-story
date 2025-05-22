"""Tool implementations for the MCP Adapter.

This package contains implementations of the MCP tools that
allow agents to query and navigate the code knowledge graph.
"""

from typing import Dict, List, Type

from .base import BaseTool

# Tool registry will be populated when modules are imported
_tools: dict[str, type[BaseTool]] = {}


def register_tool(tool_class: type[BaseTool]) -> type[BaseTool]:
    """Register a tool class in the registry.

    Args:
        tool_class: The tool class to register

    Returns:
        The registered tool class (unchanged)
    """
    _tools[tool_class.name] = tool_class
    return tool_class


def get_tool(name: str) -> type[BaseTool]:
    """Get a tool class by name.

    Args:
        name: Name of the tool to retrieve

    Returns:
        The requested tool class

    Raises:
        KeyError: If the tool is not registered
    """
    return _tools[name]


def get_all_tools() -> list[type[BaseTool]]:
    """Get all registered tool classes.

    Returns:
        List of all registered tool classes
    """
    return list(_tools.values())
