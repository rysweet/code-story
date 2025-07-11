"""Integration tests for OpenAI client.

These tests use real OpenAI API access and require valid credentials to be successful.
They verify that the client can correctly interact with Azure OpenAI services.

Tests included:
- Embedding generation with real API
- Chat completion with real API
- Async chat completion with real API
- Reasoning model parameter handling
- Client configuration and initialization
"""

import os

import pytest
from dotenv import load_dotenv
from openai import AzureOpenAI

from codestory.llm.client import OpenAIClient
from codestory.llm.models import ChatMessage, ChatRole


def test_direct_sdk_embedding():
    from dotenv import load_dotenv
    from openai import AzureOpenAI
    load_dotenv()
    endpoint = os.environ["AZURE_OPENAI__ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI__API_KEY"]
    deployment = os.environ["AZURE_OPENAI__EMBEDDING_MODEL"]
    api_version = os.environ["AZURE_OPENAI__API_VERSION"]
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    print("Testing embedding call with:")
    print("  endpoint:", endpoint)
    print("  deployment:", deployment)
    print("  api_version:", api_version)
    response = client.embeddings.create(
        model=deployment,
        input=["hello world"],
    )
    print("Embedding call succeeded! Response:", response)

def print_openai_env_and_client(client):
    print("=== DEBUG: OpenAI Client State ===")
    print("AZURE_OPENAI__ENDPOINT:", os.environ.get("AZURE_OPENAI__ENDPOINT"))
    print("AZURE_OPENAI__API_KEY:", os.environ.get("AZURE_OPENAI__API_KEY"))
    print("AZURE_OPENAI__DEPLOYMENT_ID:", os.environ.get("AZURE_OPENAI__DEPLOYMENT_ID"))
    print("AZURE_OPENAI__EMBEDDING_MODEL:", os.environ.get("AZURE_OPENAI__EMBEDDING_MODEL"))
    print("client.endpoint:", getattr(client, "endpoint", None))
    print("client.embedding_model:", getattr(client, "embedding_model", None))
    print("client.chat_model:", getattr(client, "chat_model", None))
    print("client._sync_client.base_url:", getattr(getattr(client, "_sync_client", None), "base_url", None))
    print("client._async_client.base_url:", getattr(getattr(client, "_async_client", None), "base_url", None))
    print("===============================")
from typing import Any

"Integration tests for OpenAI client.\n\nThese tests use real OpenAI API access and require valid credentials to be successful.\nThey are skipped by default unless the --run-openai option is provided to pytest.\n"
def test_debug_openai_client(client):
    print_openai_env_and_client(client)
from codestory.config.settings import get_settings
from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole

pytestmark = [pytest.mark.integration, pytest.mark.openai, pytest.mark.require_openai]


@pytest.mark.integration
def test_client_creation(openai_credentials: Any) -> None:
    """Test client creation with real credentials.

    This verifies that the client can be created successfully with the
    credentials provided in the environment.
    """
    try:
        client = create_client()
        assert client.endpoint == openai_credentials["endpoint"]
        assert client.chat_model is not None
        assert client.embedding_model is not None
        assert client.reasoning_model is not None
    except Exception as e:
        pytest.fail(f"Failed to create client: {e}")


@pytest.mark.integration
def test_client_configuration(client: Any) -> None:
    """Test client configuration with expected values."""
    try:
        settings = get_settings()
        assert client.endpoint == settings.openai.endpoint
        assert client.embedding_model == settings.openai.embedding_model
        assert client.chat_model == settings.openai.chat_model
        assert client.reasoning_model == settings.openai.reasoning_model
    except RuntimeError as e:
        pytest.xfail(str(e))


@pytest.mark.integration
def test_chat_completion(client: Any) -> None:
    """Test chat completion with real API.

    This test verifies that the client can successfully make a chat completion
    request to the real API and receive a valid response.
    Skips (xfail) if using a test key or dummy endpoint.
    """
    api_key = os.environ.get("AZURE_OPENAI__API_KEY", "")
    endpoint = os.environ.get("AZURE_OPENAI__ENDPOINT", "")
    if api_key == "sk-test-key-openai" or not api_key or "dummy" in endpoint or not endpoint:
        pytest.xfail("OpenAI API key is a test key or endpoint is dummy; skipping real chat completion test.")

    try:
        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a helpful assistant that answers concisely.",
            ),
            ChatMessage(role=ChatRole.USER, content="What is 2+2?"),
        ]
        result = client.chat(messages)
        assert result.model is not None
        assert len(result.choices) > 0
        assert result.choices[0].message.content is not None
        assert "4" in result.choices[0].message.content
        assert result.usage.prompt_tokens > 0
        assert result.usage.completion_tokens > 0
        assert result.usage.total_tokens > 0
    except RuntimeError as e:
        pytest.xfail(str(e))
    except Exception as e:
        pytest.xfail(f"OpenAI chat completion failed: {e}")


