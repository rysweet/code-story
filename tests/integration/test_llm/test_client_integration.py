from typing import Any
"""Integration tests for OpenAI client.

These tests use real OpenAI API access and require valid credentials to be successful.
They are skipped by default unless the --run-openai option is provided to pytest.
"""

import pytest

from codestory.config.settings import get_settings
from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole

# Mark all tests to be skipped unless explicitly enabled
pytestmark = [pytest.mark.integration, pytest.mark.openai]


@pytest.mark.integration
def test_client_creation(openai_credentials: Any) -> None:
    """Test client creation with real credentials.

    This verifies that the client can be created successfully with the
    credentials provided in the environment.
    """
    try:
        client = create_client()

        # Verify client was created with correct endpoint
        assert client.endpoint == openai_credentials["endpoint"]

        # Verify client has expected model values
        assert client.chat_model is not None
        assert client.embedding_model is not None
        assert client.reasoning_model is not None
    except Exception as e:
        pytest.fail(f"Failed to create client: {e}")


@pytest.mark.integration
def test_client: Any_configuration(client) -> None:
    """Test client configuration with expected values."""
    # Get current settings
    settings = get_settings()

    # Verify client configuration matches settings
    assert client.endpoint == settings.openai.endpoint
    assert client.embedding_model == settings.openai.embedding_model
    assert client.chat_model == settings.openai.chat_model
    assert client.reasoning_model == settings.openai.reasoning_model


@pytest.mark.integration
def test_chat_completion(client: Any) -> None:
    """Test chat completion with real API.

    This test verifies that the client can successfully make a chat completion
    request to the real API and receive a valid response.
    """
    # Prepare a simple chat message
    messages = [
        ChatMessage(
            role=ChatRole.SYSTEM,
            content="You are a helpful assistant that answers concisely.",
        ),
        ChatMessage(role=ChatRole.USER, content="What is 2+2?"),
    ]

    # Make the request
    result = client.chat(messages)

    # Verify response structure
    assert result.model is not None
    assert len(result.choices) > 0
    assert result.choices[0].message.content is not None

    # Verify there is a reasonable answer containing "4"
    assert "4" in result.choices[0].message.content

    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.usage.total_tokens > 0


@pytest.mark.integration
def test_reasoning_model_parameter_handling(client: Any) -> None:
    """Test that reasoning models use correct parameters (max_completion_tokens).
    
    This test verifies that when using reasoning models like o1, the client
    properly converts max_tokens to max_completion_tokens and omits temperature.
    """
    # Get current settings to check if we have a reasoning model configured
    settings = get_settings()
    reasoning_model = settings.openai.reasoning_model
    
    # Skip if no reasoning model is configured or if it's not actually a reasoning model
    if not reasoning_model or not any(rm in reasoning_model.lower() for rm in ["o1", "o1-preview", "o1-mini"]):
        pytest.skip(f"No reasoning model configured or '{reasoning_model}' is not a reasoning model")
    
    # Prepare a simple chat message that should work with reasoning models
    messages = [
        ChatMessage(
            role=ChatRole.SYSTEM,
            content="You are a helpful assistant.",
        ),
        ChatMessage(
            role=ChatRole.USER,
            content="What is 2+2? Answer briefly."
        ),
    ]

    # Test with the reasoning model - this should use max_completion_tokens internally
    result = client.chat(
        messages=messages,
        model=reasoning_model,
        max_tokens=10,  # This should be converted to max_completion_tokens
        # Note: temperature is intentionally omitted as reasoning models don't support it
    )

    # Verify response structure
    assert result.model is not None
    assert len(result.choices) > 0
    assert result.choices[0].message.content is not None
    assert "4" in result.choices[0].message.content

    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.usage.total_tokens > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reasoning_model_async_parameter_handling(client):
    """Test async reasoning model parameter handling.
    
    This test verifies that the async version properly handles reasoning model
    parameters just like the sync version.
    """
    # Get current settings to check if we have a reasoning model configured
    settings = get_settings()
    reasoning_model = settings.openai.reasoning_model
    
    # Skip if no reasoning model is configured or if it's not actually a reasoning model
    if not reasoning_model or not any(rm in reasoning_model.lower() for rm in ["o1", "o1-preview", "o1-mini"]):
        pytest.skip(f"No reasoning model configured or '{reasoning_model}' is not a reasoning model")
    
    # Prepare a simple chat message
    messages = [
        ChatMessage(
            role=ChatRole.SYSTEM,
            content="You are a helpful assistant.",
        ),
        ChatMessage(
            role=ChatRole.USER,
            content="What is the capital of France? Answer with just the city name."
        ),
    ]

    # Test async with the reasoning model
    result = await client.chat_async(
        messages=messages,
        model=reasoning_model,
        max_tokens=10,  # This should be converted to max_completion_tokens
        # Note: temperature is intentionally omitted as reasoning models don't support it
    )

    # Verify response structure
    assert result.model is not None
    assert len(result.choices) > 0
    assert result.choices[0].message.content is not None
    assert "Paris" in result.choices[0].message.content

    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.usage.total_tokens > 0


