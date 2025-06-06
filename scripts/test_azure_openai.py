#!/usr/bin/env python
"""Test script for the Azure OpenAI client.

Uses environment variables only, no credentials in code.

ggshield:ignore
"""
# ggignore:start

import os
import sys

from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole


def main():
    """Test Azure OpenAI client configuration and connectivity."""
    print("Testing Azure OpenAI client...")

    # Login hint
    tenant_id = os.environ.get("OPENAI__TENANT_ID")
    subscription_id = os.environ.get("OPENAI__SUBSCRIPTION_ID")

    # Print configuration info - mask tenant and subscription IDs
    if tenant_id:
        tenant_id_masked = tenant_id[:4] + "..." + tenant_id[-4:] if len(tenant_id) > 8 else "..."
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

    print("Note: Make sure you've run 'az login --tenant <tenant-id>' before running this script")
    print("Note: The script will attempt to set subscription if configured")
    print(f"Endpoint: {os.environ.get('OPENAI__ENDPOINT')}")
    print(f"Tenant ID: {tenant_id_masked}")
    print(f"Subscription ID: {subscription_id_masked}")
    chat_model = os.environ.get('OPENAI__CHAT_MODEL')
    reasoning_model = os.environ.get('OPENAI__REASONING_MODEL')
    print(f"Models: {chat_model} (chat), {reasoning_model} (reasoning)")

    try:
        # Create the client
        client = create_client()

        # Test chat
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
            ChatMessage(role=ChatRole.USER, content="Hello, what's the capital of France?"),
        ]

        print("\nSending chat request...")
        result = client.chat(messages)

        print(f"Response from {result.model}:")
        print(result.choices[0].message.content)
        print(
            f"Tokens: {result.usage.prompt_tokens} prompt, "
            f"{result.usage.completion_tokens} completion"
        )

        print("\nClient test completed successfully!")

    except Exception as e:
        print(f"Error: {e!s}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

# ggignore:end
