"""OpenAI adapter for the Code Story Service.

This module provides a service-specific adapter for OpenAI operations,
building on the core OpenAI client with additional functionality required
by the service layer.
"""

import logging
import os
import re
from typing import Any

from fastapi import HTTPException, status

from codestory.llm.client import OpenAIClient
from codestory.llm.exceptions import (
    AuthenticationError,
)

# Set up logging
logger = logging.getLogger(__name__)


def get_azure_tenant_id_from_environment() -> str | None:
    """Get Azure tenant ID from environment variables or config files.

    Returns:
        Optional[str]: The tenant ID if found, None otherwise
    """
    # Check for environment variables in order of precedence
    for env_var in ["AZURE_TENANT_ID", "AZURE_OPENAI__TENANT_ID", "OPENAI__TENANT_ID"]:
        if os.environ.get(env_var):
            tenant_id = os.environ[env_var]
            logger.info(
                f"Found tenant ID in environment variable {env_var}: {tenant_id}"
            )
            return tenant_id

    # Check .azure/config file
    azure_dir = os.path.expanduser("~/.azure")
    azure_config = os.path.join(azure_dir, "config")

    if os.path.exists(azure_config):
        try:
            with open(azure_config) as f:
                for line in f:
                    if line.strip().startswith("tenant ="):
                        tenant_id = line.split("=")[1].strip()
                        logger.info(f"Found tenant ID in Azure config: {tenant_id}")
                        return tenant_id
        except Exception as e:
            logger.warning(f"Error reading Azure config: {e}")

    # Check if we can extract it from Azure CLI
    try:
        import subprocess

        result = subprocess.run(
            ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,  # Timeout after 5 seconds
        )

        if result.returncode == 0 and result.stdout.strip():
            tenant_id = result.stdout.strip()
            logger.info(f"Found tenant ID from Azure CLI: {tenant_id}")
            return tenant_id
    except Exception as e:
        logger.debug(f"Could not get tenant ID from Azure CLI: {e}")

    logger.warning("Could not find Azure tenant ID in environment or config files")
    return None


def extract_tenant_id_from_error(error_message: str) -> str | None:
    """Extract tenant ID from an Azure authentication error message.

    Args:
        error_message: The error message to parse

    Returns:
        Optional[str]: The tenant ID if found, None otherwise
    """
    # Try various error message patterns
    patterns = [
        r"tenant '([0-9a-f-]+)'",
        r"tenant ID: ([0-9a-f-]+)",
        r"AADSTS500011.+?'([0-9a-f-]+)'",
        r"AADSTS700003.+?'([0-9a-f-]+)'",
    ]

    for pattern in patterns:
        tenant_match = re.search(pattern, error_message)
        if tenant_match:
            tenant_id = tenant_match.group(1)
            logger.info(f"Extracted tenant ID from error message: {tenant_id}")
            return tenant_id

    logger.debug("Could not extract tenant ID from error message")
    return None