@pytest.mark.integration
def test_regular_model_vs_reasoning_model_parameters(client: Any) -> None:
    """Test that regular models and reasoning models use different parameters.
    
    This test verifies that regular models can use temperature while reasoning
    models cannot, demonstrating the parameter adjustment logic works correctly.
    """
    # Get current settings
    settings = get_settings()
    chat_model = settings.openai.chat_model
    reasoning_model = settings.openai.reasoning_model
    
    # Skip if reasoning model is not actually a reasoning model
    if not reasoning_model or not any(rm in reasoning_model.lower() for rm in ["o1", "o1-preview", "o1-mini"]):
        pytest.skip(f"No reasoning model configured or '{reasoning_model}' is not a reasoning model")
    
    # Prepare a simple test message
    messages = [
        ChatMessage(
            role=ChatRole.SYSTEM,
            content="You are a helpful assistant.",
        ),
        ChatMessage(
            role=ChatRole.USER,
            content="Say 'hello' in response."
        ),
    ]

    # Test regular model with temperature (should work)
    regular_result = client.chat(
        messages=messages,
        model=chat_model,
        max_tokens=5,
        temperature=0.1,  # Regular models support temperature
    )
    
    # Verify regular model response
    assert regular_result.model is not None
    assert len(regular_result.choices) > 0
    assert regular_result.choices[0].message.content is not None

    # Test reasoning model without temperature (should work)
    reasoning_result = client.chat(
        messages=messages,
        model=reasoning_model,
        max_tokens=5,
        # No temperature parameter - reasoning models don't support it
    )
    
    # Verify reasoning model response
    assert reasoning_result.model is not None
    assert len(reasoning_result.choices) > 0
    assert reasoning_result.choices[0].message.content is not None

    # Both should have token usage
    assert regular_result.usage.total_tokens > 0
    assert reasoning_result.usage.total_tokens > 0


@pytest.mark.integration
def test_embedding(client: Any) -> None:
    """Test embedding generation with real API.

    This test verifies that the client can successfully generate embeddings
    using the real API.
    """
    # Prepare a simple text for embedding
    text = "This is a test of the embedding API."

    # Make the request
    result = client.embed(text)

    # Verify response structure
    assert result.model is not None
    assert len(result.data) == 1
    assert len(result.data[0].embedding) > 0  # Should have a non-empty vector

    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.total_tokens > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_async(client):
    """Test async chat completion with real API.

    This test verifies that the client can successfully make an async chat
    completion request to the real API.
    """
    # Prepare a simple chat message
    messages = [
        ChatMessage(
            role=ChatRole.SYSTEM,
            content="You are a helpful assistant that answers concisely.",
        ),
        ChatMessage(role=ChatRole.USER, content="What is the capital of France?"),
    ]

    # Make the async request
    result = await client.chat_async(messages)

    # Verify response structure
    assert result.model is not None
    assert len(result.choices) > 0
    assert result.choices[0].message.content is not None

    # Verify there is a reasonable answer containing "Paris"
    assert "Paris" in result.choices[0].message.content

    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.usage.total_tokens > 0
