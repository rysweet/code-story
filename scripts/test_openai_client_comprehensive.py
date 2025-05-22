#!/usr/bin/env python
"""Comprehensive test script for the Azure OpenAI client.

This script tests all main functionality of the client including:
- Chat completions
- Text completions
- Embeddings
- Async variants
- Error handling

ggshield:ignore
"""
# ggignore:start

import asyncio
import os
import sys

from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from codestory.llm.client import OpenAIClient, create_client
from codestory.llm.exceptions import InvalidRequestError
from codestory.llm.models import ChatMessage, ChatRole


def test_chat_completion(client: OpenAIClient) -> None:
    """Test chat completion API.

    Args:
        client: OpenAI client instance
    """
    print("\n=== Testing Chat Completion ===")

    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(
            role=ChatRole.USER,
            content="What is the capital of France? Answer in one word.",
        ),
    ]

    print("Sending chat request...")
    result = client.chat(messages, temperature=0.0)

    print(f"Response from {result.model}:")
    print(result.choices[0].message.content)
    print(
        f"Tokens: {result.usage.prompt_tokens} prompt, {result.usage.completion_tokens} completion"
    )

    assert (
        result.choices[0].message.content.strip().lower() == "paris"
    ), "Expected Paris as the answer"

    print("✅ Chat completion test passed!")


def test_completion(client: OpenAIClient) -> None:
    """Test text completion API.

    Args:
        client: OpenAI client instance
    """
    print("\n=== Testing Text Completion ===")

    prompt = "The capital of France is"

    print("Sending completion request...")
    result = client.complete(prompt, temperature=0.0, max_tokens=5)

    print(f"Response from {result.model}:")
    print(result.choices[0].text)
    print(
        f"Tokens: {result.usage.prompt_tokens} prompt, {result.usage.completion_tokens} completion"
    )

    assert (
        "paris" in result.choices[0].text.strip().lower()
    ), "Expected Paris to be in the answer"

    print("✅ Text completion test passed!")


def test_embedding(client: OpenAIClient) -> None:
    """Test embedding API.

    Args:
        client: OpenAI client instance
    """
    print("\n=== Testing Embeddings ===")

    texts = ["This is a test sentence for embeddings."]

    print("Sending embedding request...")
    result = client.embed(texts)

    print(f"Response from {result.model}:")
    print(f"Embedding dimensions: {len(result.data[0].embedding)}")
    print(f"First 5 values: {result.data[0].embedding[:5]}")
    print(
        f"Tokens: {result.usage.prompt_tokens} prompt, {result.usage.total_tokens} total"
    )

    assert len(result.data) == 1, "Expected 1 embedding"
    assert len(result.data[0].embedding) > 0, "Expected non-empty embedding"

    print("✅ Embedding test passed!")


async def test_async_chat(client: OpenAIClient) -> None:
    """Test async chat completion API.

    Args:
        client: OpenAI client instance
    """
    print("\n=== Testing Async Chat Completion ===")

    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(
            role=ChatRole.USER,
            content="What is the capital of Germany? Answer in one word.",
        ),
    ]

    print("Sending async chat request...")
    result = await client.chat_async(messages, temperature=0.0)

    print(f"Response from {result.model}:")
    print(result.choices[0].message.content)
    print(
        f"Tokens: {result.usage.prompt_tokens} prompt, {result.usage.completion_tokens} completion"
    )

    assert (
        result.choices[0].message.content.strip().lower() == "berlin"
    ), "Expected Berlin as the answer"

    print("✅ Async chat completion test passed!")


async def test_async_embedding(client: OpenAIClient) -> None:
    """Test async embedding API.

    Args:
        client: OpenAI client instance
    """
    print("\n=== Testing Async Embeddings ===")

    texts = ["This is another test sentence for async embeddings."]

    print("Sending async embedding request...")
    result = await client.embed_async(texts)

    print(f"Response from {result.model}:")
    print(f"Embedding dimensions: {len(result.data[0].embedding)}")
    print(f"First 5 values: {result.data[0].embedding[:5]}")
    print(
        f"Tokens: {result.usage.prompt_tokens} prompt, {result.usage.total_tokens} total"
    )

    assert len(result.data) == 1, "Expected 1 embedding"
    assert len(result.data[0].embedding) > 0, "Expected non-empty embedding"

    print("✅ Async embedding test passed!")


def test_error_handling(client: OpenAIClient) -> None:
    """Test error handling.

    Args:
        client: OpenAI client instance
    """
    print("\n=== Testing Error Handling ===")

    # Test invalid model name
    print("Testing invalid model error...")
    try:
        client.chat(
            [ChatMessage(role=ChatRole.USER, content="Hello")],
            model="non-existent-model",
        )
        assert False, "Expected InvalidRequestError"
    except InvalidRequestError as e:
        print(f"Correctly caught InvalidRequestError: {e}")

    print("✅ Error handling test passed!")


async def run_async_tests(client: OpenAIClient) -> None:
    """Run all async tests.

    Args:
        client: OpenAI client instance
    """
    await test_async_chat(client)
    await test_async_embedding(client)


def main() -> None:
    """Run all tests."""
    print("Testing Azure OpenAI client...")

    # Login hint
    tenant_id = os.environ.get("OPENAI__TENANT_ID")
    subscription_id = os.environ.get("OPENAI__SUBSCRIPTION_ID")

    # Print configuration info - mask tenant and subscription IDs
    if tenant_id:
        tenant_id_masked = (
            tenant_id[:4] + "..." + tenant_id[-4:] if len(tenant_id) > 8 else "..."
        )
    else:
        tenant_id_masked = "[Not set]"

    if subscription_id:
        subscription_id_masked = (
            subscription_id[:4] + "..." + subscription_id[-4:]
            if len(subscription_id) > 8
            else "..."
        )
    else:
        subscription_id_masked = "[Not set]"

    print(
        "Note: Make sure you've run 'az login --tenant <tenant-id>' before running this script"
    )
    print(f"Endpoint: {os.environ.get('OPENAI__ENDPOINT')}")
    print(f"Tenant ID: {tenant_id_masked}")
    print(f"Subscription ID: {subscription_id_masked}")
    print(
        f"Models: {os.environ.get('OPENAI__CHAT_MODEL')} (chat), {os.environ.get('OPENAI__REASONING_MODEL')} (reasoning)"
    )

    try:
        # Create the client
        client = create_client()

        # Run synchronous tests
        test_chat_completion(client)
        test_completion(client)
        test_embedding(client)
        test_error_handling(client)

        # Run asynchronous tests
        asyncio.run(run_async_tests(client))

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e!s}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

# ggignore:end
