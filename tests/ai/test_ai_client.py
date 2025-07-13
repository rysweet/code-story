import pytest

def test_import_ai_client_raises_importerror():
    with pytest.raises(ImportError):
        from codestory.ai import AIClient  # noqa: F401

@pytest.mark.skip(reason="AIClient interface contract: instantiation and methods not yet implemented")
def test_ai_client_instantiation_and_methods_contract():
    # Future contract (to be implemented in AIClient):
    # - AIClient(api_key=None) uses Settings if api_key not passed
    # - Methods: async chat(messages: list[dict]) -> str
    # - Methods: embed(text: str) -> list[float]
    # - Handles retry with exponential back-off (trait test later)
    pass