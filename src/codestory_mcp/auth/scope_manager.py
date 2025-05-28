"""Scope management for MCP authentication.

This module provides utilities for managing authorization scopes in the MCP Adapter.
"""

from codestory_mcp.utils.config import get_mcp_settings


class ScopeManager:
    """Manage authorization scopes for the MCP Adapter."""

    def __init__(self, settings=None) -> None:
        """Initialize the scope manager.

        Args:
            settings: Optional settings object for testing
        """
        self.settings = settings or get_mcp_settings()

    def get_required_scopes(self) -> list[str]:
        """Get required scopes for authorization.

        Returns:
            List of required scopes
        """
        return self.settings.required_scopes

    def has_required_scope(self, scopes: list[str]) -> bool:
        """Check if the provided scopes include at least one required scope.

        Args:
            scopes: List of scopes to check

        Returns:
            True if at least one required scope is present, False otherwise
        """
        # If no scopes are required, return True
        if not self.settings.required_scopes:
            return True

        # If wildcard scope is present, all permissions are granted
        if "*" in scopes:
            return True

        # Check if any required scope is present
        return any(required_scope in scopes for required_scope in self.settings.required_scopes)

    def can_execute_tool(self, tool_name: str, scopes: list[str]) -> bool:
        """Check if the provided scopes allow executing the specified tool.

        Args:
            tool_name: Name of the tool to check
            scopes: List of scopes to check

        Returns:
            True if the scopes allow executing the tool, False otherwise
        """
        # If any required scope is present, the tool can be executed
        return self.has_required_scope(scopes)