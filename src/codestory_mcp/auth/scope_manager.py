from codestory_mcp.utils.config import MCPSettings, get_mcp_settings

'Scope management for MCP authentication.\n\nThis module provides utilities for managing authorization scopes in the MCP Adapter.\n'

class ScopeManager:
    """Manage authorization scopes for the MCP Adapter."""

    def __init__(self, settings: MCPSettings | None = None) -> None:
        """Initialize the scope manager.

        Args:
            settings: Optional settings object for testing
        """
        self.settings: MCPSettings = settings or get_mcp_settings()

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
        if not self.settings.required_scopes:
            return True
        if '*' in scopes:
            return True
        return any(required_scope in scopes for required_scope in self.settings.required_scopes)

    def can_execute_tool(self, tool_name: str, scopes: list[str]) -> bool:
        """Check if the provided scopes allow executing the specified tool.

        Args:
            tool_name: Name of the tool to check
            scopes: List of scopes to check

        Returns:
            True if the scopes allow executing the tool, False otherwise
        """
        return self.has_required_scope(scopes)