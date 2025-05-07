# 5.0 AI Client

**Previous:** [Graph Database Service](../04-graph-database/graph-database.md) | **Next:** [Ingestion Pipeline](../06-ingestion-pipeline/ingestion-pipeline.md)

**Dependencies:** 
- [Scaffolding](../02-scaffolding/scaffolding.md)
- [Configuration Module](../03-configuration/configuration.md)

**Used by:**
- [Summarizer Workflow Step](../09-summarizer-step/summarizer-step.md)
- [Documentation Grapher Step](../10-docgrapher-step/docgrapher-step.md)
- [Code Story Service](../11-code-story-service/code-story-service.md)

## 5.1 Purpose

Provide low‑level async/sync access to Azure OpenAI services using bearer-token authentication, with support for completions, embeddings, and chat capabilities. The client implements retry logic, throttling back-off, and metrics collection while allowing multiple models to be used for different tasks. This module handles the communication with Azure OpenAI but keeps domain-specific logic (like summarization) elsewhere. Support for o1/o3 reasoning models, gpt-4o chat models, and `text-embedding-3-small` embeddings is required.

## 5.2 Responsibilities

- **Authentication**: Bearer-token auth via `AZURE_OAI_KEY` and `AZURE_OAI_ENDPOINT`
- **Model Support**: Work with o1/o3 reasoning models, gpt-4o chat models, and `text-embedding-3-small` embeddings
- **Error Handling**: Implement retry logic with exponential back-off for rate limits (429 errors)
- **API Methods**: Provide unified `complete()`, `embed()`, and `chat()` methods
- **Observability**: Expose Prometheus metrics and OpenTelemetry traces
- **Model Flexibility**: Support both chat completion and reasoning models with appropriate parameters
- **Multi-model Usage**: Allow different models to be specified for different tasks
- **Async Support**: Implement both synchronous and asynchronous request patterns

## 5.3 Architecture and Code Structure

```text
src/codestory/llm/
├── __init__.py                  # Package exports for OpenAIClient
├── client.py                    # Main OpenAIClient implementation 
├── models.py                    # Pydantic models for requests/responses
├── backoff.py                   # Retry and throttling logic
├── exceptions.py                # Custom exception types
└── metrics.py                   # Prometheus metrics collection
```

### 5.3.1 OpenAIClient Interface

The `OpenAIClient` class provides a unified interface for interacting with Azure OpenAI:

```python
class OpenAIClient:
    def __init__(self, api_key=None, endpoint=None, **config_options):
        """Initialize client with Azure OpenAI credentials and options."""
        
    # Synchronous methods
    def complete(self, prompt, model=None, max_tokens=None, temperature=None, **kwargs):
        """Generate completions using specified model."""
        
    def chat(self, messages, model=None, max_tokens=None, temperature=None, **kwargs):
        """Generate chat completions from message list."""
        
    def embed(self, texts, model=None, **kwargs):
        """Generate embeddings for provided texts."""
        
    # Asynchronous methods
    async def complete_async(self, prompt, model=None, max_tokens=None, temperature=None, **kwargs):
        """Asynchronous version of complete() method."""
        
    async def chat_async(self, messages, model=None, max_tokens=None, temperature=None, **kwargs):
        """Asynchronous version of chat() method."""
        
    async def embed_async(self, texts, model=None, **kwargs):
        """Asynchronous version of embed() method."""
```

## 5.4 Implementation Details

### 5.4.1 Configuration Integration

The client integrates with the configuration module from section 3.0:

```python
from codestory.config.settings import get_settings

def create_client():
    settings = get_settings()
    
    client = OpenAIClient(
        api_key=settings.openai.api_key.get_secret_value(),
        endpoint=settings.openai.endpoint,
        embedding_model=settings.openai.embedding_model,
        chat_model=settings.openai.chat_model,
        reasoning_model=settings.openai.reasoning_model,
        max_retries=settings.openai.max_retries,
        retry_backoff_factor=settings.openai.retry_backoff_factor
    )
    
    return client
```

### 5.4.2 Error Handling Strategy

The client implements a comprehensive error handling strategy:

```python
# src/codestory/llm/exceptions.py
class OpenAIError(Exception):
    """Base exception for all OpenAI-related errors."""
    
class AuthenticationError(OpenAIError):
    """Error with API key or authentication."""
    
class RateLimitError(OpenAIError):
    """Rate limit or quota exceeded."""
    
class InvalidRequestError(OpenAIError):
    """Invalid request parameters."""
    
class ServiceUnavailableError(OpenAIError):
    """OpenAI service unavailable or internal server error."""
```

### 5.4.3 Retry Logic

Using tenacity for robust retry handling:

```python
# src/codestory/llm/backoff.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(max_retries),
    wait=wait_exponential(multiplier=retry_backoff_factor, min=1, max=60),
    retry=retry_if_exception_type(RateLimitError),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def retry_api_call(func, *args, **kwargs):
    """Wrapper for API calls with exponential backoff retry."""
    try:
        return func(*args, **kwargs)
    except openai.RateLimitError as e:
        raise RateLimitError(f"Rate limit exceeded: {str(e)}") from e
```

## 5.5 Example Usage

### 5.5.1 Text Completion

```python
from codestory.llm.client import OpenAIClient

client = OpenAIClient()
response = client.complete(
    prompt="What is the capital of France?",
    model="gpt-4o",
    max_tokens=50,
    temperature=0.7
)
print(response.choices[0].text)
```

