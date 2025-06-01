"""Configuration-related exceptions."""
from typing import Any


class ConfigurationError(Exception):
    """Base class for configuration-related exceptions."""

    def __init__(self: Any, message: str, details: dict[str, Any] | None=None) -> None:
        """Initialize ConfigurationError.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""

    def __init__(self: Any, message: str, errors: list[dict[str, Any]] | None=None) -> None:
        """Initialize ValidationError.

        Args:
            message: Error message
            errors: List of validation errors
        """
        details = {'errors': errors or []}
        super().__init__(message, details)

class SourceError(ConfigurationError):
    """Exception raised when a configuration source cannot be loaded."""

    def __init__(self: Any, message: str, source: str, source_path: str | None=None, cause: Exception | None=None) -> None:
        """Initialize SourceError.

        Args:
            message: Error message
            source: Name of the configuration source (e.g., "env", "toml")
            source_path: Path to the configuration source
            cause: Original exception that caused this error
        """
        details = {'source': source, 'source_path': source_path, 'cause': str(cause) if cause else None}
        self.cause = cause
        super().__init__(message, details)

class KeyVaultError(ConfigurationError):
    """Exception raised when Azure KeyVault integration fails."""

    def __init__(self: Any, message: str, vault_name: str | None=None, secret_name: str | None=None, cause: Exception | None=None) -> None:
        """Initialize KeyVaultError.

        Args:
            message: Error message
            vault_name: Name of the Azure KeyVault
            secret_name: Name of the secret that failed to load
            cause: Original exception that caused this error
        """
        details = {'vault_name': vault_name, 'secret_name': secret_name, 'cause': str(cause) if cause else None}
        self.cause = cause
        super().__init__(message, details)

class SettingNotFoundError(ConfigurationError):
    """Exception raised when a requested setting doesn't exist."""

    def __init__(self: Any, setting_path: str, available_settings: list[str] | None=None) -> None:
        """Initialize SettingNotFoundError.

        Args:
            setting_path: Path to the setting that was not found
            available_settings: List of available settings paths
        """
        message = f"Setting '{setting_path}' not found"
        details = {'setting_path': setting_path, 'available_settings': available_settings}
        super().__init__(message, details)

class PermissionError(ConfigurationError):
    """Exception raised when configuration cannot be modified due to permissions."""

    def __init__(self: Any, message: str, file_path: str | None=None, operation: str | None=None) -> None:
        """Initialize PermissionError.

        Args:
            message: Error message
            file_path: Path to the file that couldn't be accessed
            operation: Operation that failed (e.g., "read", "write")
        """
        details = {'file_path': file_path, 'operation': operation}
        super().__init__(message, details)