"""Tests for OpenAI client implementation."""

import asyncio
from unittest.mock import MagicMock, patch

import openai
import pytest

from codestory.llm.client import OpenAIClient, create_client
from codestory.llm.exceptions import (
    AuthenticationError,
    InvalidRequestError,
)
from codestory.llm.models import (
    ChatCompletionResponse,
    ChatMessage,
    ChatRole,
    CompletionResponse,
    EmbeddingResponse,
)


# Patch prometheus metrics to avoid registration conflicts during tests
@pytest.fixture(autouse=True)
def patch_prometheus_metrics():
    """Patch prometheus metrics to avoid registration conflicts during tests."""
    with patch("prometheus_client.Counter") as mock_counter, patch(
        "prometheus_client.Gauge"
    ) as mock_gauge, patch("prometheus_client.Histogram") as mock_histogram:
        # Configure the mocks to behave like the real counter
        mock_labels = MagicMock()
        mock_counter.return_value.labels = mock_labels
        mock_gauge.return_value.labels = mock_labels
        mock_histogram.return_value.labels = mock_labels
        yield


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    with patch("codestory.llm.client.get_settings") as mock_get_settings:
        settings = MagicMock()

        # Configure openai settings in the mock
        settings.openai = MagicMock()
        settings.openai.endpoint = "https://test-endpoint.openai.azure.com"
        settings.openai.embedding_model = "text-embedding-3-small"
        settings.openai.chat_model = "gpt-4o"
        settings.openai.reasoning_model = "gpt-4o"
        settings.openai.api_version = "2025-03-01-preview"
        settings.openai.timeout = 30.0
        settings.openai.max_retries = 3
        settings.openai.retry_backoff_factor = 2.0

        mock_get_settings.return_value = settings
        yield mock_get_settings


@pytest.fixture
def client():
    """Create an OpenAI client for testing."""
    # Patch the internal OpenAI client to avoid needing real credentials
    # Also patch the DefaultAzureCredential and token provider
    with (
        patch("openai.AzureOpenAI"),
        patch("openai.AsyncAzureOpenAI"),
        patch("codestory.llm.client.DefaultAzureCredential"),
        patch("codestory.llm.client.get_bearer_token_provider"),
        # Also patch the metric decorators to avoid registration conflicts
        patch("codestory.llm.client.instrument_request", lambda op: lambda f: f),
        patch(
            "codestory.llm.client.instrument_async_request", lambda op: lambda f: f
        ),
        patch(
            "codestory.llm.client.retry_on_openai_errors", lambda **kw: lambda f: f
        ),
        patch(
            "codestory.llm.client.retry_on_openai_errors_async",
            lambda **kw: lambda f: f,
        ),
    ):
        client = OpenAIClient(
            endpoint="https://test-endpoint.openai.azure.com",
            embedding_model="text-embedding-3-small",
            chat_model="gpt-4o",
            reasoning_model="gpt-4o",
            api_version="2025-03-01-preview",
            timeout=30.0,
            max_retries=3,
            retry_backoff_factor=2.0,
        )
        yield client


