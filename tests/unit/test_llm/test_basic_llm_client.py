from openai import AzureOpenAI
from tests.conftest import get_test_config

def test_basic_llm_client_chat():
    print("RUNNING test_basic_llm_client_chat")
    config = get_test_config()
    endpoint = config.get("AZURE_OPENAI_ENDPOINT")
    api_key = config.get("AZURE_OPENAI_KEY")
    api_version = config.get("AZURE_OPENAI_API_VERSION")
    deployment = config.get("AZURE_OPENAI_MODEL_CHAT")
    print(f"ENDPOINT: {endpoint}")
    print(f"DEPLOYMENT: {deployment}")
    print(f"API_VERSION: {api_version}")
    print(f"API_KEY: {api_key[:4]}...{api_key[-4:] if api_key else ''}")
    assert api_key, "AZURE_OPENAI_KEY must be set"
    assert endpoint, "AZURE_OPENAI_ENDPOINT must be set"
    assert deployment, "AZURE_OPENAI_MODEL_CHAT must be set"
    assert api_version, "AZURE_OPENAI_API_VERSION must be set"

    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {
                "role": "user",
                "content": "What is 2+2?",
            }
        ],
        max_tokens=10,
        model=deployment
    )

    print("RESPONSE:", response)
    assert hasattr(response, "choices")
    assert len(response.choices) > 0
    assert hasattr(response.choices[0], "message")
    assert "4" in response.choices[0].message.content