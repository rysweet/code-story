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
from codestory_service.domain.graph import AskAnswer, AskRequest

# Set up logging
logger = logging.getLogger(__name__)

# Global singleton instance
_openai_adapter_instance: "OpenAIAdapter | None" = None


def get_azure_tenant_id_from_environment() -> str | None:
    """Get Azure tenant ID from environment variables or config files.

    Returns:
        Optional[str]: The tenant ID if found, None otherwise
    """
    # Check for environment variables in order of precedence
    for env_var in ["AZURE_TENANT_ID", "AZURE_OPENAI__TENANT_ID", "OPENAI__TENANT_ID"]:
        if os.environ.get(env_var):
            tenant_id = os.environ[env_var]
            logger.info(f"Found tenant ID in environment variable {env_var}: {tenant_id}")
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
            capture_output=True,
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
        # Log environment variables (without sensitive values)
        endpoint = os.environ.get("AZURE_OPENAI__ENDPOINT", "NOT_SET")
        deployment_id = os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID", "NOT_SET")
        api_version = os.environ.get("AZURE_OPENAI__API_VERSION", "NOT_SET")
        tenant_id = os.environ.get("AZURE_TENANT_ID") or os.environ.get(
            "AZURE_OPENAI__TENANT_ID", "NOT_SET"
        )

        logger.info(f"Azure OpenAI Endpoint: {endpoint}")
        logger.info(f"Azure OpenAI Deployment ID: {deployment_id}")
        logger.info(f"Azure OpenAI API Version: {api_version}")
        logger.info(f"Azure Tenant ID: {tenant_id}")

        # Check if API key is set (but don't log the actual value)
        api_key = os.environ.get("AZURE_OPENAI__API_KEY") or os.environ.get("OPENAI__API_KEY")
        logger.info(f"API Key configured: {'Yes' if api_key else 'No'}")

        # Check Azure CLI authentication status
        try:
            import subprocess

            result = subprocess.run(
                ["az", "account", "show", "--query", "user.name", "-o", "tsv"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info(f"Azure CLI authenticated as: {result.stdout.strip()}")
            else:
                logger.warning(f"Azure CLI not authenticated: {result.stderr.strip()}")
        except Exception as e:
            logger.warning(f"Could not check Azure CLI status: {e}")

        # Check current working directory and container info
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Running in container: {'Yes' if os.path.exists('/.dockerenv') else 'No'}")

        try:
            # Create or use provided client
            logger.info("Initializing OpenAI client...")
            try:
                self.client = client or OpenAIClient(
                    endpoint=os.environ.get("AZURE_OPENAI__ENDPOINT"),
                    embedding_model=os.environ.get("OPENAI__EMBEDDING_MODEL", "text-embedding-3-small"),
                    chat_model=os.environ.get("OPENAI__CHAT_MODEL", "gpt-4o"),
                    reasoning_model=os.environ.get("OPENAI__REASONING_MODEL", "gpt-4o"),
                    api_version=os.environ.get("AZURE_OPENAI__API_VERSION", "2025-03-01-preview"),
                )
                logger.info("OpenAI client initialized successfully.")
                logger.info(f"Client details: Endpoint={self.client.endpoint}, ChatModel={self.client.chat_model}, EmbeddingModel={self.client.embedding_model}, ReasoningModel={self.client.reasoning_model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise

            # Log client configuration details
            logger.info(f"Chat model: {getattr(self.client, 'chat_model', 'NOT_SET')}")
            logger.info(f"Embedding model: {getattr(self.client, 'embedding_model', 'NOT_SET')}")
            logger.info(f"Reasoning model: {getattr(self.client, 'reasoning_model', 'NOT_SET')}")

        except AuthenticationError as e:
            logger.error(f"OpenAI authentication error during initialization: {e!s}")
            # Try to extract tenant info from error
            tenant_from_error = extract_tenant_id_from_error(str(e))
            if tenant_from_error:
                logger.error(f"Tenant ID from error: {tenant_from_error}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"OpenAI authentication error: {e!s}",
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e!s}")
            logger.error(f"Error type: {type(e).__name__}")

            # Log additional debug info for common issues
            if "404" in str(e):
                logger.error("404 error suggests endpoint or deployment configuration issue")
            elif "401" in str(e) or "403" in str(e):
                logger.error("Authentication error suggests credential or permission issue")
            elif "timeout" in str(e).lower():
                logger.error("Timeout suggests network connectivity issue")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize OpenAI client: {e!s}",
            ) from e
    async def answer_question(
        self,
        request: AskRequest,
        context_items: list[dict[str, Any]]
    ) -> AskAnswer:
        """
        Generate a natural language answer to a codebase question.

        Args:
            request: The AskRequest containing the question and parameters.
            context_items: List of context items (nodes) relevant to the question.

        Returns:
            AskAnswer: The generated answer.

        Note:
            This is a stub for type correctness. Implement actual logic as needed.
        """
        raise NotImplementedError("answer_question must be implemented.")

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
            ) from e
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create embeddings: {e!s}",
            ) from e

    async def check_health(self) -> dict[str, Any]:
        """Check OpenAI API health.

        Returns:
            Dictionary containing health information
        """
        try:
            # Get the actual deployment model from environment first, then fallback to client default
            test_model = os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID") or self.client.chat_model
            test_message = "Hello! This is a health check."
            
            logger.info(f"Health check using model: {test_model}")
            logger.info(f"Test message: {test_message}")

            # Check if this is a reasoning model and adjust parameters accordingly
            is_reasoning_model = any(reasoning_model in test_model.lower() for reasoning_model in ["o1", "o1-preview", "o1-mini"])
            logger.info(f"Is reasoning model: {is_reasoning_model}")
            
            # Use the client's chat_async method which handles reasoning models properly
            from codestory.llm.models import ChatMessage, ChatRole
            messages = [
                ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
                ChatMessage(role=ChatRole.USER, content=test_message),
            ]

            logger.info("Sending health check request via OpenAI client...")

            if is_reasoning_model:
                # For reasoning models, use max_completion_tokens and no temperature
                logger.info("Using max_completion_tokens=10 for reasoning model (no temperature)")
                response = await self.client.chat_async(
                    messages,
                    model=test_model,
                    max_completion_tokens=10
                )
            else:
                # For regular models, use max_tokens and temperature
                logger.info("Using max_tokens=10 and temperature=0.1 for regular model")
                response = await self.client.chat_async(
                    messages,
                    model=test_model,
                    max_tokens=10,
                    temperature=0.1
                )

            logger.info("Health check request completed successfully")
            logger.info(f"Response ID: {getattr(response, 'id', 'N/A')}")
            logger.info(f"Response model: {getattr(response, 'model', 'N/A')}")

            # If we get here, the API is healthy
            available_models = [
                self.client.embedding_model,
                self.client.chat_model,
                self.client.reasoning_model,
            ]
            available_models = [m for m in list(set(available_models)) if m is not None]

            # Determine status: require embedding and chat models at minimum
            if self.client.embedding_model and self.client.chat_model:
                status = "healthy"
            else:
                status = "degraded"

            logger.info(f"Health check completed with status: {status}")
            logger.info(f"Available models: {available_models}")

            result = {
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

            logger.info(f"Health check result: {result}")
            return result

        except Exception as e:
            error_message = str(e)
            logger.error("=== OpenAI Health Check Failed ===")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {error_message}")

            # Log full stack trace for debugging
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Check for 404 errors - this indicates a serious API configuration issue
            # that needs fixing
            if (
                "<html>" in error_message
                and "404 Not Found" in error_message
                and "nginx" in error_message
            ):
                logger.error(
                    "Received nginx 404 error when accessing Azure OpenAI API. "
                    "This indicates a serious endpoint configuration issue."
                )
                deployment_id = os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID", "NOT SET")
                endpoint = os.environ.get("AZURE_OPENAI__ENDPOINT", "NOT SET")
                api_version = os.environ.get("AZURE_OPENAI__API_VERSION", "NOT SET")

                logger.error(f"Current deployment_id: {deployment_id}")
                logger.error(f"Current endpoint: {endpoint}")
                logger.error(f"Current api_version: {api_version}")

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
                        "suggestion": (
                            "Set all required Azure OpenAI environment variables. "
                            "No default endpoint is provided."
                        ),
                    },
                }
            # Check for Azure authentication errors
            elif (
                "DefaultAzureCredential failed to retrieve a token" in error_message
                or "AADSTS700003" in error_message
            ):
                logger.error("Azure authentication failure detected")

                tenant_id = get_azure_tenant_id_from_environment()
                if not tenant_id:
                    tenant_id = extract_tenant_id_from_error(error_message)

                logger.error(f"Tenant ID for renewal: {tenant_id}")

                renewal_cmd = "az login --scope https://cognitiveservices.azure.com/.default"
                if tenant_id:
                    renewal_cmd = f"az login --tenant {tenant_id} --scope https://cognitiveservices.azure.com/.default"

                logger.error(f"Suggested renewal command: {renewal_cmd}")

                return {
                    "status": "unhealthy",
                    "details": {
                        "error": "Azure authentication credentials expired",
                        "type": "AuthenticationError",
                        "tenant_id": tenant_id,
                        "solution": f"Run: {renewal_cmd}",
                        "hint": (
                            "You can use our CLI for manual renewal: codestory service auth-renew"
                        ),
                    },
                }
            else:
                logger.warning(f"OpenAI health check failed with unexpected error: {error_message}")

                # Log additional context for debugging
                logger.error(f"Client type: {type(self.client)}")
                logger.error(
                    f"Async client type: {type(getattr(self.client, '_async_client', None))}"
                )

                return {
                    "status": "degraded",
                    "details": {
                        "message": "OpenAI health check failed with unexpected error",
                        "error": error_message,
                        "error_type": type(e).__name__,
                    },
                }


import asyncio


async def get_openai_adapter() -> "OpenAIAdapter":
    """Factory function to get a singleton OpenAIAdapter instance, with health check."""
    global _openai_adapter_instance
    if _openai_adapter_instance is None:
        adapter = OpenAIAdapter()
        await adapter.check_health()  # Will raise if not healthy
        _openai_adapter_instance = adapter
    return _openai_adapter_instance