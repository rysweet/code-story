from typing import Any
'Tests for OpenAI client implementation.'
import asyncio
from unittest.mock import MagicMock, patch
import openai
import pytest
from codestory.llm.client import OpenAIClient, create_client
from codestory.llm.exceptions import AuthenticationError, InvalidRequestError
from codestory.llm.models import ChatCompletionResponse, ChatMessage, ChatRole, CompletionResponse, EmbeddingResponse

@pytest.fixture(autouse=True)
def patch_prometheus_metrics() -> None:
    """Patch prometheus metrics to avoid registration conflicts during tests."""
    with patch('prometheus_client.Counter'), patch('prometheus_client.Gauge'), patch('prometheus_client.Histogram'):
        yield

@pytest.fixture
def mock_settings() -> None:
    """Create mock settings for testing."""
    with patch('codestory.llm.client.get_settings') as mock_get_settings:
        settings = MagicMock()
        settings.openai = MagicMock()
        settings.openai.endpoint = 'https://test-endpoint.openai.azure.com'
        settings.openai.embedding_model = 'text-embedding-3-small'
        settings.openai.chat_model = 'gpt-4o'
        settings.openai.reasoning_model = 'gpt-4o'
        settings.openai.api_version = '2025-03-01-preview'
        settings.openai.timeout = 30.0
        settings.openai.max_retries = 3
        settings.openai.retry_backoff_factor = 2.0
        mock_get_settings.return_value = settings
        yield mock_get_settings

@pytest.fixture
def client() -> None:
    """Create an OpenAI client for testing."""
    with patch('openai.AzureOpenAI'), patch('openai.AsyncAzureOpenAI'), patch('codestory.llm.client.DefaultAzureCredential'), patch('codestory.llm.client.get_bearer_token_provider'), patch('codestory.llm.client.instrument_request', lambda op: lambda f: f), patch('codestory.llm.client.instrument_async_request', lambda op: lambda f: f), patch('codestory.llm.client.retry_on_openai_errors', lambda **kw: lambda f: f), patch('codestory.llm.client.retry_on_openai_errors_async', lambda **kw: lambda f: f):
        client = OpenAIClient(endpoint='https://test-endpoint.openai.azure.com', embedding_model='text-embedding-3-small', chat_model='gpt-4o', reasoning_model='gpt-4o', api_version='2025-03-01-preview', timeout=30.0, max_retries=3, retry_backoff_factor=2.0)
        yield client

