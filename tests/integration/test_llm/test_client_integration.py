"""Integration tests for OpenAI client.

These tests interact with the actual Azure OpenAI API and require valid credentials.
They are intended to be run manually or in CI with appropriate secrets.

To skip these tests when credentials are not available, they are all marked with
the 'integration' and 'openai' markers.
"""

import os
import pytest
from typing import List

from src.codestory.llm.client import OpenAIClient, create_client
from src.codestory.llm.models import ChatMessage, ChatRole
from src.codestory.config.settings import get_settings, refresh_settings


# Skip all tests if the required credentials are not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.openai,
    pytest.mark.skipif(
        not os.environ.get("AZURE_OPENAI_API_KEY") and not os.environ.get("OPENAI_API_KEY"),
        reason="No OpenAI API credentials available"
    )
]


@pytest.fixture
def client() -> OpenAIClient:
    """Create a client using environment credentials."""
    # Ensure settings are refreshed
    refresh_settings()
    
    # Try to get credentials from settings
    try:
        return create_client()
    except Exception:
        # Fallback to environment variables if settings fail
        api_key = os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or "https://api.openai.com/v1"
        
        return OpenAIClient(
            api_key=api_key,
            endpoint=endpoint
        )


@pytest.mark.xfail(reason="Requires valid API credentials")
def test_chat_integration(client: OpenAIClient):
    """Test chat completion with real API."""
    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(role=ChatRole.USER, content="What is the capital of France?")
    ]
    
    result = client.chat(messages)
    
    # Verify response structure
    assert result.model is not None
    assert len(result.choices) > 0
    assert result.choices[0].message.content is not None
    assert "Paris" in result.choices[0].message.content
    
    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.usage.total_tokens > 0


@pytest.mark.xfail(reason="Requires valid API credentials")
def test_embed_integration(client: OpenAIClient):
    """Test embedding generation with real API."""
    text = "This is a test sentence for embedding."
    
    result = client.embed(text)
    
    # Verify response structure
    assert result.model is not None
    assert len(result.data) > 0
    assert len(result.data[0].embedding) > 0
    
    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.total_tokens > 0


@pytest.mark.xfail(reason="Requires valid API credentials")
@pytest.mark.asyncio
async def test_chat_async_integration(client: OpenAIClient):
    """Test async chat completion with real API."""
    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(role=ChatRole.USER, content="What is the tallest mountain in the world?")
    ]
    
    result = await client.chat_async(messages)
    
    # Verify response structure
    assert result.model is not None
    assert len(result.choices) > 0
    assert result.choices[0].message.content is not None
    assert "Everest" in result.choices[0].message.content
    
    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.usage.total_tokens > 0


@pytest.mark.xfail(reason="Requires valid API credentials")
@pytest.mark.asyncio
async def test_embed_async_integration(client: OpenAIClient):
    """Test async embedding generation with real API."""
    texts = ["This is the first test sentence.", "This is the second test sentence."]
    
    result = await client.embed_async(texts)
    
    # Verify response structure
    assert result.model is not None
    assert len(result.data) == 2
    assert len(result.data[0].embedding) > 0
    assert len(result.data[1].embedding) > 0
    
    # Verify token usage was recorded
    assert result.usage.prompt_tokens > 0
    assert result.usage.total_tokens > 0