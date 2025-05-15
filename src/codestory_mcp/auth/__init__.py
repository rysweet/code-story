"""Authentication utilities for the MCP Adapter.

This package contains utilities for authenticating requests
to the MCP Adapter using Microsoft Entra ID.
"""

from .entra_validator import EntraValidator
from .scope_manager import ScopeManager

__all__ = ["EntraValidator", "ScopeManager"]
