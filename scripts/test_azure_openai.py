#!/usr/bin/env python
"""Test script for the Azure OpenAI client"""

import os
import sys
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from src.codestory.llm.client import create_client
from src.codestory.llm.models import ChatMessage, ChatRole

def main():
    print("Testing Azure OpenAI client...")
    
    # Login hint
    tenant_id = os.environ.get('OPENAI__TENANT_ID')
    subscription_id = os.environ.get('OPENAI__SUBSCRIPTION_ID')
    
    print(f"Note: Make sure you've run 'az login --tenant {tenant_id}' before running this script")
    print(f"Note: The script will attempt to set subscription to: {subscription_id}")
    print(f"Endpoint: {os.environ.get('OPENAI__ENDPOINT')}")
    print(f"Tenant ID: {tenant_id}")
    print(f"Subscription ID: {subscription_id}")
    print(f"Models: {os.environ.get('OPENAI__CHAT_MODEL')} (chat), {os.environ.get('OPENAI__REASONING_MODEL')} (reasoning)")
    
    try:
        # Create the client
        client = create_client()
        
        # Test chat
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
            ChatMessage(role=ChatRole.USER, content="Hello, what's the capital of France?")
        ]
        
        print("\nSending chat request...")
        result = client.chat(messages)
        
        print(f"Response from {result.model}:")
        print(result.choices[0].message.content)
        print(f"Tokens: {result.usage.prompt_tokens} prompt, {result.usage.completion_tokens} completion")
        
        print("\nClient test completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()