### 5.5.2 Chat Completion

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum computing in simple terms."}
]

response = client.chat(
    messages=messages,
    model="gpt-4o",
    max_tokens=150
)
print(response.choices[0].message.content)
```

### 5.5.3 Embeddings

```python
texts = ["This is a sample text", "This is another sample"]
embeddings = client.embed(texts, model="text-embedding-3-small")
print(f"First embedding vector (truncated): {embeddings.data[0].embedding[:5]}...")
```

### 5.5.4 Async Usage

```python
async def get_embedding_async():
    client = OpenAIClient()
    result = await client.embed_async(["Asynchronous embedding example"])
    return result

# In an async context
embeddings = await get_embedding_async()
```

## 5.6 User Stories and Acceptance Criteria

| User Story | Acceptance Criteria |
|------------|---------------------|
| As a developer, I want to generate completions from OpenAI models so that I can create text for various purposes. | • The client provides a `complete()` method that handles different completion models.<br>• Parameters like temperature and max_tokens are properly passed to the API.<br>• Results are returned in a consistent format. |
| As a developer, I want to generate chat completions with message history so that I can implement conversational features. | • The client provides a `chat()` method that accepts message arrays.<br>• The method handles system, user, and assistant message roles.<br>• Chat history can be maintained across multiple calls. |
| As a developer, I want to generate embeddings for semantic search so that I can find related content in the graph database. | • The client provides an `embed()` method that returns vector embeddings.<br>• Multiple texts can be embedded in a single call for efficiency.<br>• Embeddings work with the Neo4j vector search capability. |
| As a developer, I want automatic retry on rate limiting so that my application remains resilient. | • The client automatically retries on 429 errors with exponential backoff.<br>• Maximum retry attempts and backoff parameters are configurable.<br>• Metrics are collected on retry attempts. |
| As a developer, I want to use different models for different purposes so that I can optimize for performance and cost. | • The client allows specifying different models for completions, chat, and embeddings.<br>• Default models can be configured globally.<br>• The client correctly handles different parameter requirements for each model. |
| As a developer, I want to make asynchronous API calls so that I can use the client in async web applications. | • The client provides async versions of all methods (`complete_async()`, `chat_async()`, `embed_async()`).<br>• Async methods have the same interface as their synchronous counterparts.<br>• Resource management works correctly in async contexts. |
| As an operator, I want to monitor API usage and performance so that I can troubleshoot issues and optimize costs. | • Prometheus metrics track API calls, latency, and errors.<br>• OpenTelemetry traces provide detailed request tracking.<br>• Error rates and types are tracked for monitoring. |
| As a developer, I want to handle different error types appropriately so that I can provide relevant feedback to users. | • Different error types (authentication, rate limiting, invalid requests) are properly categorized.<br>• Error messages provide actionable information.<br>• The client doesn't expose sensitive information in error messages. |

## 5.7 Testing Strategy

- **Unit Tests**
  - Test client methods with mocked API responses
  - Test retry logic with simulated rate limiting
  - Test error handling for various error conditions
  - Test parameter validation and formatting
  - Test integration with configuration system

- **Integration Tests**
  - Test with actual Azure OpenAI endpoints (in test environment)
  - Verify embedding dimensions and formats
  - Verify authentication and error handling with real API

## 5.8 Implementation Steps

1. **Set up project structure**
   - Create module directory structure as outlined in section 5.3
   - Set up package exports in `__init__.py`

2. **Install dependencies**
   ```bash
   poetry add openai azure-identity azure-core tenacity prometheus-client structlog opentelemetry-sdk
   poetry add --dev pytest pytest-asyncio pytest-mock pytest-cov
   ```

3. **Implement core client**
   - Create base client class with configuration integration
   - Implement synchronous methods for completions, chat, and embeddings
   - Add parameter validation and formatting
   - Create response parsing and error handling

4. **Add retry logic**
   - Implement exponential backoff using tenacity
   - Create custom exception types
   - Add logging for retry attempts
   - Configure retry parameters from settings

5. **Add async support**
   - Implement async versions of all client methods
   - Ensure proper resource management in async context
   - Test with async frameworks

6. **Add monitoring**
   - Implement Prometheus metrics collection
   - Add OpenTelemetry tracing
   - Create health check endpoint

7. **Create unit tests**
   - Write comprehensive unit tests with mocked API
   - Test error handling and retry logic
   - Test parameter validation and formatting

8. **Create integration tests**
   - Set up test environment with Azure OpenAI
   - Write tests for actual API calls
   - Test embedding dimensions and formats

9. **Document API and usage**
   - Add detailed docstrings to all public methods
   - Create usage examples
   - Document error handling strategies
   - Create visualization of database schema

10. **Verification and Review**
    - Run all unit and integration tests to ensure complete functionality
    - Verify test coverage meets targets for all methods
    - Test with actual Azure OpenAI endpoints in test environment
    - Run linting and type checking on all code
    - Perform thorough code review against requirements and user stories
    - Test error handling and retry mechanisms with simulated failures
    - Verify proper handling of rate limits and other API errors
    - Validate authentication and token handling
    - Check embedding dimensions and format consistency
    - Make necessary adjustments based on review findings
    - Re-run all tests after any changes
    - Document any discovered issues and their resolutions
    - Create detailed PR for final review

---

