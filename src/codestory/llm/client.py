"""Azure OpenAI client implementation.

This module provides a client for interacting with Azure OpenAI services,
supporting completions, chat, and embeddings with both synchronous and
asynchronous APIs.
"""
import logging
import os
from typing import Any
import openai
from openai import AsyncAzureOpenAI, AzureOpenAI
try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning('azure.identity not found. Azure AD authentication will not be available.')
    AZURE_IDENTITY_AVAILABLE = False
from ..config.settings import get_settings
from .backoff import retry_on_openai_errors, retry_on_openai_errors_async
from .exceptions import AuthenticationError, InvalidRequestError, OpenAIError
from .metrics import OperationType, instrument_async_request, instrument_request
from .models import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, CompletionRequest, CompletionResponse, EmbeddingRequest, EmbeddingResponse
logger = logging.getLogger(__name__)

class OpenAIClient:
    """Client for Azure OpenAI services with support for completion, chat, and embeddings."""

    def __init__(self: Any, endpoint: str | None=None, embedding_model: str='text-embedding-3-small', chat_model: str='gpt-4o', reasoning_model: str='gpt-4o', api_version: str='2025-03-01-preview', timeout: float=60.0, max_retries: int=5, retry_backoff_factor: float=2.0, **config_options: Any) -> None:
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
        if not endpoint and get_settings:
            try:
                settings = get_settings()
                if hasattr(settings, 'openai') and hasattr(settings.openai, 'endpoint'):
                    self.endpoint = settings.openai.endpoint
            except Exception as e:
                logger.warning(f'Failed to load OpenAI settings: {e}')
        if not self.endpoint:
            raise AuthenticationError('API endpoint is required')
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.reasoning_model = reasoning_model
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.config_options = config_options
        try:
            settings = get_settings()
            tenant_id = getattr(settings.openai, 'tenant_id', None)
            subscription_id = getattr(settings.openai, 'subscription_id', None)
        except Exception:
            tenant_id = None
            subscription_id = None
        try:
            if subscription_id:
                import subprocess
                try:
                    subprocess.run(['az', 'account', 'set', '--subscription', subscription_id], check=True, capture_output=True)
                    logger.info(f'Set Azure subscription to {subscription_id}')
                except Exception as e:
                    logger.warning(f'Failed to set Azure subscription: {e}')
            if tenant_id:
                import subprocess
                try:
                    show_result = subprocess.run(['az', 'account', 'show', '--query', 'tenantId', '-o', 'tsv'], check=False, capture_output=True, text=True)
                    current_tenant = show_result.stdout.strip()
                    if show_result.returncode != 0 or current_tenant != tenant_id:
                        logger.warning(f"Currently logged into tenant '{current_tenant}', but need tenant '{tenant_id}'. Attempting to run 'az login --tenant {tenant_id}' automatically")
                        try:
                            logger.info(f'Attempting automatic Azure login to tenant {tenant_id}')
                            login_cmd = ['az', 'login', '--tenant', tenant_id, '--use-device-code']
                            if 'CODESTORY_AUTH_SCOPE' in os.environ:
                                login_cmd.extend(['--scope', os.environ['CODESTORY_AUTH_SCOPE']])
                            else:
                                login_cmd.extend(['--scope', 'https://cognitiveservices.azure.com/.default'])
                            login_result = subprocess.run(login_cmd, check=False, capture_output=True, text=True)
                            if login_result.returncode == 0:
                                logger.info(f'Automatic Azure login to tenant {tenant_id} successful')
                            else:
                                if 'devicelogin' in login_result.stdout:
                                    try:
                                        import re
                                        url_match = re.search('(https://microsoft\\.com/devicelogin)', login_result.stdout)
                                        code_match = re.search('Enter the code ([A-Z0-9]+) to authenticate', login_result.stdout)
                                        if url_match and code_match:
                                            auth_url = url_match.group(1)
                                            auth_code = code_match.group(1)
                                            logger.warning('=' * 80)
                                            logger.warning('AZURE AUTHENTICATION REQUIRED')
                                            logger.warning('-' * 80)
                                            logger.warning(f'Visit: {auth_url}')
                                            logger.warning(f'Enter code: {auth_code}')
                                            logger.warning('=' * 80)
                                    except Exception as parse_err:
                                        logger.warning(f'Failed to parse device login info: {parse_err}')
                                if "Can't get attribute 'NormalizedResponse'" in login_result.stderr:
                                    logger.warning('Azure CLI appears to have an installation issue')
                                    logger.warning("You may need to reinstall or update the Azure CLI with 'brew update && brew upgrade azure-cli'")
                                    logger.warning(f"Then run 'az login --tenant {tenant_id}' manually in a terminal")
                                else:
                                    logger.warning(f'Automatic Azure login failed: {login_result.stderr}')
                                    logger.warning("You may need to run 'az login' manually in a terminal")
                        except Exception as login_err:
                            logger.warning(f'Automatic Azure login attempt failed: {login_err}')
                            logger.warning("You may need to run 'az login' manually in a terminal")
                except Exception as e:
                    logger.warning(f'Failed to check Azure tenant: {e}')
        except Exception as e:
            logger.warning(f'Error setting up Azure authentication: {e}')
        logger.info('=== OpenAI Client Initialization ===')
        logger.info(f'Endpoint: {self.endpoint}')
        logger.info(f'API Version: {self.api_version}')
        logger.info(f'Chat Model: {self.chat_model}')
        logger.info(f'Embedding Model: {self.embedding_model}')
        logger.info(f'Reasoning Model: {self.reasoning_model}')
        logger.info(f'Timeout: {self.timeout}')
        logger.info(f'Max Retries: {self.max_retries}')
        deployment_id_env = os.environ.get('AZURE_OPENAI__DEPLOYMENT_ID')
        client_params = {'azure_endpoint': self.endpoint, 'api_version': self.api_version, 'timeout': self.timeout, 'max_retries': 0}
        if not deployment_id_env:
            logger.warning('No AZURE_OPENAI__DEPLOYMENT_ID set; Azure requests may fail.')
        logger.info(f'Client parameters: {client_params}')
        if AZURE_IDENTITY_AVAILABLE:
            logger.info('Azure identity available - attempting DefaultAzureCredential authentication')
            try:
                logger.info('Creating DefaultAzureCredential...')
                credential = DefaultAzureCredential()
                logger.info('DefaultAzureCredential created successfully')
                logger.info('Testing credential by requesting token...')
                token_provider = get_bearer_token_provider(credential, 'https://cognitiveservices.azure.com/.default')
                logger.info('Token provider created successfully')
                client_params['azure_ad_token_provider'] = token_provider
                logger.info('Added token provider to client parameters')
            except Exception as e:
                logger.warning(f'Failed to initialize Azure AD authentication: {e}')
                logger.warning(f'Error type: {type(e).__name__}')
                logger.warning('Falling back to API key authentication...')
                logger.info('Attempting to get API key from settings...')
                try:
                    settings = get_settings()
                    api_key = getattr(settings.openai, 'api_key', None)
                    if api_key:
                        if hasattr(api_key, 'get_secret_value') and callable(api_key.get_secret_value):
                            client_params['api_key'] = api_key.get_secret_value()
                            logger.info('Using API key from settings (SecretStr)')
                        else:
                            client_params['api_key'] = api_key
                            logger.info('Using API key from settings (string)')
                    else:
                        logger.warning('No API key found in settings')
                except Exception as settings_e:
                    logger.error(f'Failed to get API key from settings: {settings_e}')
        else:
            logger.warning('Azure identity not available - using API key authentication only')
            try:
                settings = get_settings()
                api_key = getattr(settings.openai, 'api_key', None)
                if api_key:
                    if hasattr(api_key, 'get_secret_value') and callable(api_key.get_secret_value):
                        client_params['api_key'] = api_key.get_secret_value()
                        logger.info('Using API key authentication')
                    else:
                        client_params['api_key'] = api_key
                        logger.info('Using API key authentication')
                else:
                    logger.error('No API key found - authentication will likely fail')
            except Exception as e:
                logger.error(f'Failed to get API key from settings: {e}')
        safe_params = {k: v for k, v in client_params.items() if k not in ['api_key', 'azure_ad_token_provider']}
        logger.info(f'Final client parameters (sanitized): {safe_params}')
        auth_method = 'Azure AD' if 'azure_ad_token_provider' in client_params else 'API Key'
        logger.info(f'Authentication method: {auth_method}')
        logger.info('Creating Azure OpenAI clients...')
        deployment_id = deployment_id_env or self.chat_model
        logger.info(f'Using deployment ID: {deployment_id}')
        azure_openai_kwargs = {'azure_endpoint': client_params.get('azure_endpoint'), 'azure_deployment': deployment_id, 'api_version': client_params.get('api_version'), 'api_key': client_params.get('api_key'), 'azure_ad_token_provider': client_params.get('azure_ad_token_provider')}
        azure_openai_kwargs = {k: v for k, v in azure_openai_kwargs.items() if v is not None}
        logger.info(f'AzureOpenAI instantiation kwargs: {azure_openai_kwargs}')
        try:
            self._sync_client = AzureOpenAI(**azure_openai_kwargs)
            logger.info('Sync client created successfully')
            self._async_client = AsyncAzureOpenAI(**azure_openai_kwargs)
            logger.info('Async client created successfully')
            logger.info('=== OpenAI Client Initialization Complete ===')
        except Exception as e:
            logger.error(f'Failed to create AzureOpenAI clients: {e}')
            logger.error(f'Error type: {type(e).__name__}')
            if '404' in str(e):
                logger.error('404 error during client creation - check endpoint configuration')
            elif '401' in str(e) or '403' in str(e):
                logger.error('Authentication error during client creation - check credentials')
            raise

    def _prepare_request_data(self: Any, request: Any) -> None:
        """Extract model name and prepare request data, removing internal parameters.

        Args:
            request: Request model with parameters

        Returns:
            tuple: (model_name, request_data) with model_name extracted and internal params removed
        """
        request_data = request.model_dump(exclude_none=True)
        model_name = request_data.pop('model')
        if '_operation_type' in request_data:
            request_data.pop('_operation_type')
        for key in ('prompt', 'messages', 'input'):
            if key in request_data:
                request_data.pop(key)
        return (model_name, request_data)

    def _is_reasoning_model(self: Any, model: str) -> bool:
        """Check if the model is a reasoning model that requires special parameter handling.

        Args:
            model: Model name to check

        Returns:
            True if this is a reasoning model, False otherwise
        """
        reasoning_models = ['o1', 'o1-preview', 'o1-mini']
        return any((reasoning_model in model.lower() for reasoning_model in reasoning_models))

    def _adjust_params_for_reasoning_model(self: Any, params: dict[str, Any], model: str) -> dict[str, Any]:
        """Adjust parameters for reasoning models.

        Reasoning models like o1 require different parameters:
        - Use max_completion_tokens instead of max_tokens
        - Do not support temperature parameter

        Args:
            params: Original parameters
            model: Model name

        Returns:
            Adjusted parameters for reasoning models
        """
        if not self._is_reasoning_model(model):
            return params
        adjusted_params = params.copy()
        if 'max_tokens' in adjusted_params:
            max_tokens_value = adjusted_params.pop('max_tokens')
            if max_tokens_value is not None:
                adjusted_params['max_completion_tokens'] = max_tokens_value
                logger.info(f'Converted max_tokens to max_completion_tokens for reasoning model: {model}')
        if 'temperature' in adjusted_params:
            adjusted_params.pop('temperature')
            logger.info(f'Removed temperature parameter for reasoning model: {model}')
        return adjusted_params

    @instrument_request(operation=OperationType.COMPLETION)
    @retry_on_openai_errors(operation_type=OperationType.COMPLETION)
    def complete(self: Any, prompt: str | list[str], model: str | None=None, max_tokens: int | None=None, temperature: float | None=None, **kwargs: Any) -> CompletionResponse:
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
        request = CompletionRequest(model=model, prompt=prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
        try:
            model_name, request_data = self._prepare_request_data(request)
            response = self._sync_client.completions.create(model=model_name, prompt=prompt, max_tokens=max_tokens, temperature=temperature, **request_data)
            return CompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f'Invalid completion request: {message}')
            raise InvalidRequestError(f'Invalid request parameters: {message}', cause=e) from e
        except Exception as e:
            if not isinstance(e, OpenAIError):
                logger.error(f'Unexpected error in completion: {e!s}')
                raise OpenAIError(f'Error generating completion: {e!s}', cause=e) from e
            raise

    @instrument_request(operation=OperationType.CHAT)
    @retry_on_openai_errors(operation_type=OperationType.CHAT)
    def chat(self: Any, messages: list[ChatMessage], model: str | None=None, max_tokens: int | None=None, temperature: float | None=None, **kwargs: Any) -> ChatCompletionResponse:
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
        request = ChatCompletionRequest(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **kwargs)
        try:
            model_name, request_data = self._prepare_request_data(request)
            request_data = self._adjust_params_for_reasoning_model(request_data, model_name)
            api_call_params = {'model': model_name, 'messages': [m.model_dump() for m in messages], **request_data}
            response = self._sync_client.chat.completions.create(**api_call_params)
            return ChatCompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f'Invalid chat request: {message}')
            raise InvalidRequestError(f'Invalid request parameters: {message}', cause=e) from e
        except Exception as e:
            if not isinstance(e, OpenAIError):
                logger.error(f'Unexpected error in chat: {e!s}')
                raise OpenAIError(f'Error generating chat completion: {e!s}', cause=e) from e
            raise

    @instrument_request(operation=OperationType.EMBEDDING)
    @retry_on_openai_errors(operation_type=OperationType.EMBEDDING)
    def embed(self: Any, texts: str | list[str], model: str | None=None, **kwargs: Any) -> EmbeddingResponse:
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
        if isinstance(texts, str):
            texts = [texts]
        request = EmbeddingRequest(model=model, input=texts, **kwargs)
        try:
            model_name, request_data = self._prepare_request_data(request)
            response = self._sync_client.embeddings.create(model=model_name, input=texts, **request_data)
            return EmbeddingResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f'Invalid embedding request: {message}')
            raise InvalidRequestError(f'Invalid request parameters: {message}', cause=e) from e
        except Exception as e:
            if not isinstance(e, OpenAIError):
                logger.error(f'Unexpected error in embedding: {e!s}')
                raise OpenAIError(f'Error generating embeddings: {e!s}', cause=e) from e
            raise

    @instrument_async_request(operation=OperationType.COMPLETION)
    @retry_on_openai_errors_async(operation_type=OperationType.COMPLETION)
    async def complete_async(self: Any, prompt: str | list[str], model: str | None=None, max_tokens: int | None=None, temperature: float | None=None, **kwargs: Any) -> CompletionResponse:
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
        request = CompletionRequest(model=model, prompt=prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
        try:
            model_name, request_data = self._prepare_request_data(request)
            response = await self._async_client.completions.create(model=model_name, prompt=prompt, max_tokens=max_tokens, temperature=temperature, **request_data)
            return CompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f'Invalid completion request: {message}')
            raise InvalidRequestError(f'Invalid request parameters: {message}', cause=e) from e
        except Exception as e:
            if not isinstance(e, OpenAIError):
                logger.error(f'Unexpected error in async completion: {e!s}')
                raise OpenAIError(f'Error generating completion: {e!s}', cause=e) from e
            raise

    @instrument_async_request(operation=OperationType.CHAT)
    @retry_on_openai_errors_async(operation_type=OperationType.CHAT)
    async def chat_async(self: Any, messages: list[ChatMessage], model: str | None=None, max_tokens: int | None=None, temperature: float | None=None, **kwargs: Any) -> ChatCompletionResponse:
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
        request = ChatCompletionRequest(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **kwargs)
        try:
            model_name, request_data = self._prepare_request_data(request)
            request_data = self._adjust_params_for_reasoning_model(request_data, model_name)
            api_call_params = {'model': model_name, 'messages': [m.model_dump() for m in messages], **request_data}
            response = await self._async_client.chat.completions.create(**api_call_params)
            return ChatCompletionResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f'Invalid chat request: {message}')
            raise InvalidRequestError(f'Invalid request parameters: {message}', cause=e) from e
        except Exception as e:
            if not isinstance(e, OpenAIError):
                logger.error(f'Unexpected error in async chat: {e!s}')
                raise OpenAIError(f'Error generating chat completion: {e!s}', cause=e) from e
            raise

    @instrument_async_request(operation=OperationType.EMBEDDING)
    @retry_on_openai_errors_async(operation_type=OperationType.EMBEDDING)
    async def embed_async(self: Any, texts: str | list[str], model: str | None=None, **kwargs: Any) -> EmbeddingResponse:
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
        if isinstance(texts, str):
            texts = [texts]
        request = EmbeddingRequest(model=model, input=texts, **kwargs)
        try:
            model_name, request_data = self._prepare_request_data(request)
            response = await self._async_client.embeddings.create(model=model_name, input=texts, **request_data)
            return EmbeddingResponse.model_validate(response.model_dump())
        except openai.BadRequestError as e:
            message = str(e)
            logger.error(f'Invalid embedding request: {message}')
            raise InvalidRequestError(f'Invalid request parameters: {message}', cause=e) from e
        except Exception as e:
            if not isinstance(e, OpenAIError):
                logger.error(f'Unexpected error in async embedding: {e!s}')
                raise OpenAIError(f'Error generating embeddings: {e!s}', cause=e) from e
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
        client = OpenAIClient(endpoint=settings.openai.endpoint, embedding_model=settings.openai.embedding_model, chat_model=settings.openai.chat_model, reasoning_model=settings.openai.reasoning_model, api_version=settings.openai.api_version, timeout=settings.openai.timeout, max_retries=settings.openai.max_retries, retry_backoff_factor=settings.openai.retry_backoff_factor, **kwargs)
        return client
    except Exception as e:
        logger.error(f'Failed to create OpenAI client from settings: {e}')
        raise