class OpenAIAdapter:
    """Adapter for OpenAI operations specific to the service layer.

    This class wraps the core OpenAIClient, providing methods that map
    directly to the service's use cases and handling conversion between
    domain models and OpenAI API data structures.
    """

    def __init__(self, client: OpenAIClient | None = None) -> None:
        """Initialize the OpenAI adapter.

        Args:
            client: Optional existing OpenAIClient instance.
                   If not provided, a new OpenAIClient will be created.

        Raises:
            HTTPException: If connecting to OpenAI fails
        """
        try:
            # Create or use provided client
            if client is None:
                # Create a new client
                self.client = OpenAIClient()
            else:
                # Use the provided client
                self.client = client
        except AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"OpenAI authentication error: {e!s}",
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize OpenAI client: {e!s}",
            )

    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Create embeddings for a list of texts.

        Args:
            texts: List of texts to create embeddings for

        Returns:
            List of embedding vectors, one for each input text

        Raises:
            HTTPException: If embedding creation fails
        """
        try:
            # Use the async client to create embeddings
            response = await self.client.embed_async(texts)

            # Extract and return the embedding vectors
            return [data.embedding for data in response.data]
        except AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,  # Match the expected code in tests
                detail=f"OpenAI authentication error: {e!s}",
            )
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create embeddings: {e!s}",
            )

    async def check_health(self) -> dict[str, Any]:
        """Check OpenAI API health.

        Returns:
            Dictionary containing health information
        """
        try:
            client = self.client._async_client
            test_message = "Hello! This is a health check."
            test_model = self.client.chat_model
            # Use a minimal chat completion to check endpoint health
            try:
                response = await client.chat.completions.create(
                    deployment_name=test_model,
                    model=test_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": test_message},
                    ],
                    max_tokens=1,
                    temperature=0,
                )
                # If we get here, the API is healthy
                available_models = [
                    self.client.embedding_model,
                    self.client.chat_model,
                    self.client.reasoning_model,
                ]
                available_models = [
                    m for m in list(set(available_models)) if m is not None
                ]
                if all(
                    [
                        self.client.embedding_model,
                        self.client.chat_model,
                        self.client.reasoning_model,
                    ]
                ):
                    status = "healthy"
                else:
                    status = "degraded"
                logger.info(
                    f"OpenAI API health check passed with a test completion using model {test_model}"
                )
                return {
                    "status": status,
                    "details": {
                        "message": "OpenAI API connection successful",
                        "models": [
                            self.client.embedding_model or "unknown",
                            self.client.chat_model or "unknown",
                            self.client.reasoning_model or "unknown",
                        ],
                        "api_version": getattr(self.client, "api_version", "latest"),
                    },
                }
            except Exception as chat_err:
                error_message = str(chat_err)
                # Check for nginx 404 errors
                if (
                    "<html>" in error_message
                    and "404 Not Found" in error_message
                    and "nginx" in error_message
                ):
                    logger.error(
                        "Received nginx 404 error when accessing Azure OpenAI API. This indicates a serious endpoint configuration issue."
                    )
                    deployment_id = os.environ.get(
                        "AZURE_OPENAI__DEPLOYMENT_ID", "NOT SET"
                    )
                    endpoint = os.environ.get("AZURE_OPENAI__ENDPOINT", "NOT SET")
                    api_version = os.environ.get("AZURE_OPENAI__API_VERSION", "NOT SET")
                    return {
                        "status": "unhealthy",
                        "details": {
                            "message": "Azure OpenAI endpoint returned a 404 error",
                            "error": "Endpoint not found or unavailable",
                            "current_config": {
                                "deployment_id": deployment_id,
                                "endpoint": endpoint,
                                "api_version": api_version,
                            },
                            "required_config": {
                                "AZURE_OPENAI__DEPLOYMENT_ID": "<your-deployment-id>",
                                "AZURE_OPENAI__ENDPOINT": "<your-endpoint>",
                                "AZURE_OPENAI__API_VERSION": "<your-api-version>",
                            },
                            "suggestion": "Set all required Azure OpenAI environment variables. No default endpoint is provided.",
                        },
                    }
                # Check for Azure auth errors
                elif (
                    "DefaultAzureCredential failed to retrieve a token" in error_message
                    or "AADSTS700003" in error_message
                ):
                    tenant_id = get_azure_tenant_id_from_environment()
                    if not tenant_id:
                        tenant_id = extract_tenant_id_from_error(error_message)
                    renewal_cmd = (
                        "az login --scope https://cognitiveservices.azure.com/.default"
                    )
                    if tenant_id:
                        renewal_cmd = f"az login --tenant {tenant_id} --scope https://cognitiveservices.azure.com/.default"
                    logger.error(
                        f"Azure authentication failure detected. Attempting automatic renewal with: {renewal_cmd}"
                    )
                    return {
                        "status": "unhealthy",
                        "details": {
                            "error": "Azure authentication credentials expired",
                            "type": "AuthenticationError",
                            "tenant_id": tenant_id,
                            "solution": f"Run: {renewal_cmd}",
                            "hint": "You can use our CLI for manual renewal: codestory service auth-renew",
                        },
                    }
                else:
                    # Some other error occurred
                    logger.warning(f"Couldn't use chat completions API: {chat_err}")
                    available_models = [
                        self.client.embedding_model,
                        self.client.chat_model,
                        self.client.reasoning_model,
                    ]
                    available_models = [m for m in available_models if m is not None]
                    status = "degraded"
                    return {
                        "status": status,
                        "details": {
                            "message": "OpenAI API connection successful (degraded mode)",
                            "models": available_models,
                            "api_version": getattr(
                                self.client, "api_version", "latest"
                            ),
                            "error": error_message,
                        },
                    }
        except Exception as e:
            error_message = str(e)
            logger.error(f"OpenAI health check failed: {error_message}")
            # Check for 404 errors - this indicates a serious API configuration issue that needs fixing
            if (
                "<html>" in error_message
                and "404 Not Found" in error_message
                and "nginx" in error_message
            ):
                logger.error(
                    "Received nginx 404 error when accessing Azure OpenAI API. This indicates a serious endpoint configuration issue."
                )
                deployment_id = os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID", "NOT SET")
                endpoint = os.environ.get("AZURE_OPENAI__ENDPOINT", "NOT SET")
                api_version = os.environ.get("AZURE_OPENAI__API_VERSION", "NOT SET")
                return {
                    "status": "unhealthy",
                    "details": {
                        "message": "Azure OpenAI endpoint returned a 404 error",
                        "error": "Endpoint not found or unavailable",
                        "current_config": {
                            "deployment_id": deployment_id,
                            "endpoint": endpoint,
                            "api_version": api_version,
                        },
                        "required_config": {
                            "AZURE_OPENAI__DEPLOYMENT_ID": "<your-deployment-id>",
                            "AZURE_OPENAI__ENDPOINT": "<your-endpoint>",
                            "AZURE_OPENAI__API_VERSION": "<your-api-version>",
                        },
                        "suggestion": "Set all required Azure OpenAI environment variables. No default endpoint is provided.",
                    },
                }
            # Check for Azure authentication errors
            elif (
                "DefaultAzureCredential failed to retrieve a token" in error_message
                or "AADSTS700003" in error_message
            ):
                tenant_id = get_azure_tenant_id_from_environment()
                if not tenant_id:
                    tenant_id = extract_tenant_id_from_error(error_message)
                renewal_cmd = (
                    "az login --scope https://cognitiveservices.azure.com/.default"
                )
                if tenant_id:
                    renewal_cmd = f"az login --tenant {tenant_id} --scope https://cognitiveservices.azure.com/.default"
                return {
                    "status": "unhealthy",
                    "details": {
                        "error": "Azure authentication credentials expired",
                        "type": "AuthenticationError",
                        "tenant_id": tenant_id,
                        "solution": f"Run: {renewal_cmd}",
                        "hint": "You can use our CLI for manual renewal: codestory service auth-renew",
                    },
                }
            else:
                logger.warning(
                    f"OpenAI health check failed with unexpected error: {error_message}"
                )
                return {
                    "status": "degraded",
                    "details": {
                        "message": "OpenAI health check failed with unexpected error",
                        "error": error_message,
                    },
                }


def get_openai_adapter() -> "OpenAIAdapter":
    """Factory function to get a singleton OpenAIAdapter instance."""
    global _openai_adapter_instance
    if "_openai_adapter_instance" not in globals():
        _openai_adapter_instance = OpenAIAdapter()
    return _openai_adapter_instance
