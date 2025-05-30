from typing import Any
'Tests for the Code Story Service infrastructure adapters.\n\nThis module contains tests for the infrastructure adapters used in the service.\n'
from unittest import mock
import pytest
from fastapi import HTTPException
from codestory.graphdb.exceptions import ConnectionError, QueryError
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.llm.exceptions import AuthenticationError
from codestory_service.domain.graph import CypherQuery, QueryType
from codestory_service.domain.ingestion import IngestionRequest, IngestionSourceType
from codestory_service.infrastructure.celery_adapter import CeleryAdapter
from codestory_service.infrastructure.msal_validator import MSALValidator
from codestory_service.infrastructure.neo4j_adapter import Neo4jAdapter
from codestory_service.infrastructure.openai_adapter import OpenAIAdapter

class TestNeo4jAdapter:
    """Tests for Neo4j adapter."""

    @pytest.fixture
    def mock_connector(self):
        """Create a mock Neo4jConnector."""
        connector = mock.MagicMock(spec=Neo4jConnector)
        connector.execute_query.return_value = [{'name': 'test', 'value': 123}]
        connector.check_connection.return_value = {'connected': True, 'database': 'neo4j', 'components': []}
        return connector

    @pytest.fixture
    def adapter(self, mock_connector: Any):
        """Create a Neo4jAdapter with a mock connector."""
        return Neo4jAdapter(connector=mock_connector)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_connector) -> None:
        """Test health check returns healthy status when connection succeeds."""
        result = await adapter.check_health()
        assert result['status'] == 'healthy'
        mock_connector.check_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_connector) -> None:
        """Test health check returns unhealthy status when connection fails."""
        mock_connector.check_connection.side_effect = ConnectionError('Failed to connect')
        adapter = Neo4jAdapter(connector=mock_connector)
        result = await adapter.check_health()
        assert result['status'] == 'unhealthy'
        assert 'error' in result['details']

    @pytest.mark.asyncio
    async def test_execute_cypher_query_success(self, adapter, mock_connector) -> None:
        """Test executing a Cypher query successfully."""
        query = CypherQuery(query='MATCH (n) RETURN n LIMIT 10', parameters={'limit': 10}, query_type=QueryType.READ)
        result = await adapter.execute_cypher_query(query)
        mock_connector.execute_query.assert_called_once_with(query.query, params=query.parameters, write=False)
        assert result.row_count > 0

    @pytest.mark.asyncio
    async def test_execute_cypher_query_error(self, adapter, mock_connector) -> None:
        """Test error handling when executing a Cypher query fails."""
        mock_connector.execute_query.side_effect = QueryError('Invalid query')
        query = CypherQuery(query='INVALID QUERY', parameters={}, query_type=QueryType.READ)
        with pytest.raises(HTTPException) as exc_info:
            await adapter.execute_cypher_query(query)
        assert exc_info.value.status_code == 400
        assert 'Invalid query' in exc_info.value.detail

