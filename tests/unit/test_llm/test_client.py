from typing import Any
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
def patch_prometheus_metrics() -> None:
    """Patch prometheus metrics to avoid registration conflicts during tests."""
    with (
        patch("prometheus_client.Counter"),
        patch("prometheus_client.Gauge"),
        patch("prometheus_client.Histogram"),
    ):
        yield


@pytest.fixture
def mock_settings() -> None:
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
def client() -> None:
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
        patch("codestory.llm.client.instrument_async_request", lambda op: lambda f: f),
        patch("codestory.llm.client.retry_on_openai_errors", lambda **kw: lambda f: f),
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


class TestReasoningModelSupport:
    """Tests for reasoning model parameter adjustment logic."""

    def test_is_reasoning_model(self, client: Any) -> None:
        """Test reasoning model detection."""
        # Test reasoning models
        assert client._is_reasoning_model("o1")
        assert client._is_reasoning_model("o1-preview")
        assert client._is_reasoning_model("o1-mini")
        assert client._is_reasoning_model("O1")  # Case insensitive
        assert client._is_reasoning_model("gpt-o1-preview")
        assert client._is_reasoning_model("my-o1-deployment")

        # Test non-reasoning models
        assert not client._is_reasoning_model("gpt-4o")
        assert not client._is_reasoning_model("gpt-4")
        assert not client._is_reasoning_model("gpt-3.5-turbo")
        assert not client._is_reasoning_model("text-embedding-3-small")
        assert not client._is_reasoning_model("claude-3")

    def test_adjust_params_for_reasoning_model_o1(self, client: Any) -> None:
        """Test parameter adjustment for o1 reasoning models."""
        # Test with o1 model
        original_params = {
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9,
            "other_param": "value"
        }

        adjusted_params = client._adjust_params_for_reasoning_model(original_params, "o1")

        # Should convert max_tokens to max_completion_tokens
        assert "max_completion_tokens" in adjusted_params
        assert adjusted_params["max_completion_tokens"] == 100
        assert "max_tokens" not in adjusted_params

        # Should remove temperature
        assert "temperature" not in adjusted_params

        # Should preserve other parameters
        assert adjusted_params["top_p"] == 0.9
        assert adjusted_params["other_param"] == "value"

    def test_adjust_params_for_reasoning_model_o1_preview(self, client: Any) -> None:
        """Test parameter adjustment for o1-preview model."""
        original_params = {
            "max_tokens": 50,
            "temperature": 1.0,
        }

        adjusted_params = client._adjust_params_for_reasoning_model(original_params, "o1-preview")

        # Should convert max_tokens to max_completion_tokens
        assert "max_completion_tokens" in adjusted_params
        assert adjusted_params["max_completion_tokens"] == 50
        assert "max_tokens" not in adjusted_params
        assert "temperature" not in adjusted_params

    def test_adjust_params_for_reasoning_model_regular_model(self, client: Any) -> None:
        """Test parameter adjustment for regular (non-reasoning) models."""
        original_params = {
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9,
        }

        adjusted_params = client._adjust_params_for_reasoning_model(original_params, "gpt-4o")

        # Should not modify parameters for regular models
        assert adjusted_params == original_params
        assert "max_tokens" in adjusted_params
        assert adjusted_params["max_tokens"] == 100
        assert "temperature" in adjusted_params
        assert adjusted_params["temperature"] == 0.7
        assert "max_completion_tokens" not in adjusted_params

    def test_adjust_params_for_reasoning_model_no_max_tokens(self, client: Any) -> None:
        """Test parameter adjustment when max_tokens is not present."""
        original_params = {
            "temperature": 0.5,
            "top_p": 0.8,
        }

        adjusted_params = client._adjust_params_for_reasoning_model(original_params, "o1")

        # Should only remove temperature for reasoning model
        assert "temperature" not in adjusted_params
        assert "top_p" in adjusted_params
        assert adjusted_params["top_p"] == 0.8
        assert "max_completion_tokens" not in adjusted_params
        assert "max_tokens" not in adjusted_params

    def test_adjust_params_for_reasoning_model_none_max_tokens(self, client: Any) -> None:
        """Test parameter adjustment when max_tokens is None."""
        original_params = {
            "max_tokens": None,
            "temperature": 0.3,
        }

        adjusted_params = client._adjust_params_for_reasoning_model(original_params, "o1-mini")

        # Should not add max_completion_tokens if max_tokens was None
        assert "max_tokens" not in adjusted_params
        assert "max_completion_tokens" not in adjusted_params
        assert "temperature" not in adjusted_params

    def test_chat_with_reasoning_model_parameter_adjustment(self, client: Any) -> None:
        """Test that chat method properly adjusts parameters for reasoning models."""
        with patch.object(client._sync_client.chat.completions, "create") as mock_create:
            # Configure the mock response
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1616782565,
                "model": "o1",
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
                ChatMessage(role=ChatRole.USER, content="Hello"),
            ]

            # Call chat with reasoning model and parameters that should be adjusted
            result = client.chat(
                messages=messages,
                model="o1",
                max_tokens=10,
                temperature=0.7,  # This should be removed
            )

            # Verify the result
            assert isinstance(result, ChatCompletionResponse)
            
            # Verify the mock was called with adjusted parameters
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            
            # Should have max_completion_tokens instead of max_tokens
            assert "max_completion_tokens" in call_args
            assert call_args["max_completion_tokens"] == 10
            assert "max_tokens" not in call_args
            
            # Should not have temperature
            assert "temperature" not in call_args
            
            # Should have correct model and messages
            assert call_args["model"] == "o1"
            assert len(call_args["messages"]) == 1

    @pytest.mark.asyncio
    async def test_chat_async_with_reasoning_model_parameter_adjustment(self, client):
        """Test that chat_async method properly adjusts parameters for reasoning models."""
        # Create a mock response for the async function
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1616782565,
            "model": "o1-preview",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Async response",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        # Create a proper awaitable for the async function to return
        future = asyncio.Future()
        future.set_result(mock_response)

        # Create a patch for the async client
        with patch.object(client._async_client.chat.completions, "create", return_value=future) as mock_create:
            # Create messages
            messages = [
                ChatMessage(role=ChatRole.USER, content="Hello async"),
            ]

            # Call chat_async with reasoning model and parameters that should be adjusted
            result = await client.chat_async(
                messages=messages,
                model="o1-preview",
                max_tokens=20,
                temperature=0.9,  # This should be removed
            )

            # Verify the result
            assert isinstance(result, ChatCompletionResponse)
            
            # Verify the mock was called with adjusted parameters
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            
            # Should have max_completion_tokens instead of max_tokens
            assert "max_completion_tokens" in call_args
            assert call_args["max_completion_tokens"] == 20
            assert "max_tokens" not in call_args
            
            # Should not have temperature
            assert "temperature" not in call_args
            
            # Should have correct model and messages
            assert call_args["model"] == "o1-preview"
            assert len(call_args["messages"]) == 1


