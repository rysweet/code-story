# Azure OpenAI Client

The Azure OpenAI client provides a unified interface for interacting with Azure OpenAI services, offering both synchronous and asynchronous APIs for completions, chat, and embeddings.

## Authentication

The client supports two authentication methods:

1. **Azure AD Authentication** (Recommended): Uses DefaultAzureCredential to authenticate with Azure, supporting managed identities, environment variables, and various credential sources.

2. **API Key Authentication** (Fallback): Uses API keys for authentication when Azure AD is not available.

## Key Features

- **Bearer Token Authentication**: Automatically uses Azure AD authentication with DefaultAzureCredential
- **Tenant and Subscription Handling**: Supports tenant_id and subscription_id parameters for Azure-specific scenarios
- **Retry Logic**: Implements exponential backoff for rate limiting and transient errors
- **Unified API**: Common interface for different types of completions and embeddings
- **Error Handling**: Comprehensive exception hierarchy for different error types
- **Metrics Collection**: Prometheus metrics for observability
- **Asynchronous API**: Full async support for all operations

## Basic Usage

```python
from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole

# Create a client with default settings from environment variables
client = create_client()

# Chat example
messages = [
    ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
    ChatMessage(role=ChatRole.USER, content="What is the capital of France?")
]

response = client.chat(messages)
print(response.choices[0].message.content)

# Embedding example
texts = ["This is a sample sentence to embed."]
embeddings = client.embed(texts)
print(f"Embedding dimensions: {len(embeddings.data[0].embedding)}")
```

## Async Example

```python
import asyncio
from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole

async def main():
    client = create_client()
    
    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(role=ChatRole.USER, content="What is the capital of France?")
    ]
    
    response = await client.chat_async(messages)
    print(response.choices[0].message.content)
    
    # Multiple concurrent requests
    texts = ["First text", "Second text", "Third text"]
    embedding_tasks = [client.embed_async([text]) for text in texts]
    results = await asyncio.gather(*embedding_tasks)
    
    for i, result in enumerate(results):
        print(f"Embedding {i} dimensions: {len(result.data[0].embedding)}")

asyncio.run(main())
```

## Configuration

The client uses settings from the configuration module, with the following precedence:
1. Explicitly provided parameters to the constructor or factory function
2. Environment variables (OPENAI__*)
3. Configuration settings from `.env` or `.codestory.toml`
4. Default values

### Environment Variables

Key environment variables:

- `OPENAI__ENDPOINT`: The Azure OpenAI endpoint URL (required)
- `OPENAI__API_KEY`: API key for direct authentication (optional when using Azure AD)
- `OPENAI__TENANT_ID`: Azure tenant ID for Azure AD authentication
- `OPENAI__SUBSCRIPTION_ID`: Azure subscription ID 
- `OPENAI__CHAT_MODEL`: Model name for chat completions (default: "gpt-4o")
- `OPENAI__REASONING_MODEL`: Model name for text completions (default: "gpt-4o")
- `OPENAI__EMBEDDING_MODEL`: Model name for embeddings (default: "text-embedding-3-small")
- `OPENAI__API_VERSION`: API version to use (default: "2025-03-01-preview")

## Error Handling

The client provides a detailed exception hierarchy:

- `OpenAIError`: Base exception for all errors
  - `AuthenticationError`: Authentication failed
  - `RateLimitError`: Rate limit exceeded
  - `InvalidRequestError`: Invalid request parameters
    - `ContextLengthError`: Input too large for model context
  - `ServiceUnavailableError`: API unavailable
  - `TimeoutError`: Request timed out

Example with error handling:

```python
from codestory.llm.client import create_client
from codestory.llm.exceptions import RateLimitError, AuthenticationError, OpenAIError

client = create_client()

try:
    response = client.chat([...])
    print(response.choices[0].message.content)
except RateLimitError as e:
    print(f"Rate limit exceeded, suggested retry after: {e.retry_after} seconds")
except AuthenticationError:
    print("Authentication failed. Check your credentials.")
except OpenAIError as e:
    print(f"OpenAI error: {e}")
```

## Testing

To test the OpenAI client:

1. Basic test: `python scripts/test_azure_openai.py`
2. Comprehensive test: `python scripts/test_openai_client_comprehensive.py`
3. Integration tests: `python -m pytest tests/integration/test_llm/ -v --run-openai`
4. Run all tests: `./scripts/run_openai_tests.sh` and select option 4

## Advanced Configuration

The client constructor accepts additional parameters for fine-tuning behavior:

```python
from codestory.llm.client import OpenAIClient

client = OpenAIClient(
    endpoint="https://your-resource.openai.azure.com",
    embedding_model="text-embedding-3-small",
    chat_model="gpt-4o",
    reasoning_model="gpt-4o",
    api_version="2025-03-01-preview",
    timeout=60.0,
    max_retries=5,
    retry_backoff_factor=2.0
)
```

## Client Methods

- **Chat**: `chat(messages, model=None, max_tokens=None, temperature=None, **kwargs)`
- **Completion**: `complete(prompt, model=None, max_tokens=None, temperature=None, **kwargs)`
- **Embedding**: `embed(texts, model=None, **kwargs)`
- **Async Chat**: `chat_async(messages, model=None, max_tokens=None, temperature=None, **kwargs)`
- **Async Completion**: `complete_async(prompt, model=None, max_tokens=None, temperature=None, **kwargs)`
- **Async Embedding**: `embed_async(texts, model=None, **kwargs)`