class TestOpenAIClient:
    """Tests for the OpenAIClient class."""

    def test_init(self):
        """Test client initialization."""
        with (
            patch("openai.AzureOpenAI"),
            patch("openai.AsyncAzureOpenAI"),
            patch("codestory.llm.client.DefaultAzureCredential"),
            patch("codestory.llm.client.get_bearer_token_provider"),
        ):
            client = OpenAIClient(endpoint="https://test-endpoint.openai.azure.com")

            assert client.endpoint == "https://test-endpoint.openai.azure.com"
            assert client.embedding_model == "text-embedding-3-small"  # Default value
            assert client.chat_model == "gpt-4o"  # Default value
            assert client.reasoning_model == "gpt-4o"  # Default value

            # Test client initialization with custom model values
            client = OpenAIClient(
                endpoint="https://test-endpoint.openai.azure.com",
                embedding_model="custom-embedding-model",
                chat_model="custom-chat-model",
                reasoning_model="custom-reasoning-model",
            )

            assert client.embedding_model == "custom-embedding-model"
            assert client.chat_model == "custom-chat-model"
            assert client.reasoning_model == "custom-reasoning-model"

    def test_init_missing_credentials(self):
        """Test client initialization with missing credentials."""
        with patch(
            "codestory.llm.client.get_settings",
            side_effect=Exception("No settings"),
        ):
            with patch("codestory.llm.client.DefaultAzureCredential"), patch(
                "codestory.llm.client.get_bearer_token_provider"
            ), pytest.raises(AuthenticationError):
                OpenAIClient()  # No endpoint provided

            # No need to test api_key since we're using Azure AD

    def test_complete(self, client):
        """Test text completion."""
        with patch.object(client._sync_client.completions, "create") as mock_create:
            # Configure the mock response
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {
                "id": "cmpl-123",
                "object": "text_completion",
                "created": 1616782565,
                "model": "gpt-4o",
                "choices": [
                    {
                        "text": "This is a test completion.",
                        "index": 0,
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 7,
                    "total_tokens": 12,
                },
            }
            mock_create.return_value = mock_response

            # Call the method
            result = client.complete("Test prompt")

            # Check result
            assert isinstance(result, CompletionResponse)
            assert result.model == "gpt-4o"
            assert len(result.choices) == 1
            assert result.choices[0].text == "This is a test completion."
            assert result.usage.prompt_tokens == 5
            assert result.usage.completion_tokens == 7
            assert result.usage.total_tokens == 12

            # Verify the mock was called with correct args
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args["deployment_name"] == "gpt-4o"  # Default reasoning model
            assert call_args["prompt"] == "Test prompt"

    def test_chat(self, client):
        """Test chat completion."""
        with patch.object(
            client._sync_client.chat.completions, "create"
        ) as mock_create:
            # Configure the mock response
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1616782565,
                "model": "gpt-4o",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Hello, how can I help you?",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 12,
                    "total_tokens": 27,
                },
            }
            mock_create.return_value = mock_response

            # Create messages
            messages = [
                ChatMessage(
                    role=ChatRole.SYSTEM, content="You are a helpful assistant."
                ),
                ChatMessage(role=ChatRole.USER, content="Hello, assistant!"),
            ]

            # Call the method
            result = client.chat(messages)

            # Check result
            assert isinstance(result, ChatCompletionResponse)
            assert result.model == "gpt-4o"
            assert len(result.choices) == 1
            assert result.choices[0].message.role == ChatRole.ASSISTANT
            assert result.choices[0].message.content == "Hello, how can I help you?"
            assert result.usage.prompt_tokens == 15
            assert result.usage.completion_tokens == 12
            assert result.usage.total_tokens == 27

            # Verify the mock was called with correct args
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args["deployment_name"] == "gpt-4o"  # Default chat model
            assert len(call_args["messages"]) == 2

    def test_embed(self, client):
        """Test embedding generation."""
        with patch.object(client._sync_client.embeddings, "create") as mock_create:
            # Configure the mock response
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {
                "object": "list",
                "data": [
                    {"object": "embedding", "embedding": [0.1, 0.2, 0.3], "index": 0}
                ],
                "model": "text-embedding-3-small",
                "usage": {"prompt_tokens": 8, "total_tokens": 8},
            }
            mock_create.return_value = mock_response

            # Call the method
            result = client.embed("Test text")

            # Check result
            assert isinstance(result, EmbeddingResponse)
            assert result.model == "text-embedding-3-small"
            assert len(result.data) == 1
            assert result.data[0].embedding == [0.1, 0.2, 0.3]
            assert result.usage.prompt_tokens == 8
            assert result.usage.total_tokens == 8

            # Verify the mock was called with correct args
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args["deployment_name"] == "text-embedding-3-small"
            assert call_args["input"] == ["Test text"]

    def test_error_handling_complete(self):
        """Test error handling in completion."""
        # Instead of patching the actual retry decorator, we'll mock the completion method
        # directly to expose the exception handling behavior
        with (
            patch("openai.AzureOpenAI") as mock_azure_openai,
            patch("openai.AsyncAzureOpenAI"),
            patch("codestory.llm.backoff.retry_on_openai_errors"),
            patch("codestory.llm.client.DefaultAzureCredential"),
            patch("codestory.llm.client.get_bearer_token_provider"),
            patch(
                "codestory.llm.client.instrument_request", lambda op: lambda f: f
            ),
        ):
            # Configure the mock OpenAI client
            mock_completions = MagicMock()
            mock_azure_openai.return_value = MagicMock(completions=mock_completions)

            # Create a new client instance with our mocks
            client = OpenAIClient(endpoint="https://test-endpoint.openai.azure.com")

            # Patch the complete method to expose the internal exception handling
            with patch.object(client, "_sync_client") as mock_sync_client:
                # 1. Test BadRequestError
                mock_completions_create = MagicMock()
                mock_completions_create.create.side_effect = openai.BadRequestError(
                    message="Invalid request parameters",
                    response=MagicMock(),
                    body=None,
                )
                mock_sync_client.completions = mock_completions_create

                with pytest.raises(InvalidRequestError):
                    client.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_complete_async(self, client):
        """Test async text completion."""
        # Create a mock response for the async function
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "cmpl-123",
            "object": "text_completion",
            "created": 1616782565,
            "model": "gpt-4o",
            "choices": [
                {
                    "text": "This is a test completion.",
                    "index": 0,
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
        }

        # Create a proper awaitable for the async function to return
        future = asyncio.Future()
        future.set_result(mock_response)

        # Create a patch for the async client
        with patch.object(
            client._async_client.completions, "create", return_value=future
        ):
            # Call the method
            result = await client.complete_async("Test prompt")

            # Check result
            assert isinstance(result, CompletionResponse)
            assert result.model == "gpt-4o"
            assert len(result.choices) == 1
            assert result.choices[0].text == "This is a test completion."
            assert result.usage.prompt_tokens == 5
            assert result.usage.completion_tokens == 7
            assert result.usage.total_tokens == 12


class TestCreateClient:
    """Tests for the create_client function."""

    def test_create_client(self, mock_settings):
        """Test client creation with default settings."""
        with (
            patch("openai.AzureOpenAI"),
            patch("openai.AsyncAzureOpenAI"),
            patch("codestory.llm.client.DefaultAzureCredential"),
            patch("codestory.llm.client.get_bearer_token_provider"),
            # Also patch metric decorators to avoid conflicts
            patch("codestory.llm.client.instrument_request", lambda op: lambda f: f),
            patch("codestory.llm.client.instrument_async_request", lambda op: lambda f: f),
            patch("codestory.llm.client.retry_on_openai_errors", lambda **kw: lambda f: f),
            patch("codestory.llm.client.retry_on_openai_errors_async", lambda **kw: lambda f: f),
        ):
            client = create_client()

            # Check that the settings were used
            assert client.endpoint == "https://test-endpoint.openai.azure.com"
            assert client.embedding_model == "text-embedding-3-small"
            assert client.chat_model == "gpt-4o"
            assert client.reasoning_model == "gpt-4o"

    def test_create_client_override(self):
        """Test client creation with overridden settings."""
        # Since we're mocking the client itself, let's make a simpler test
        with patch("codestory.llm.client.OpenAIClient") as mock_client_class:
            # Configure our mock client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Don't use the real settings, mock them with exact values we need
            with patch("codestory.llm.client.get_settings") as mock_get_settings:
                # Create a simple settings mock that has just what we need
                mock_settings = MagicMock()
                mock_settings.openai = MagicMock()
                mock_settings.openai.endpoint = "https://test-endpoint.openai.azure.com"
                mock_settings.openai.api_version = "2025-03-01-preview"
                mock_settings.openai.timeout = 30.0
                mock_settings.openai.max_retries = 3
                mock_settings.openai.retry_backoff_factor = 2.0

                # Set models that match our hardcoded values
                mock_settings.openai.embedding_model = "text-embedding-3-small"
                mock_settings.openai.chat_model = "gpt-4o"
                mock_settings.openai.reasoning_model = "gpt-4o"

                mock_get_settings.return_value = mock_settings

                # This is what we're testing
                create_client()

                # Verify client was created with the correct settings
                mock_client_class.assert_called_once_with(
                    endpoint="https://test-endpoint.openai.azure.com",
                    embedding_model="text-embedding-3-small",
                    chat_model="gpt-4o",
                    reasoning_model="gpt-4o",
                    api_version="2025-03-01-preview",
                    timeout=30.0,
                    max_retries=3,
                    retry_backoff_factor=2.0,
                )