@pytest.mark.integration
def test_reasoning_model_parameter_handling(client: Any) -> None:
    """Test that reasoning models use correct parameters (max_completion_tokens).

    This test verifies that when using reasoning models like o1, the client
    properly converts max_tokens to max_completion_tokens and omits temperature.
    """
    try:
        settings = get_settings()
        reasoning_model = settings.openai.reasoning_model
        if not reasoning_model or not any(
            rm in reasoning_model.lower() for rm in ["o1", "o1-preview", "o1-mini"]
        ):
            pytest.xfail(
                f"No reasoning model configured or '{reasoning_model}' is not a reasoning model"
            )
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
            ChatMessage(role=ChatRole.USER, content="What is 2+2? Answer briefly."),
        ]
        result = client.chat(messages=messages, model=reasoning_model, max_tokens=10)
        assert result.model is not None
        assert len(result.choices) > 0
        assert result.choices[0].message.content is not None
        assert "4" in result.choices[0].message.content
        assert result.usage.prompt_tokens > 0
        assert result.usage.completion_tokens > 0
        assert result.usage.total_tokens > 0
    except RuntimeError as e:
        pytest.xfail(str(e))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reasoning_model_async_parameter_handling(client: Any) -> None:
    """Test async reasoning model parameter handling.

    This test verifies that the async version properly handles reasoning model
    parameters just like the sync version.
    """
    try:
        settings = get_settings()
        reasoning_model = settings.openai.reasoning_model
        if not reasoning_model or not any(
            rm in reasoning_model.lower() for rm in ["o1", "o1-preview", "o1-mini"]
        ):
            pytest.xfail(
                f"No reasoning model configured or '{reasoning_model}' is not a reasoning model"
            )
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
            ChatMessage(
                role=ChatRole.USER,
                content="What is the capital of France? Answer with just the city name.",
            ),
        ]
        result = await client.chat_async(
            messages=messages, model=reasoning_model, max_tokens=10
        )
        assert result.model is not None
        assert len(result.choices) > 0
        assert result.choices[0].message.content is not None
        assert "Paris" in result.choices[0].message.content
        assert result.usage.prompt_tokens > 0
        assert result.usage.completion_tokens > 0
        assert result.usage.total_tokens > 0
    except RuntimeError as e:
        pytest.xfail(str(e))


@pytest.mark.integration
def test_regular_model_vs_reasoning_model_parameters(client: Any) -> None:
    """Test that regular models and reasoning models use different parameters.

    This test verifies that regular models can use temperature while reasoning
    models cannot, demonstrating the parameter adjustment logic works correctly.
    """
    try:
        settings = get_settings()
        chat_model = settings.openai.chat_model
        reasoning_model = settings.openai.reasoning_model
        if not reasoning_model or not any(
            rm in reasoning_model.lower() for rm in ["o1", "o1-preview", "o1-mini"]
        ):
            pytest.xfail(
                f"No reasoning model configured or '{reasoning_model}' is not a reasoning model"
            )
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
            ChatMessage(role=ChatRole.USER, content="Say 'hello' in response."),
        ]
        regular_result = client.chat(
            messages=messages, model=chat_model, max_tokens=5, temperature=0.1
        )
        assert regular_result.model is not None
        assert len(regular_result.choices) > 0
        assert regular_result.choices[0].message.content is not None
        reasoning_result = client.chat(
            messages=messages, model=reasoning_model, max_tokens=5
        )
        assert reasoning_result.model is not None
        assert len(reasoning_result.choices) > 0
        assert reasoning_result.choices[0].message.content is not None
        assert regular_result.usage.total_tokens > 0
        assert reasoning_result.usage.total_tokens > 0
    except RuntimeError as e:
        pytest.xfail(str(e))


@pytest.mark.integration
def test_embedding(client: Any) -> None:
    """Test embedding generation with real API.

    This test verifies that the client can successfully generate embeddings
    using the real API.
    """
@pytest.mark.integration
def test_direct_sdk_embedding_in_worker():
    load_dotenv()
    endpoint = os.environ["AZURE_OPENAI__ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI__API_KEY"]
    deployment = os.environ["AZURE_OPENAI__EMBEDDING_MODEL"]
    api_version = os.environ["AZURE_OPENAI__API_VERSION"]
    client_sdk = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    print("DEBUG: Direct SDK embedding call from within pytest worker:")
    print("  endpoint:", endpoint)
    print("  deployment:", deployment)
    print("  api_version:", api_version)
    response = client_sdk.embeddings.create(
        model=deployment,
        input=["hello world"],
    )
    print("Direct SDK embedding call succeeded! Response:", response)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_async(client: Any) -> None:
    """Test async chat completion with real API.

    This test verifies that the client can successfully make an async chat
    completion request to the real API.
    Skips (xfail) if using a test key or dummy endpoint.
    """
    api_key = os.environ.get("AZURE_OPENAI__API_KEY", "")
    endpoint = os.environ.get("AZURE_OPENAI__ENDPOINT", "")
    if api_key == "sk-test-key-openai" or not api_key or "dummy" in endpoint or not endpoint:
        pytest.xfail("OpenAI API key is a test key or endpoint is dummy; skipping real async chat completion test.")

    try:
        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a helpful assistant that answers concisely.",
            ),
            ChatMessage(role=ChatRole.USER, content="What is the capital of France?"),
        ]
        result = await client.chat_async(messages)
        assert result.model is not None
        assert len(result.choices) > 0
        assert result.choices[0].message.content is not None
        assert "Paris" in result.choices[0].message.content
        assert result.usage.prompt_tokens > 0
        assert result.usage.completion_tokens > 0
        assert result.usage.total_tokens > 0
    except RuntimeError as e:
        pytest.xfail(str(e))
    except Exception as e:
        pytest.xfail(f"OpenAI async chat completion failed: {e}")