class TestReasoningModelSupport:
    """Tests for reasoning model parameter adjustment logic."""

    def test_is_reasoning_model(self: Any, client: Any) -> None:
        """Test reasoning model detection."""
        assert client._is_reasoning_model('o1')
        assert client._is_reasoning_model('o1-preview')
        assert client._is_reasoning_model('o1-mini')
        assert client._is_reasoning_model('O1')
        assert client._is_reasoning_model('gpt-o1-preview')
        assert client._is_reasoning_model('my-o1-deployment')
        assert not client._is_reasoning_model('gpt-4o')
        assert not client._is_reasoning_model('gpt-4')
        assert not client._is_reasoning_model('gpt-3.5-turbo')
        assert not client._is_reasoning_model('text-embedding-3-small')
        assert not client._is_reasoning_model('claude-3')

    def test_adjust_params_for_reasoning_model_o1(self: Any, client: Any) -> None:
        """Test parameter adjustment for o1 reasoning models."""
        original_params = {'max_tokens': 100, 'temperature': 0.7, 'top_p': 0.9, 'other_param': 'value'}
        adjusted_params = client._adjust_params_for_reasoning_model(original_params, 'o1')
        assert 'max_completion_tokens' in adjusted_params
        assert adjusted_params['max_completion_tokens'] == 100
        assert 'max_tokens' not in adjusted_params
        assert 'temperature' not in adjusted_params
        assert adjusted_params['top_p'] == 0.9
        assert adjusted_params['other_param'] == 'value'

    def test_adjust_params_for_reasoning_model_o1_preview(self: Any, client: Any) -> None:
        """Test parameter adjustment for o1-preview model."""
        original_params = {'max_tokens': 50, 'temperature': 1.0}
        adjusted_params = client._adjust_params_for_reasoning_model(original_params, 'o1-preview')
        assert 'max_completion_tokens' in adjusted_params
        assert adjusted_params['max_completion_tokens'] == 50
        assert 'max_tokens' not in adjusted_params
        assert 'temperature' not in adjusted_params

    def test_adjust_params_for_reasoning_model_regular_model(self: Any, client: Any) -> None:
        """Test parameter adjustment for regular (non-reasoning) models."""
        original_params = {'max_tokens': 100, 'temperature': 0.7, 'top_p': 0.9}
        adjusted_params = client._adjust_params_for_reasoning_model(original_params, 'gpt-4o')
        assert adjusted_params == original_params
        assert 'max_tokens' in adjusted_params
        assert adjusted_params['max_tokens'] == 100
        assert 'temperature' in adjusted_params
        assert adjusted_params['temperature'] == 0.7
        assert 'max_completion_tokens' not in adjusted_params

    def test_adjust_params_for_reasoning_model_no_max_tokens(self: Any, client: Any) -> None:
        """Test parameter adjustment when max_tokens is not present."""
        original_params = {'temperature': 0.5, 'top_p': 0.8}
        adjusted_params = client._adjust_params_for_reasoning_model(original_params, 'o1')
        assert 'temperature' not in adjusted_params
        assert 'top_p' in adjusted_params
        assert adjusted_params['top_p'] == 0.8
        assert 'max_completion_tokens' not in adjusted_params
        assert 'max_tokens' not in adjusted_params

    def test_adjust_params_for_reasoning_model_none_max_tokens(self: Any, client: Any) -> None:
        """Test parameter adjustment when max_tokens is None."""
        original_params = {'max_tokens': None, 'temperature': 0.3}
        adjusted_params = client._adjust_params_for_reasoning_model(original_params, 'o1-mini')
        assert 'max_tokens' not in adjusted_params
        assert 'max_completion_tokens' not in adjusted_params
        assert 'temperature' not in adjusted_params

    def test_chat_with_reasoning_model_parameter_adjustment(self: Any, client: Any) -> None:
        """Test that chat method properly adjusts parameters for reasoning models."""
        with patch.object(client._sync_client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {'id': 'chatcmpl-123', 'object': 'chat.completion', 'created': 1616782565, 'model': 'o1', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Hello, how can I help you?'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 15, 'completion_tokens': 12, 'total_tokens': 27}}
            mock_create.return_value = mock_response
            messages = [ChatMessage(role=ChatRole.USER, content='Hello')]
            result = client.chat(messages=messages, model='o1', max_tokens=10, temperature=0.7)
            assert isinstance(result, ChatCompletionResponse)
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert 'max_completion_tokens' in call_args
            assert call_args['max_completion_tokens'] == 10
            assert 'max_tokens' not in call_args
            assert 'temperature' not in call_args
            assert call_args['model'] == 'o1'
            assert len(call_args['messages']) == 1

    @pytest.mark.asyncio
    async def test_chat_async_with_reasoning_model_parameter_adjustment(self: Any, client: Any) -> None:
        """Test that chat_async method properly adjusts parameters for reasoning models."""
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {'id': 'chatcmpl-123', 'object': 'chat.completion', 'created': 1616782565, 'model': 'o1-preview', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Async response'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}
        future = asyncio.Future()
        future.set_result(mock_response)
        with patch.object(client._async_client.chat.completions, 'create', return_value=future) as mock_create:
            messages = [ChatMessage(role=ChatRole.USER, content='Hello async')]
            result = await client.chat_async(messages=messages, model='o1-preview', max_tokens=20, temperature=0.9)
            assert isinstance(result, ChatCompletionResponse)
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert 'max_completion_tokens' in call_args
            assert call_args['max_completion_tokens'] == 20
            assert 'max_tokens' not in call_args
            assert 'temperature' not in call_args
            assert call_args['model'] == 'o1-preview'
            assert len(call_args['messages']) == 1

class TestOpenAIClient:
    """Tests for the OpenAIClient class."""

    def test_init(self: Any) -> None:
        """Test client initialization."""
        with patch('openai.AzureOpenAI'), patch('openai.AsyncAzureOpenAI'), patch('codestory.llm.client.DefaultAzureCredential'), patch('codestory.llm.client.get_bearer_token_provider'):
            client = OpenAIClient(endpoint='https://test-endpoint.openai.azure.com')
            assert client.endpoint == 'https://test-endpoint.openai.azure.com'
            assert client.embedding_model == 'text-embedding-3-small'
            assert client.chat_model == 'gpt-4o'
            assert client.reasoning_model == 'gpt-4o'
            client = OpenAIClient(endpoint='https://test-endpoint.openai.azure.com', embedding_model='custom-embedding-model', chat_model='custom-chat-model', reasoning_model='custom-reasoning-model')
            assert client.embedding_model == 'custom-embedding-model'
            assert client.chat_model == 'custom-chat-model'
            assert client.reasoning_model == 'custom-reasoning-model'

    def test_init_missing_credentials(self: Any) -> None:
        """Test client initialization with missing credentials."""
        with patch('codestory.llm.client.get_settings', side_effect=Exception('No settings')), patch('codestory.llm.client.DefaultAzureCredential'), patch('codestory.llm.client.get_bearer_token_provider'), pytest.raises(AuthenticationError):
            OpenAIClient()

    def test_complete(self: Any, client: Any) -> None:
        """Test text completion."""
        with patch.object(client._sync_client.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {'id': 'cmpl-123', 'object': 'text_completion', 'created': 1616782565, 'model': 'gpt-4o', 'choices': [{'text': 'This is a test completion.', 'index': 0, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 5, 'completion_tokens': 7, 'total_tokens': 12}}
            mock_create.return_value = mock_response
            result = client.complete('Test prompt')
            assert isinstance(result, CompletionResponse)
            assert result.model == 'gpt-4o'
            assert len(result.choices) == 1
            assert result.choices[0].text == 'This is a test completion.'
            assert result.usage.prompt_tokens == 5
            assert result.usage.completion_tokens == 7
            assert result.usage.total_tokens == 12
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args['model'] == 'gpt-4o'
            assert call_args['prompt'] == 'Test prompt'

    def test_chat(self: Any, client: Any) -> None:
        """Test chat completion."""
        with patch.object(client._sync_client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {'id': 'chatcmpl-123', 'object': 'chat.completion', 'created': 1616782565, 'model': 'gpt-4o', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Hello, how can I help you?'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 15, 'completion_tokens': 12, 'total_tokens': 27}}
            mock_create.return_value = mock_response
            messages = [ChatMessage(role=ChatRole.SYSTEM, content='You are a helpful assistant.'), ChatMessage(role=ChatRole.USER, content='Hello, assistant!')]
            result = client.chat(messages)
            assert isinstance(result, ChatCompletionResponse)
            assert result.model == 'gpt-4o'
            assert len(result.choices) == 1
            assert result.choices[0].message.role == ChatRole.ASSISTANT
            assert result.choices[0].message.content == 'Hello, how can I help you?'
            assert result.usage.prompt_tokens == 15
            assert result.usage.completion_tokens == 12
            assert result.usage.total_tokens == 27
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args['model'] == 'gpt-4o'
            assert len(call_args['messages']) == 2

    def test_embed(self: Any, client: Any) -> None:
        """Test embedding generation."""
        with patch.object(client._sync_client.embeddings, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {'object': 'list', 'data': [{'object': 'embedding', 'embedding': [0.1, 0.2, 0.3], 'index': 0}], 'model': 'text-embedding-3-small', 'usage': {'prompt_tokens': 8, 'total_tokens': 8}}
            mock_create.return_value = mock_response
            result = client.embed('Test text')
            assert isinstance(result, EmbeddingResponse)
            assert result.model == 'text-embedding-3-small'
            assert len(result.data) == 1
            assert result.data[0].embedding == [0.1, 0.2, 0.3]
            assert result.usage.prompt_tokens == 8
            assert result.usage.total_tokens == 8
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args['model'] == 'text-embedding-3-small'
            assert call_args['input'] == ['Test text']

    def test_error_handling_complete(self: Any) -> None:
        """Test error handling in completion."""
        with patch('openai.AzureOpenAI') as mock_azure_openai, patch('openai.AsyncAzureOpenAI'), patch('codestory.llm.backoff.retry_on_openai_errors'), patch('codestory.llm.client.DefaultAzureCredential'), patch('codestory.llm.client.get_bearer_token_provider'), patch('codestory.llm.client.instrument_request', lambda op: lambda f: f):
            mock_completions = MagicMock()
            mock_azure_openai.return_value = MagicMock(completions=mock_completions)
            client = OpenAIClient(endpoint='https://test-endpoint.openai.azure.com')
            with patch.object(client, '_sync_client') as mock_sync_client:
                mock_completions_create = MagicMock()
                mock_completions_create.create.side_effect = openai.BadRequestError(message='Invalid request parameters', response=MagicMock(), body=None)
                mock_sync_client.completions = mock_completions_create
                with pytest.raises(InvalidRequestError):
                    client.complete('Test prompt')

    @pytest.mark.asyncio
    async def test_complete_async(self: Any, client: Any) -> None:
        """Test async text completion."""
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {'id': 'cmpl-123', 'object': 'text_completion', 'created': 1616782565, 'model': 'gpt-4o', 'choices': [{'text': 'This is a test completion.', 'index': 0, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 5, 'completion_tokens': 7, 'total_tokens': 12}}
        future = asyncio.Future()
        future.set_result(mock_response)
        with patch.object(client._async_client.completions, 'create', return_value=future):
            result = await client.complete_async('Test prompt')
            assert isinstance(result, CompletionResponse)
            assert result.model == 'gpt-4o'
            assert len(result.choices) == 1
            assert result.choices[0].text == 'This is a test completion.'
            assert result.usage.prompt_tokens == 5
            assert result.usage.completion_tokens == 7
            assert result.usage.total_tokens == 12

class TestCreateClient:
    """Tests for the create_client function."""

    def test_create_client(self: Any, mock_settings: Any) -> None:
        """Test client creation with default settings."""
        with patch('openai.AzureOpenAI'), patch('openai.AsyncAzureOpenAI'), patch('codestory.llm.client.DefaultAzureCredential'), patch('codestory.llm.client.get_bearer_token_provider'), patch('codestory.llm.client.instrument_request', lambda op: lambda f: f), patch('codestory.llm.client.instrument_async_request', lambda op: lambda f: f), patch('codestory.llm.client.retry_on_openai_errors', lambda **kw: lambda f: f), patch('codestory.llm.client.retry_on_openai_errors_async', lambda **kw: lambda f: f):
            client = create_client()
            assert client.endpoint == 'https://test-endpoint.openai.azure.com'
            assert client.embedding_model == 'text-embedding-3-small'
            assert client.chat_model == 'gpt-4o'
            assert client.reasoning_model == 'gpt-4o'

    def test_create_client_override(self: Any) -> None:
        """Test client creation with overridden settings."""
        with patch('codestory.llm.client.OpenAIClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            with patch('codestory.llm.client.get_settings') as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.openai = MagicMock()
                mock_settings.openai.endpoint = 'https://test-endpoint.openai.azure.com'
                mock_settings.openai.api_version = '2025-03-01-preview'
                mock_settings.openai.timeout = 30.0
                mock_settings.openai.max_retries = 3
                mock_settings.openai.retry_backoff_factor = 2.0
                mock_settings.openai.embedding_model = 'text-embedding-3-small'
                mock_settings.openai.chat_model = 'gpt-4o'
                mock_settings.openai.reasoning_model = 'gpt-4o'
                mock_get_settings.return_value = mock_settings
                create_client()
                mock_client_class.assert_called_once_with(endpoint='https://test-endpoint.openai.azure.com', embedding_model='text-embedding-3-small', chat_model='gpt-4o', reasoning_model='gpt-4o', api_version='2025-03-01-preview', timeout=30.0, max_retries=3, retry_backoff_factor=2.0)