class TestOpenAIAdapter:
    """Tests for OpenAI adapter."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAIClient."""
        client = mock.MagicMock()
        client.embedding_model = 'text-embedding-ada-002'
        client.chat_model = 'gpt-4'
        client.reasoning_model = 'gpt-3.5-turbo'
        from codestory.llm.models import EmbeddingData, EmbeddingResponse
        embedding_data = [EmbeddingData(embedding=[0.1, 0.2, 0.3], index=0, object='embedding')]
        embedding_response = EmbeddingResponse(object='list', data=embedding_data, model='text-embedding-ada-002', usage={'prompt_tokens': 8, 'total_tokens': 8})
        models_response = mock.MagicMock()
        model_data = [mock.MagicMock(id='text-embedding-ada-002'), mock.MagicMock(id='gpt-4'), mock.MagicMock(id='gpt-3.5-turbo')]
        models_response.data = model_data

        async def mock_list():
            return models_response
        client.embed_async = mock.AsyncMock(return_value=embedding_response)
        mock_response = mock.MagicMock()
        mock_response.model_dump.return_value = embedding_response.model_dump()

        async def mock_create(**kwargs):
            return mock_response
        mock_embeddings = mock.MagicMock()
        mock_embeddings.create = mock_create
        mock_models = mock.MagicMock()
        mock_models.list = mock_list
        mock_completion_response = mock.MagicMock()
        mock_completion_response.choices = [mock.MagicMock()]
        mock_completion_response.choices[0].message = mock.MagicMock()
        mock_completion_response.choices[0].message.content = 'Hello'

        async def mock_chat_create(**kwargs):
            return mock_completion_response
        mock_chat = mock.MagicMock()
        mock_completions = mock.MagicMock()
        mock_completions.create = mock_chat_create
        mock_chat.completions = mock_completions
        mock_async_client = mock.MagicMock()
        mock_async_client.embeddings = mock_embeddings
        mock_async_client.models = mock_models
        mock_async_client.chat = mock_chat
        client._async_client = mock_async_client
        return client

    @pytest.fixture
    def adapter(self, mock_client: Any):
        """Create an OpenAIAdapter with a mock client."""
        return OpenAIAdapter(client=mock_client)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_client) -> None:
        """Test health check returns healthy status when API is responsive."""
        result = await adapter.check_health()
        assert result['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_client) -> None:
        """Test health check returns unhealthy status when API fails."""
        mock_client.embedding_model = None
        mock_client.chat_model = None
        mock_client.reasoning_model = None
        adapter = OpenAIAdapter(client=mock_client)
        result = await adapter.check_health()
        assert result['status'] == 'degraded'

    @pytest.mark.asyncio
    async def test_health_check_azure_auth_error(self, mock_client) -> None:
        """Test health check detects Azure authentication errors."""
        azure_error = Exception('DefaultAzureCredential failed to retrieve a token from the included credentials. DefaultAzureCredential failed to retrieve a token from the included credentials. AzureCliCredential authentication failed: Azure CLI not found on the system PATH.')

        async def mock_list_error() -> None:
            raise azure_error
        mock_client._async_client.models.list = mock_list_error
        with mock.patch('codestory_service.infrastructure.openai_adapter.get_azure_tenant_id_from_environment', return_value=None):
            with mock.patch('codestory_service.infrastructure.openai_adapter.extract_tenant_id_from_error', return_value=None):
                with mock.patch('asyncio.create_subprocess_exec'):
                    adapter = OpenAIAdapter(client=mock_client)
                    result = await adapter.check_health()
        assert result['status'] == 'unhealthy'
        assert 'error' in result['details']
        assert result['details']['error'] == 'Azure authentication credentials expired'
        assert result['details'].get('type') == 'AuthenticationError'
        assert 'solution' in result['details']
        assert 'az login' in result['details']['solution']
        assert 'hint' in result['details']
        assert 'codestory service auth-renew' in result['details']['hint']
        assert 'tenant_id' in result['details']
        assert result['details']['tenant_id'] is None

    @pytest.mark.asyncio
    async def test_health_check_azure_auth_error_with_tenant(self, mock_client) -> None:
        """Test health check extracts tenant ID from Azure authentication errors."""
        azure_error = Exception("DefaultAzureCredential failed to retrieve a token from the included credentials. DefaultAzureCredential authentication failed for tenant '12345678-1234-1234-1234-123456789012'. AzureCliCredential authentication failed: AADSTS700003.")

        async def mock_list_error() -> None:
            raise azure_error
        mock_client._async_client.models.list = mock_list_error
        with mock.patch('codestory_service.infrastructure.openai_adapter.get_azure_tenant_id_from_environment', return_value=None):
            with mock.patch('codestory_service.infrastructure.openai_adapter.extract_tenant_id_from_error', return_value='12345678-1234-1234-1234-123456789012'):
                with mock.patch('asyncio.create_subprocess_exec'):
                    adapter = OpenAIAdapter(client=mock_client)
                    result = await adapter.check_health()
        assert result['status'] == 'unhealthy'
        assert 'tenant_id' in result['details']
        assert result['details']['tenant_id'] == '12345678-1234-1234-1234-123456789012'
        assert 'solution' in result['details']
        assert '--tenant 12345678-1234-1234-1234-123456789012' in result['details']['solution']

    @pytest.mark.asyncio
    async def test_health_check_nginx_404_error(self, mock_client) -> None:
        """Test health check handles nginx 404 errors with proper error reporting."""
        nginx_error = Exception('<html>\n<head><title>404 Not Found</title></head>\n<body>\n<center><h1>404 Not Found</h1></center>\n<hr><center>nginx</center>\n</body>\n</html>')

        async def mock_list_error() -> None:
            raise nginx_error
        mock_client._async_client.models.list = mock_list_error
        adapter = OpenAIAdapter(client=mock_client)
        result = await adapter.check_health()
        assert result['status'] == 'unhealthy'
        assert 'details' in result
        assert 'message' in result['details']
        assert 'Azure OpenAI endpoint returned a 404 error' in result['details']['message']
        assert 'error' in result['details']
        assert 'Endpoint not found or unavailable' in result['details']['error']
        assert 'suggestion' in result['details']
        assert 'current_config' in result['details']
        assert 'deployment_id' in result['details']['current_config']
        assert 'required_config' in result['details']
        assert 'AZURE_OPENAI__DEPLOYMENT_ID' in result['details']['required_config']
        assert 'AZURE_OPENAI__ENDPOINT' in result['details']['required_config']
        assert result['details']['required_config']['AZURE_OPENAI__DEPLOYMENT_ID'] == '<your-deployment-id>'
        assert result['details']['required_config']['AZURE_OPENAI__ENDPOINT'] == '<your-endpoint>'

    @pytest.mark.asyncio
    async def test_create_embeddings_success(self, adapter, mock_client) -> None:
        """Test creating embeddings successfully."""
        embeddings = await adapter.create_embeddings(['Test text'])
        assert len(embeddings) == 1
        assert isinstance(embeddings[0], list)

    @pytest.mark.asyncio
    async def test_create_embeddings_error(self, adapter, mock_client) -> None:
        """Test error handling when creating embeddings fails."""
        mock_client.embed_async.side_effect = AuthenticationError('Invalid API key')
        with pytest.raises(HTTPException) as exc_info:
            await adapter.create_embeddings(['Test text'])
        assert exc_info.value.status_code == 502
        assert 'Invalid API key' in exc_info.value.detail

class TestCeleryAdapter:
    """Tests for Celery adapter."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock Celery app."""
        app = mock.MagicMock()
        inspector = mock.MagicMock()
        inspector.active.return_value = {'worker1': ['task1', 'task2']}
        inspector.registered.return_value = {'worker1': ['task1', 'task2', 'task3']}
        app.control.inspect.return_value = inspector
        async_result = mock.MagicMock()
        async_result.id = 'job123'
        async_result.state = 'PENDING'
        app.AsyncResult.return_value = async_result
        task = mock.MagicMock()
        task.id = 'job123'
        task.apply_async.return_value = task
        app.tasks = {'run_ingestion_pipeline': task}
        return app

    @pytest.fixture
    def adapter(self, mock_app: Any):
        """Create a CeleryAdapter with a mock app."""
        adapter = CeleryAdapter()
        adapter.app = mock_app
        adapter._run_ingestion_pipeline = mock_app.tasks['run_ingestion_pipeline']
        return adapter

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_app) -> None:
        """Test health check returns healthy status when workers are active."""
        result = await adapter.check_health()
        assert result['status'] == 'healthy'
        assert result['details']['active_workers'] > 0

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_app) -> None:
        """Test health check returns unhealthy status when no workers are active."""
        inspector = mock_app.control.inspect.return_value
        inspector.active.return_value = {}
        inspector.registered.return_value = {}
        adapter = CeleryAdapter()
        adapter.app = mock_app
        result = await adapter.check_health()
        assert result['status'] == 'unhealthy'

    @pytest.mark.asyncio
    async def test_get_job_status(self, adapter, mock_app) -> None:
        """Test getting job status."""
        job = await adapter.get_job_status('job123')
        mock_app.AsyncResult.assert_called_once_with('job123')
        assert job.job_id == 'job123'
        assert job.status == 'pending'

    @pytest.mark.asyncio
    async def test_start_ingestion(self, adapter, mock_app) -> None:
        """Test starting an ingestion job."""
        request = IngestionRequest(source_type=IngestionSourceType.LOCAL_PATH, source='/path/to/repo')
        response = await adapter.start_ingestion(request)
        assert response.job_id == 'job123'
        assert response.status == 'pending'

    @pytest.mark.asyncio
    async def test_parameter_filtering(self, adapter, mock_app) -> None:
        """Test that parameter filtering is applied correctly to different steps."""
        request = IngestionRequest(source_type=IngestionSourceType.LOCAL_PATH, source='/path/to/repo', steps=['filesystem', 'blarify', 'summarizer', 'docgrapher'], options={'concurrency': 5, 'timeout': 300, 'job_id': 'test-job', 'ignore_patterns': ['.git'], 'custom_option': 'value', 'incremental': True})
        mock_apply_async = mock.MagicMock()
        mock_apply_async.return_value = mock.MagicMock(id='job123')
        adapter._run_ingestion_pipeline.apply_async = mock_apply_async
        await adapter.start_ingestion(request)
        mock_apply_async.assert_called_once()
        args, kwargs = mock_apply_async.call_args
        step_configs = kwargs.get('args', [None, None, None])[1]
        assert len(step_configs) == 4, 'Should have 4 step configs'
        filesystem_config = next((cfg for cfg in step_configs if cfg['name'] == 'filesystem'))
        assert 'concurrency' in filesystem_config, 'Filesystem should keep concurrency parameter'
        assert 'custom_option' in filesystem_config, 'Filesystem should keep custom_option parameter'
        blarify_config = next((cfg for cfg in step_configs if cfg['name'] == 'blarify'))
        assert 'concurrency' not in blarify_config, 'Blarify should not have concurrency parameter'
        assert 'custom_option' in blarify_config, 'Blarify should keep custom_option parameter'
        summarizer_config = next((cfg for cfg in step_configs if cfg['name'] == 'summarizer'))
        assert 'job_id' in summarizer_config, 'Summarizer should keep job_id parameter'
        assert 'ignore_patterns' in summarizer_config, 'Summarizer should keep ignore_patterns parameter'
        assert 'timeout' in summarizer_config, 'Summarizer should keep timeout parameter'
        assert 'incremental' in summarizer_config, 'Summarizer should keep incremental parameter'
        assert 'custom_option' not in summarizer_config, 'Summarizer should not have custom_option parameter'
        docgrapher_config = next((cfg for cfg in step_configs if cfg['name'] == 'docgrapher'))
        assert 'job_id' in docgrapher_config, 'Docgrapher should keep job_id parameter'
        assert 'ignore_patterns' in docgrapher_config, 'Docgrapher should keep ignore_patterns parameter'
        assert 'timeout' in docgrapher_config, 'Docgrapher should keep timeout parameter'
        assert 'incremental' in docgrapher_config, 'Docgrapher should keep incremental parameter'
        assert 'custom_option' not in docgrapher_config, 'Docgrapher should not have custom_option parameter'

class TestMSALValidator:
    """Tests for MSAL validator."""

    @pytest.fixture
    def validator(self) -> None:
        """Create an MSALValidator."""
        with mock.patch('codestory_service.infrastructure.msal_validator.get_service_settings') as mock_settings:
            settings = mock.MagicMock()
            settings.jwt_expiration = 3600
            mock_settings.return_value = settings
            validator = MSALValidator()
            validator.auth_enabled = False
            validator.dev_mode = True
            validator.jwt_secret = 'test_secret'
            validator.jwt_algorithm = 'HS256'
            validator.settings = settings
            return validator

    @pytest.mark.asyncio
    async def test_validate_token_auth_disabled(self, validator) -> None:
        """Test token validation when auth is disabled."""
        claims = await validator.validate_token('invalid_token')
        assert 'sub' in claims
        assert claims['roles'] == ['user']

    @pytest.mark.asyncio
    async def test_create_dev_token(self, validator) -> None:
        """Test creating a development token."""
        token = await validator.create_dev_token('testuser', roles=['admin'])
        assert isinstance(token, str)
        assert len(token) > 0