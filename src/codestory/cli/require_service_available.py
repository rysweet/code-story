import os
import sys

from rich.console import Console

from .client import ServiceClient, ServiceError


def require_service_available() -> None:
    """Checks if the Code Story service is running and healthy.
    
    If not, prints an error and exits.
    Skips the check in test environments (when PYTEST_CURRENT_TEST is set).
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        # In test environment, do nothing
        return
    
    console = Console()
    try:
        client = ServiceClient(console=console)
        client.check_service_health()
    except ServiceError:
        console.print(
            "[bold red]Code Story services are not running. Please start them "
            "with `codestory service start`."
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Failed to check service status: {e}")
        sys.exit(1)
