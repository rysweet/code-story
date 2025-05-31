"""Main entry point for the MCP Adapter.

This module provides the main entry point for running the MCP Adapter.
"""

import logging
import sys

import structlog

from codestory_mcp.server import run_server

# Import all tools to register them
from codestory_mcp.utils.config import get_mcp_settings


def setup_logging() -> None:
    """Set up structured logging.

    This function configures structlog for structured logging.
    """
    settings = get_mcp_settings()

    # Configure structlog
    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")
    from typing import Callable, Any, MutableMapping, Mapping, Sequence
    pre_chain: Sequence[
        Callable[
            [Any, str, MutableMapping[str, Any]],
            Mapping[str, Any] | str | bytes | bytearray | tuple[Any, ...]
        ]
    ] = [
        structlog.stdlib.add_log_level,
        timestamper,
    ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer()
        if settings.debug
        else structlog.processors.JSONRenderer(),
        foreign_pre_chain=pre_chain,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # Set logging level for external libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    """Run the MCP Adapter.

    This function is the main entry point for running the MCP Adapter.
    """
    # Set up logging
    setup_logging()

    # Create a logger
    logger = structlog.get_logger(__name__)

    try:
        # Log startup
        logger.info("Starting MCP Adapter")

        # Run the server
        run_server()
    except KeyboardInterrupt:
        logger.info("MCP Adapter stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Error running MCP Adapter", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()