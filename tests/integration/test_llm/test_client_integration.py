"""Integration tests for OpenAI client.

These tests use real OpenAI API access and require valid credentials to be successful.
They are skipped by default unless the --run-openai option is provided to pytest.
"""

import pytest

from codestory.config.settings import get_settings
from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole

# Mark all tests to be skipped unless explicitly enabled
pytestmark = [
    pytest.mark.integration,
    pytest.mark.openai
]


@pytest.mark.integration
def test_client_creation(openai_credentials):
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
def test_client_configuration(client):
    """Test client configuration with expected values."""
    # Get current settings
    settings = get_settings()
    
    # Verify client configuration matches settings
    assert client.endpoint == settings.openai.endpoint
    assert client.embedding_model == settings.openai.embedding_model
    assert client.chat_model == settings.openai.chat_model
    assert client.reasoning_model == settings.openai.reasoning_model


@pytest.mark.integration
def test_chat_completion(client):
    """Test chat completion with real API.
    
    This test verifies that the client can successfully make a chat completion
    request to the real API and receive a valid response.
    """
    # Prepare a simple chat message
    messages = [
        ChatMessage(
            role=ChatRole.SYSTEM, 
            content="You are a helpful assistant that answers concisely."
        ),
        ChatMessage(role=ChatRole.USER, content="What is 2+2?")
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
def test_embedding(client):
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
            content="You are a helpful assistant that answers concisely."
        ),
        ChatMessage(role=ChatRole.USER, content="What is the capital of France?")
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