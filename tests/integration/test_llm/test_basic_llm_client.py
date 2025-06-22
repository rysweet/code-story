import os
import pytest
from codestory.llm.client import OpenAIClient
from codestory.llm.models import ChatMessage, ChatRole

@pytest.mark.integration
def test_basic_llm_client_chat():
    print("RUNNING test_basic_llm_client_chat")
    # Use environment variables for endpoint, deployment, and API key
    endpoint = os.environ.get("AZURE_OPENAI__ENDPOINT", "https://ai-adapt-oai-eastus2.openai.azure.com/")
    deployment = os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID", "o3")
    api_version = os.environ.get("AZURE_OPENAI__API_VERSION", "2025-01-01-preview")
    api_key = os.environ.get("AZURE_OPENAI__API_KEY")
    assert api_key, "AZURE_OPENAI__API_KEY must be set"

    client = OpenAIClient(
        endpoint=endpoint,
        chat_model=deployment,
        api_version=api_version,
    )

    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(role=ChatRole.USER, content="What is 2+2?"),
    ]
    result = client.chat(messages=messages, model=deployment, max_tokens=10)
    assert result.model is not None
    assert len(result.choices) > 0
    assert result.choices[0].message.content is not None
    assert "4" in result.choices[0].message.content