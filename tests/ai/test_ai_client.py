import pytest

from pydantic import ValidationError


def test_ai_client_requires_api_key(monkeypatch):
    # Ensure OPENAI_API_KEY is not set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from codestory.ai import AIClient

    with pytest.raises(ValidationError):
        AIClient()


@pytest.mark.skip(
    reason="AIClient interface contract: instantiation and methods not yet implemented"
)
def test_ai_client_instantiation_and_methods_contract():
    # Future contract (to be implemented in AIClient):
    # - AIClient(api_key=None) uses Settings if api_key not passed
    # - Methods: async chat(messages: list[dict]) -> str
    # - Methods: embed(text: str) -> list[float]
    # - Handles retry with exponential back-off (trait test later)
    pass
