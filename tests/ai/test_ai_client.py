import pytest

from pydantic import ValidationError


def test_ai_client_requires_api_key(monkeypatch):
    # Ensure OPENAI_API_KEY is not set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from codestory.ai import AIClient

    with pytest.raises(ValidationError):
        AIClient()


import asyncio


def test_ai_client_instantiation_and_methods_contract(monkeypatch):
    from codestory.ai import AIClient

    # Provide dummy API key via env
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    client = AIClient()

    # Test async chat

    result = asyncio.run(client.chat("hello"))
    assert result == "Echo: hello"

    # Test async embed
    embed_result = asyncio.run(client.embed("foo"))
    assert embed_result == [0.0]
