"""Azure OpenAI client implementation.

This module provides a client for interacting with Azure OpenAI services,
supporting completions, chat, and embeddings with both synchronous and
asynchronous APIs.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, cast

import openai
from openai import AsyncAzureOpenAI, AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from ..config.settings import get_settings
from .backoff import retry_on_openai_errors, retry_on_openai_errors_async
from .exceptions import (
    AuthenticationError,
    InvalidRequestError,
    OpenAIError,
)
from .metrics import OperationType, instrument_request, instrument_async_request
from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)

# Set up logging
logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for Azure OpenAI services with support for completion, chat, and embeddings."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        chat_model: str = "gpt-4o",
        reasoning_model: str = "gpt-4o",
        api_version: str = "2025-03-01-preview",
        timeout: float = 60.0,
        max_retries: int = 5,
        retry_backoff_factor: float = 2.0,
        **config_options: Any,
    ) -> None:
        """Initialize client with Azure OpenAI credentials and options.

        Args:
            endpoint: Azure OpenAI API endpoint
            embedding_model: Default model for embeddings (also used as deployment name)
            chat_model: Default model for chat completions (also used as deployment name)
            reasoning_model: Default model for text completions (also used as deployment name)
            api_version: Azure OpenAI API version
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Multiplier for exponential backoff
            **config_options: Additional client configuration options

        Raises:
            AuthenticationError: If endpoint is missing
        """
        self.endpoint = endpoint

        # If endpoint not provided, attempt to load from settings
        if not endpoint and get_settings:
            try:
                settings = get_settings()
                if hasattr(settings, "openai") and hasattr(settings.openai, "endpoint"):
                    self.endpoint = settings.openai.endpoint
            except Exception as e:
                logger.warning(f"Failed to load OpenAI settings: {e}")

        # Validate endpoint
        if not self.endpoint:
            raise AuthenticationError("API endpoint is required")

        # Store default models (also used as deployment names)
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.reasoning_model = reasoning_model

        # Store configuration
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.config_options = config_options

        # Initialize clients
        # Use tenant_id and subscription_id from settings if available
        try:
            settings = get_settings()
            tenant_id = getattr(settings.openai, "tenant_id", None)
            subscription_id = getattr(settings.openai, "subscription_id", None)
        except Exception:
            tenant_id = None
            subscription_id = None

        # For DefaultAzureCredential - need to handle tenant separately
        try:
            # Set subscription if provided
            if subscription_id:
                import subprocess

                try:
                    # Set the default subscription
                    subprocess.run(
                        ["az", "account", "set", "--subscription", subscription_id],
                        check=True,
                        capture_output=True,
                    )
                    logger.info(f"Set Azure subscription to {subscription_id}")
                except Exception as e:
                    logger.warning(f"Failed to set Azure subscription: {e}")

            # If tenant_id is provided, check if we need to login
            if tenant_id:
                import subprocess

                try:
                    # Check if we need to log in specifically to the tenant
                    # First check if we're already authenticated with the correct tenant
                    show_result = subprocess.run(
                        ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
                        check=False,  # Don't raise error if not logged in
                        capture_output=True,
                        text=True,
                    )

                    current_tenant = show_result.stdout.strip()

                    # If we're not logged in or tenant doesn't match, remind user
                    if show_result.returncode != 0 or current_tenant != tenant_id:
                        logger.warning(
                            f"Currently logged into tenant '{current_tenant}', but need tenant '{tenant_id}'. "
                            f"Consider running 'az login --tenant {tenant_id}'"
                        )
                except Exception as e:
                    logger.warning(f"Failed to check Azure tenant: {e}")
        except Exception as e:
            logger.warning(f"Error setting up Azure authentication: {e}")

        # Create the credential - DefaultAzureCredential doesn't accept tenant_id directly
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )

        self._sync_client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            timeout=self.timeout,
            max_retries=0,  # We handle retries ourselves
            azure_ad_token_provider=token_provider,
        )

        self._async_client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            timeout=self.timeout,
            max_retries=0,  # We handle retries ourselves
            azure_ad_token_provider=token_provider,
        )

    def _prepare_request_data(self, request):
        """Extract model name and prepare request data, removing internal parameters.

        Args:
            request: Request model with parameters

        Returns:
            tuple: (model_name, request_data) with model_name extracted and internal params removed
        """
        request_data = request.model_dump(exclude_none=True)
        model_name = request_data.pop("model")

        # Remove internal parameters that shouldn't be passed to the API
        if "_operation_type" in request_data:
            request_data.pop("_operation_type")

        return model_name, request_data

    @instrument_request(operation=OperationType.COMPLETION)
    @retry_on_openai_errors(operation_type=OperationType.COMPLETION)
    def complete(
        self,
        prompt: Union[str, List[str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        """Generate completions using specified model.

        Args:
            prompt: Text prompt(s) to generate from
            model: OpenAI model to use (defaults to reasoning_model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters for the OpenAI API

        Returns:
            Response containing generated completions

        Raises:
            InvalidRequestError: If the request parameters are invalid
            RateLimitError: If the API rate limit is exceeded
            AuthenticationError: If authentication fails
            ServiceUnavailableError: If the OpenAI API is unavailable
            OpenAIError: For other API errors
        """
        model = model or self.reasoning_model

        # Create request payload
        request = CompletionRequest(
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        try:
            # Make API request
            # Extract model name and prepare request data
            model_name, request_data = self._prepare_request_data(request)

            # Try to use the Azure OpenAI specific parameters, fall back to standard if not supported
            try:
                # First try with Azure-specific parameters
                response = self._sync_client.completions.create(
                    deployment_name=model_name, model=model_name, **request_data
                )
            except TypeError as e:
                if "unexpected keyword argument 'deployment_name'" in str(e):
                    # Fall back to standard parameters for non-Azure clients
                    logger.debug(
                        "Falling back to standard OpenAI parameters (not using deployment_name)"
                    )
                    response = self._sync_client.completions.create(
                        model=model_name, **request_data
                    )
                else:
                    # Re-raise other TypeError issues
                    raise

            # Convert to our response model
            return CompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f"Invalid completion request: {message}")
            raise InvalidRequestError(
                f"Invalid request parameters: {message}", cause=e
            ) from e
        except Exception as e:
            # The retry decorator will handle most errors, but we need to catch and convert
            # any that slip through to maintain a consistent interface
            if not isinstance(e, OpenAIError):
                logger.error(f"Unexpected error in completion: {str(e)}")
                raise OpenAIError(
                    f"Error generating completion: {str(e)}", cause=e
                ) from e
            raise

    @instrument_request(operation=OperationType.CHAT)
    @retry_on_openai_errors(operation_type=OperationType.CHAT)
    def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> ChatCompletionResponse:
        """Generate chat completions from message list.

        Args:
            messages: List of chat messages with roles
            model: OpenAI model to use (defaults to chat_model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters for the OpenAI API

        Returns:
            Response containing generated chat completions

        Raises:
            InvalidRequestError: If the request parameters are invalid
            RateLimitError: If the API rate limit is exceeded
            AuthenticationError: If authentication fails
            ServiceUnavailableError: If the OpenAI API is unavailable
            OpenAIError: For other API errors
        """
        model = model or self.chat_model

        # Create request payload
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        try:
            # Make API request
            # Extract model name and prepare request data
            model_name, request_data = self._prepare_request_data(request)

            # Try to use the Azure OpenAI specific parameters, fall back to standard if not supported
            try:
                # First try with Azure-specific parameters
                response = self._sync_client.chat.completions.create(
                    deployment_name=model_name, model=model_name, **request_data
                )
            except TypeError as e:
                if "unexpected keyword argument 'deployment_name'" in str(e):
                    # Fall back to standard parameters for non-Azure clients
                    logger.debug(
                        "Falling back to standard OpenAI parameters (not using deployment_name)"
                    )
                    response = self._sync_client.chat.completions.create(
                        model=model_name, **request_data
                    )
                else:
                    # Re-raise other TypeError issues
                    raise

            # Convert to our response model
            return ChatCompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f"Invalid chat request: {message}")
            raise InvalidRequestError(
                f"Invalid request parameters: {message}", cause=e
            ) from e
        except Exception as e:
            # The retry decorator will handle most errors, but we need to catch and convert
            # any that slip through to maintain a consistent interface
            if not isinstance(e, OpenAIError):
                logger.error(f"Unexpected error in chat: {str(e)}")
                raise OpenAIError(
                    f"Error generating chat completion: {str(e)}", cause=e
                ) from e
            raise

    @instrument_request(operation=OperationType.EMBEDDING)
    @retry_on_openai_errors(operation_type=OperationType.EMBEDDING)
    def embed(
        self, texts: Union[str, List[str]], model: Optional[str] = None, **kwargs: Any
    ) -> EmbeddingResponse:
        """Generate embeddings for provided texts.

        Args:
            texts: Text(s) to generate embeddings for
            model: OpenAI model to use (defaults to embedding_model)
            **kwargs: Additional parameters for the OpenAI API

        Returns:
            Response containing generated embeddings

        Raises:
            InvalidRequestError: If the request parameters are invalid
            RateLimitError: If the API rate limit is exceeded
            AuthenticationError: If authentication fails
            ServiceUnavailableError: If the OpenAI API is unavailable
            OpenAIError: For other API errors
        """
        model = model or self.embedding_model

        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        # Create request payload
        request = EmbeddingRequest(model=model, input=texts, **kwargs)

        try:
            # Make API request
            # Extract model name and prepare request data
            model_name, request_data = self._prepare_request_data(request)

            # Try to use the Azure OpenAI specific parameters, fall back to standard if not supported
            try:
                # First try with Azure-specific parameters
                response = self._sync_client.embeddings.create(
                    deployment_name=model_name, model=model_name, **request_data
                )
            except TypeError as e:
                if "unexpected keyword argument 'deployment_name'" in str(e):
                    # Fall back to standard parameters for non-Azure clients
                    logger.debug(
                        "Falling back to standard OpenAI parameters (not using deployment_name)"
                    )
                    response = self._sync_client.embeddings.create(
                        model=model_name, **request_data
                    )
                else:
                    # Re-raise other TypeError issues
                    raise

            # Convert to our response model
            return EmbeddingResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f"Invalid embedding request: {message}")
            raise InvalidRequestError(
                f"Invalid request parameters: {message}", cause=e
            ) from e
        except Exception as e:
            # The retry decorator will handle most errors, but we need to catch and convert
            # any that slip through to maintain a consistent interface
            if not isinstance(e, OpenAIError):
                logger.error(f"Unexpected error in embedding: {str(e)}")
                raise OpenAIError(
                    f"Error generating embeddings: {str(e)}", cause=e
                ) from e
            raise

    @instrument_async_request(operation=OperationType.COMPLETION)
    @retry_on_openai_errors_async(operation_type=OperationType.COMPLETION)
    async def complete_async(
        self,
        prompt: Union[str, List[str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        """Asynchronous version of complete() method.

        Args:
            prompt: Text prompt(s) to generate from
            model: OpenAI model to use (defaults to reasoning_model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters for the OpenAI API

        Returns:
            Response containing generated completions

        Raises:
            InvalidRequestError: If the request parameters are invalid
            RateLimitError: If the API rate limit is exceeded
            AuthenticationError: If authentication fails
            ServiceUnavailableError: If the OpenAI API is unavailable
            OpenAIError: For other API errors
        """
        model = model or self.reasoning_model

        # Create request payload
        request = CompletionRequest(
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        try:
            # Make API request
            # Extract model name and prepare request data
            model_name, request_data = self._prepare_request_data(request)

            # Try to use the Azure OpenAI specific parameters, fall back to standard if not supported
            try:
                # First try with Azure-specific parameters
                response = await self._async_client.completions.create(
                    deployment_name=model_name, model=model_name, **request_data
                )
            except TypeError as e:
                if "unexpected keyword argument 'deployment_name'" in str(e):
                    # Fall back to standard parameters for non-Azure clients
                    logger.debug(
                        "Falling back to standard OpenAI parameters (not using deployment_name)"
                    )
                    response = await self._async_client.completions.create(
                        model=model_name, **request_data
                    )
                else:
                    # Re-raise other TypeError issues
                    raise

            # Convert to our response model
            return CompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f"Invalid completion request: {message}")
            raise InvalidRequestError(
                f"Invalid request parameters: {message}", cause=e
            ) from e
        except Exception as e:
            # The retry decorator will handle most errors, but we need to catch and convert
            # any that slip through to maintain a consistent interface
            if not isinstance(e, OpenAIError):
                logger.error(f"Unexpected error in async completion: {str(e)}")
                raise OpenAIError(
                    f"Error generating completion: {str(e)}", cause=e
                ) from e
            raise

    @instrument_async_request(operation=OperationType.CHAT)
    @retry_on_openai_errors_async(operation_type=OperationType.CHAT)
    async def chat_async(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> ChatCompletionResponse:
        """Asynchronous version of chat() method.

        Args:
            messages: List of chat messages with roles
            model: OpenAI model to use (defaults to chat_model)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters for the OpenAI API

        Returns:
            Response containing generated chat completions

        Raises:
            InvalidRequestError: If the request parameters are invalid
            RateLimitError: If the API rate limit is exceeded
            AuthenticationError: If authentication fails
            ServiceUnavailableError: If the OpenAI API is unavailable
            OpenAIError: For other API errors
        """
        model = model or self.chat_model

        # Create request payload
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        try:
            # Make API request
            # Extract model name and prepare request data
            model_name, request_data = self._prepare_request_data(request)

            # Try to use the Azure OpenAI specific parameters, fall back to standard if not supported
            try:
                # First try with Azure-specific parameters
                response = await self._async_client.chat.completions.create(
                    deployment_name=model_name, model=model_name, **request_data
                )
            except TypeError as e:
                if "unexpected keyword argument 'deployment_name'" in str(e):
                    # Fall back to standard parameters for non-Azure clients
                    logger.debug(
                        "Falling back to standard OpenAI parameters (not using deployment_name)"
                    )
                    response = await self._async_client.chat.completions.create(
                        model=model_name, **request_data
                    )
                else:
                    # Re-raise other TypeError issues
                    raise

            # Convert to our response model
            return ChatCompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f"Invalid chat request: {message}")
            raise InvalidRequestError(
                f"Invalid request parameters: {message}", cause=e
            ) from e
        except Exception as e:
            # The retry decorator will handle most errors, but we need to catch and convert
            # any that slip through to maintain a consistent interface
            if not isinstance(e, OpenAIError):
                logger.error(f"Unexpected error in async chat: {str(e)}")
                raise OpenAIError(
                    f"Error generating chat completion: {str(e)}", cause=e
                ) from e
            raise

    @instrument_async_request(operation=OperationType.EMBEDDING)
    @retry_on_openai_errors_async(operation_type=OperationType.EMBEDDING)
    async def embed_async(
        self, texts: Union[str, List[str]], model: Optional[str] = None, **kwargs: Any
    ) -> EmbeddingResponse:
        """Asynchronous version of embed() method.

        Args:
            texts: Text(s) to generate embeddings for
            model: OpenAI model to use (defaults to embedding_model)
            **kwargs: Additional parameters for the OpenAI API

        Returns:
            Response containing generated embeddings

        Raises:
            InvalidRequestError: If the request parameters are invalid
            RateLimitError: If the API rate limit is exceeded
            AuthenticationError: If authentication fails
            ServiceUnavailableError: If the OpenAI API is unavailable
            OpenAIError: For other API errors
        """
        model = model or self.embedding_model

        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        # Create request payload
        request = EmbeddingRequest(model=model, input=texts, **kwargs)

        try:
            # Make API request
            # Extract model name and prepare request data
            model_name, request_data = self._prepare_request_data(request)

            # Try to use the Azure OpenAI specific parameters, fall back to standard if not supported
            try:
                # First try with Azure-specific parameters
                response = await self._async_client.embeddings.create(
                    deployment_name=model_name, model=model_name, **request_data
                )
            except TypeError as e:
                if "unexpected keyword argument 'deployment_name'" in str(e):
                    # Fall back to standard parameters for non-Azure clients
                    logger.debug(
                        "Falling back to standard OpenAI parameters (not using deployment_name)"
                    )
                    response = await self._async_client.embeddings.create(
                        model=model_name, **request_data
                    )
                else:
                    # Re-raise other TypeError issues
                    raise

            # Convert to our response model
            return EmbeddingResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f"Invalid embedding request: {message}")
            raise InvalidRequestError(
                f"Invalid request parameters: {message}", cause=e
            ) from e
        except Exception as e:
            # The retry decorator will handle most errors, but we need to catch and convert
            # any that slip through to maintain a consistent interface
            if not isinstance(e, OpenAIError):
                logger.error(f"Unexpected error in async embedding: {str(e)}")
                raise OpenAIError(
                    f"Error generating embeddings: {str(e)}", cause=e
                ) from e
            raise


def create_client(**kwargs: Any) -> OpenAIClient:
    """Create an OpenAIClient with settings from configuration.

    Args:
        **kwargs: Override configuration settings

    Returns:
        Configured OpenAIClient instance

    Raises:
        Exception: If settings cannot be loaded
    """
    try:
        settings = get_settings()

        # Create client with settings
        client = OpenAIClient(
            endpoint=settings.openai.endpoint,
            embedding_model=settings.openai.embedding_model,
            chat_model=settings.openai.chat_model,
            reasoning_model=settings.openai.reasoning_model,
            api_version=settings.openai.api_version,
            timeout=settings.openai.timeout,
            max_retries=settings.openai.max_retries,
            retry_backoff_factor=settings.openai.retry_backoff_factor,
            **kwargs,
        )

        return client
    except Exception as e:
        logger.error(f"Failed to create OpenAI client from settings: {e}")
        raise
