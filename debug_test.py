#!/usr/bin/env python3
"""Simple debug test to understand the ChatCompletionRequest issue."""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# These imports must come after sys.path modification
from codestory.llm.models import ChatCompletionRequest, ChatMessage, ChatRole  # noqa: E402

load_dotenv()

print("Testing ChatCompletionRequest creation...")

try:
    message = ChatMessage(role=ChatRole.USER, content="Hello test")
    print(f"✅ ChatMessage created: {message}")

    request = ChatCompletionRequest(model="o1", messages=[message], max_tokens=10, temperature=0.0)
    print(f"✅ ChatCompletionRequest created: {request}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