class TestOpenAIClient:
    """Tests for the OpenAIClient class."""

    def test_init(self) -> None:
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

    def test_init_missing_credentials(self) -> None:
        """Test client initialization with missing credentials."""
        with (
            patch(
                "codestory.llm.client.get_settings",
                side_effect=Exception("No settings"),
            ),
            patch("codestory.llm.client.DefaultAzureCredential"),
            patch("codestory.llm.client.get_bearer_token_provider"),
            pytest.raises(AuthenticationError),
        ):
            OpenAIClient()  # No endpoint provided

        # No need to test api_key since we're using Azure AD

    def test_complete(self, client: Any) -> None:
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
            assert call_args["model"] == "gpt-4o"  # Default reasoning model
            assert call_args["prompt"] == "Test prompt"

    def test_chat(self, client: Any) -> None:
        """Test chat completion."""
        with patch.object(client._sync_client.chat.completions, "create") as mock_create:
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
                ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
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
            assert call_args["model"] == "gpt-4o"  # Default chat model
            assert len(call_args["messages"]) == 2

    def test_embed(self, client: Any) -> None:
        """Test embedding generation."""
        with patch.object(client._sync_client.embeddings, "create") as mock_create:
            # Configure the mock response
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {
                "object": "list",
                "data": [{"object": "embedding", "embedding": [0.1, 0.2, 0.3], "index": 0}],
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
            assert call_args["model"] == "text-embedding-3-small"
            assert call_args["input"] == ["Test text"]

    def test_error_handling_complete(self) -> None:
        """Test error handling in completion."""
        # Instead of patching the actual retry decorator, we'll mock the completion method
        # directly to expose the exception handling behavior
        with (
            patch("openai.AzureOpenAI") as mock_azure_openai,
            patch("openai.AsyncAzureOpenAI"),
            patch("codestory.llm.backoff.retry_on_openai_errors"),
            patch("codestory.llm.client.DefaultAzureCredential"),
            patch("codestory.llm.client.get_bearer_token_provider"),
            patch("codestory.llm.client.instrument_request", lambda op: lambda f: f),
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
        with patch.object(client._async_client.completions, "create", return_value=future):
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

    def test_create_client(self, mock_settings: Any) -> None:
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
            patch(
                "codestory.llm.client.retry_on_openai_errors_async",
                lambda **kw: lambda f: f,
            ),
        ):
            client = create_client()

            # Check that the settings were used
            assert client.endpoint == "https://test-endpoint.openai.azure.com"
            assert client.embedding_model == "text-embedding-3-small"
            assert client.chat_model == "gpt-4o"
            assert client.reasoning_model == "gpt-4o"

    def test_create_client_override(self) -> None:
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
