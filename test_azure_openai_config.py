#!/usr/bin/env python3
"""
Integration test for Azure OpenAI configuration.
This script tests the Azure OpenAI setup without requiring Docker containers.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    print("❌ azure.identity not available")
    AZURE_IDENTITY_AVAILABLE = False
    sys.exit(1)

try:
    from openai import AzureOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    print("❌ openai library not available")
    OPENAI_AVAILABLE = False
    sys.exit(1)

from codestory.config.settings import AzureOpenAISettings


def validate_environment():
    """Validate all required environment variables are set."""
    print("🔍 Validating environment variables...")

    required_vars = [
        "AZURE_OPENAI__ENDPOINT",
        "AZURE_OPENAI__DEPLOYMENT_ID",
        "AZURE_OPENAI__API_VERSION",
        "AZURE_TENANT_ID",
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mask sensitive values for display
            if "KEY" in var or "SECRET" in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"  ✅ {var} = {display_value}")

    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False

    print("✅ All required environment variables are set")
    return True


def test_azure_authentication():
    """Test Azure authentication using DefaultAzureCredential."""
    print("\n� Testing Azure authentication...")

    try:
        credential = DefaultAzureCredential()

        # Try to get a token to verify authentication works
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )

        print("✅ Azure authentication successful")
        return True, token_provider

    except Exception as e:
        print(f"❌ Azure authentication failed: {e}")
        return False, None


def test_azure_openai_settings():
    """Test loading Azure OpenAI settings."""
    print("\n⚙️  Testing Azure OpenAI settings...")

    try:
        # Create settings directly from environment variables
        # since AzureOpenAISettings doesn't extend BaseSettings
        settings = AzureOpenAISettings(
            endpoint=os.getenv("AZURE_OPENAI__ENDPOINT"),
            deployment_id=os.getenv("AZURE_OPENAI__DEPLOYMENT_ID", "gpt-4o"),
            api_version=os.getenv("AZURE_OPENAI__API_VERSION", "2024-05-01"),
            api_key=os.getenv("AZURE_OPENAI__API_KEY"),
        )
        print(f"  ✅ Endpoint: {settings.endpoint}")
        print(f"  ✅ Deployment ID: {settings.deployment_id}")
        print(f"  ✅ API Version: {settings.api_version}")

        return True, settings

    except Exception as e:
        print(f"❌ Failed to load Azure OpenAI settings: {e}")
        return False, None


def test_direct_azure_openai():
    """Test direct Azure OpenAI connection using the working foo.py pattern."""
    print("\n🔗 Testing direct Azure OpenAI connection (foo.py pattern)...")

    try:
        # Get settings
        settings_ok, settings = test_azure_openai_settings()
        if not settings_ok:
            return False

        # Create client exactly like foo.py
        print("  📱 Creating AzureOpenAI client...")
        client = AzureOpenAI(
            azure_deployment=settings.deployment_id,  # "o1"
            azure_endpoint=str(settings.endpoint),
            api_version=settings.api_version,
            azure_ad_token_provider=get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            ),
        )

        print("  📤 Sending test request...")
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {
                    "role": "user",
                    "content": "Hello! Just testing the connection. Please respond briefly.",
                },
            ],
            max_completion_tokens=100,
            model=settings.deployment_id,  # "o1"
        )

        print("  ✅ Direct Azure OpenAI call successful!")
        print(f"  📝 Response: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ Direct Azure OpenAI call failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        if "404" in str(e):
            print("   💡 404 error suggests endpoint or deployment configuration issue")
        elif "401" in str(e) or "403" in str(e):
            print("   💡 Authentication error - check Azure credentials")
        return False


async def test_codestory_client():
    """Test CodeStory OpenAI client."""
    print("\n🏗️  Testing CodeStory OpenAI client...")

    try:
        from codestory.llm.client import OpenAIClient
        from codestory.llm.models import ChatMessage

        # Get settings
        settings_ok, settings = test_azure_openai_settings()
        if not settings_ok:
            return False

        # Create client
        print("  📱 Creating CodeStory OpenAI client...")
        client = OpenAIClient(
            endpoint=str(settings.endpoint),
            chat_model=settings.deployment_id,
            api_version=settings.api_version,
        )

        # Test with a simple message
        test_messages = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(
                role="user", content="Hello! Just testing the connection. Please respond briefly."
            ),
        ]

        print("  📤 Sending test request...")
        response = await client.chat_async(
            messages=test_messages, model=settings.deployment_id, max_tokens=100, temperature=0.1
        )

        print("  ✅ CodeStory OpenAI API call successful!")
        print(f"  📝 Response: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ CodeStory OpenAI client failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        if "404" in str(e):
            print("   💡 404 error suggests endpoint or deployment configuration issue")
        elif "401" in str(e) or "403" in str(e):
            print("   💡 Authentication error - check Azure credentials")
        return False


async def main():
    """Run all integration tests."""
    print("🚀 Starting Azure OpenAI Integration Test")
    print("=" * 50)

    # Step 1: Validate environment
    if not validate_environment():
        sys.exit(1)

    # Step 2: Test Azure authentication
    auth_ok, token_provider = test_azure_authentication()
    if not auth_ok:
        sys.exit(1)

    # Step 3: Test Azure OpenAI settings
    settings_ok, settings = test_azure_openai_settings()
    if not settings_ok:
        sys.exit(1)

    # Step 4: Test direct Azure OpenAI (foo.py pattern)
    direct_ok = test_direct_azure_openai()
    if not direct_ok:
        print("\n❌ Direct Azure OpenAI test failed - cannot proceed to CodeStory client test")
        sys.exit(1)

    # Step 5: Test CodeStory client
    codestory_ok = await test_codestory_client()
    if not codestory_ok:
        print("\n❌ CodeStory client test failed")
        sys.exit(1)

    print("\n🎉 All tests passed! Azure OpenAI integration is working correctly.")


if __name__ == "__main__":
    asyncio.run(main())
