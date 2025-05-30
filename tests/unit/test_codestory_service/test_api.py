from typing import Any
'Tests for the Code Story Service API endpoints.\n\nThis module contains tests for the API layer of the service.\n'
import asyncio
from unittest import mock
import pytest
from fastapi import HTTPException, status
from codestory_service.api import auth, config, graph, health, ingest
from codestory_service.domain.auth import LoginRequest
from codestory_service.domain.graph import CypherQuery, QueryType, VectorQuery
from codestory_service.domain.ingestion import IngestionRequest, IngestionSourceType, JobStatus

class TestIngestAPI:
    """Tests for ingestion API endpoints."""

    @pytest.fixture
    def mock_service(self: Any) -> Any:
        """Create a mock ingestion service."""
        service = mock.AsyncMock()
        service.start_ingestion.return_value = mock.MagicMock(job_id='job123', status=JobStatus.PENDING, message='Job submitted successfully', eta=1620000000)
        service.get_job_status.return_value = mock.MagicMock(job_id='job123', status=JobStatus.RUNNING, progress=0.5)
        return service

    @pytest.mark.asyncio
    async def test_start_ingestion(self: Any, mock_service: Any) -> None:
        """Test starting an ingestion job."""
        request = IngestionRequest(source_type=IngestionSourceType.LOCAL_PATH, source='/path/to/repo')
        user = {'name': 'testuser'}
        result = await ingest.start_ingestion(request, mock_service, user)
        mock_service.start_ingestion.assert_called_once()
        actual_request = mock_service.start_ingestion.call_args[0][0]
        assert actual_request.source_type == IngestionSourceType.LOCAL_PATH
        assert actual_request.source == '/path/to/repo'
        assert actual_request.created_by == 'testuser'
        assert result.job_id == 'job123'
        assert result.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_job_status(self: Any, mock_service: Any) -> None:
        """Test getting job status."""
        result = await ingest.get_job_status('job123', mock_service, {})
        mock_service.get_job_status.assert_called_once_with('job123')
        assert result.job_id == 'job123'
        assert result.status == JobStatus.RUNNING
        assert result.progress == 0.5

    @pytest.mark.asyncio
    async def test_cancel_job(self: Any, mock_service: Any) -> None:
        """Test cancelling a job."""
        mock_service.cancel_job.return_value = mock.MagicMock(job_id='job123', status=JobStatus.CANCELLING)
        result = await ingest.cancel_job('job123', mock_service, {})
        mock_service.cancel_job.assert_called_once_with('job123')
        assert result.job_id == 'job123'
        assert result.status == JobStatus.CANCELLING

class TestGraphAPI:
    """Tests for graph API endpoints."""

    @pytest.fixture
    def mock_service(self: Any) -> Any:
        """Create a mock graph service."""
        service = mock.AsyncMock()
        service.execute_cypher_query.return_value = mock.MagicMock(columns=['name', 'value'], rows=[['test', 123]], row_count=1)
        service.execute_vector_search.return_value = mock.MagicMock(results=[mock.MagicMock(id='node1', score=0.9)], total_count=1)
        return service

    @pytest.mark.asyncio
    async def test_execute_cypher_query(self: Any, mock_service: Any) -> None:
        """Test executing a Cypher query."""
        query = CypherQuery(query='MATCH (n) RETURN n.name, n.value', parameters={}, query_type=QueryType.READ)
        user = {'roles': ['user']}
        result = await graph.execute_cypher_query(query, mock_service, user)
        mock_service.execute_cypher_query.assert_called_once_with(query)
        assert result.columns == ['name', 'value']
        assert result.row_count == 1

    @pytest.mark.asyncio
    async def test_execute_cypher_query_write_permission(self: Any, mock_service: Any) -> None:
        """Test that only admins can execute write queries."""
        query = CypherQuery(query='CREATE (n:Test) RETURN n', parameters={}, query_type=QueryType.WRITE)
        user = {'roles': ['user']}
        with pytest.raises(HTTPException) as exc_info:
            await graph.execute_cypher_query(query, mock_service, user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert 'admin permissions' in exc_info.value.detail
        admin_user = {'roles': ['admin']}
        await graph.execute_cypher_query(query, mock_service, admin_user)
        mock_service.execute_cypher_query.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_execute_vector_search(self: Any, mock_service: Any) -> None:
        """Test executing a vector search."""
        query = VectorQuery(query='Find authentication functions', limit=10)
        user = {'roles': ['user']}
        result = await graph.execute_vector_search(query, mock_service, user)
        mock_service.execute_vector_search.assert_called_once_with(query)
        assert result.total_count == 1

class TestConfigAPI:
    """Tests for configuration API endpoints."""

    @pytest.fixture
    def mock_service(self: Any) -> Any:
        """Create a mock config service."""
        from codestory_service.domain.config import ConfigDump, ConfigGroup, ConfigItem, ConfigMetadata, ConfigPermission, ConfigSection, ConfigSource, ConfigValueType
        service = mock.MagicMock()
        groups = {ConfigSection.GENERAL: ConfigGroup(section=ConfigSection.GENERAL, items={'debug': ConfigItem(value=True, metadata=ConfigMetadata(section=ConfigSection.GENERAL, key='debug', type=ConfigValueType.BOOLEAN, description='Debug mode', source=ConfigSource.CONFIG_FILE, permission=ConfigPermission.READ_WRITE))})}
        config_dump = ConfigDump(groups=groups, version='1.0.0', last_updated='2025-05-09T10:00:00Z')
        service.get_config_dump.return_value = config_dump
        service.update_config = mock.AsyncMock(return_value=config_dump)
        return service

    def test_get_config(self: Any, mock_service: Any) -> None:
        """Test getting configuration."""
        from codestory_service.domain.config import ConfigSection
        result = config.get_config(include_sensitive=False, config_service=mock_service, user={'roles': ['user']})
        mock_service.get_config_dump.assert_called_once_with(include_sensitive=False)
        assert result.version == '1.0.0'
        assert ConfigSection.GENERAL in result.groups

    def test_get_config_sensitive(self: Any, mock_service: Any) -> None:
        """Test that only admins can view sensitive values."""
        with pytest.raises(HTTPException) as exc_info:
            config.get_config(include_sensitive=True, config_service=mock_service, user={'name': 'user', 'roles': ['user']})
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        admin_user = {'roles': ['admin']}
        config.get_config(include_sensitive=True, config_service=mock_service, user=admin_user)
        mock_service.get_config_dump.assert_called_with(include_sensitive=True)

    @pytest.mark.asyncio
    async def test_update_config(self: Any, mock_service: Any) -> None:
        """Test updating configuration."""
        from codestory_service.domain.config import ConfigPatch, ConfigSection
        patch = ConfigPatch(items=[{'key': 'general.debug', 'value': False}], comment='Disable debug mode')
        user = {'roles': ['admin']}
        result = await config.update_config(patch, mock_service, user)
        mock_service.update_config.assert_awaited_once_with(patch)
        assert result.version == '1.0.0'
        assert ConfigSection.GENERAL in result.groups

class TestAuthAPI:
    """Tests for authentication API endpoints."""

    @pytest.fixture
    def mock_service(self: Any) -> Any:
        """Create a mock auth service."""
        service = mock.AsyncMock()
        service.login.return_value = mock.MagicMock(access_token='test.jwt.token', token_type='Bearer', expires_in=3600, scope='api')
        service.get_user_info.return_value = mock.MagicMock(id='user123', name='Test User', roles=['user'], is_authenticated=True)
        return service

    @pytest.mark.asyncio
    async def test_login(self: Any, mock_service: Any) -> None:
        """Test login endpoint."""
        request = LoginRequest(username='testuser', password='password')
        result = await auth.login(request, mock_service)
        mock_service.login.assert_called_once_with(request)
        assert result.access_token == 'test.jwt.token'
        assert result.token_type == 'Bearer'
        assert result.expires_in == 3600

    @pytest.mark.asyncio
    async def test_get_user_info(self: Any, mock_service: Any) -> None:
        """Test getting user info."""
        from codestory_service.domain.auth import UserInfo
        user = {'sub': 'user123', 'name': 'Test User', 'roles': ['user']}
        mock_service.get_user_info.return_value = UserInfo(id='user123', name='Test User', roles=['user'], is_authenticated=True)
        result = await auth.get_user_info(mock_service, user)
        mock_service.get_user_info.assert_called_once_with(user)
        assert result.id == 'user123'
        assert result.name == 'Test User'
        assert result.is_authenticated is True

class TestVisualizationAPI:
    """Tests for visualization API."""

    @pytest.fixture
    def mock_graph_service(self: Any) -> Any:
        """Create a mock graph service for visualization tests."""
        service = mock.AsyncMock()
        service.generate_visualization.return_value = '<html>Test Visualization</html>'
        return service

    @pytest.fixture
    def mock_request(self: Any) -> Any:
        """Create a mock request object."""
        return mock.MagicMock()

    @pytest.mark.asyncio
    async def test_generate_visualization(self: Any, mock_request: Any, mock_graph_service: Any) -> None:
        """Test generate visualization endpoint."""
        result = await graph.generate_visualization(type=graph.VisualizationType.FORCE, theme=graph.VisualizationTheme.DARK, focus_node_id=None, depth=2, max_nodes=100, node_types=None, search_query=None, include_orphans=False, graph_service=mock_graph_service, user={'id': 'test-user'})
        mock_graph_service.generate_visualization.assert_called_once()
        request_arg = mock_graph_service.generate_visualization.call_args[0][0]
        assert request_arg.type == graph.VisualizationType.FORCE
        assert request_arg.theme == graph.VisualizationTheme.DARK
        assert request_arg.filter is None
        assert result.status_code == 200
        assert result.media_type == 'text/html'
        assert result.body == b'<html>Test Visualization</html>'

    @pytest.mark.asyncio
    async def test_generate_visualization_with_filters(self: Any, mock_request: Any, mock_graph_service: Any) -> None:
        """Test generate visualization endpoint with filters."""
        result = await graph.generate_visualization(type=graph.VisualizationType.HIERARCHY, theme=graph.VisualizationTheme.LIGHT, focus_node_id='node123', depth=3, max_nodes=50, node_types='File,Class,Function', search_query='test', include_orphans=True, graph_service=mock_graph_service, user={'id': 'test-user'})
        mock_graph_service.generate_visualization.assert_called_once()
        request_arg = mock_graph_service.generate_visualization.call_args[0][0]
        assert request_arg.type == graph.VisualizationType.HIERARCHY
        assert request_arg.theme == graph.VisualizationTheme.LIGHT
        assert request_arg.focus_node_id == 'node123'
        assert request_arg.depth == 3
        assert request_arg.filter.max_nodes == 50
        assert request_arg.filter.node_types == ['File', 'Class', 'Function']
        assert request_arg.filter.search_query == 'test'
        assert request_arg.filter.include_orphans is True
        assert result.status_code == 200
        assert result.media_type == 'text/html'

    @pytest.mark.asyncio
    async def test_generate_visualization_error(self: Any, mock_request: Any, mock_graph_service: Any) -> None:
        """Test generate visualization endpoint with error."""
        mock_graph_service.generate_visualization.side_effect = Exception('Test error')
        with pytest.raises(HTTPException) as excinfo:
            await graph.generate_visualization(type=graph.VisualizationType.FORCE, theme=graph.VisualizationTheme.DARK, focus_node_id=None, depth=2, max_nodes=100, node_types=None, search_query=None, include_orphans=False, graph_service=mock_graph_service, user={'id': 'test-user'})
        assert excinfo.value.status_code == 500
        assert 'Error generating visualization' in str(excinfo.value.detail)

class TestHealthAPI:
    """Tests for health API endpoints."""

    @pytest.fixture
    def mock_adapters(self: Any) -> Any:
        """Create mock adapters for health check."""
        neo4j = mock.AsyncMock()
        neo4j.check_health.return_value = {'status': 'healthy', 'details': {'database': 'neo4j'}}
        celery = mock.AsyncMock()
        celery.check_health.return_value = {'status': 'healthy', 'details': {'active_workers': 2}}
        openai = mock.AsyncMock()
        openai.check_health.return_value = {'status': 'healthy', 'details': {'models': 'text-embedding-ada-002'}}
        return (neo4j, celery, openai)

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self: Any, mock_adapters: Any, monkeypatch: Any) -> None:
        """Test health check when all components are healthy."""
        neo4j, celery, openai = mock_adapters

        class MockRedisClient:

            async def ping(self):
                return True

            async def info(self, section=None):
                return {'redis_version': '6.0.0', 'used_memory_human': '1M'}

            async def close(self) -> None:
                pass
        monkeypatch.setattr(health.redis, 'Redis', lambda **kwargs: MockRedisClient())

        async def mock_wait_for(coro, timeout):
            return await coro
        monkeypatch.setattr(asyncio, 'wait_for', mock_wait_for)
        result = await health.health_check(neo4j, celery, openai)
        neo4j.check_health.assert_called_once()
        celery.check_health.assert_called_once()
        openai.check_health.assert_called_once()
        assert result.status == 'healthy'
        assert 'neo4j' in result.components
        assert 'celery' in result.components
        assert 'openai' in result.components
        assert 'redis' in result.components
        assert result.components['redis'].status == 'healthy'

    @pytest.mark.asyncio
    async def test_health_check_one_unhealthy(self: Any, mock_adapters: Any, monkeypatch: Any) -> None:
        """Test health check when one component is unhealthy."""
        neo4j, celery, openai = mock_adapters

        class MockRedisClient:

            async def ping(self):
                return True

            async def info(self, section=None):
                return {'redis_version': '6.0.0', 'used_memory_human': '1M'}

            async def close(self) -> None:
                pass
        monkeypatch.setattr(health.redis, 'Redis', lambda **kwargs: MockRedisClient())

        async def mock_wait_for(coro, timeout):
            return await coro
        monkeypatch.setattr(asyncio, 'wait_for', mock_wait_for)
        neo4j.check_health.return_value = {'status': 'unhealthy', 'details': {'error': 'Database connection failed'}}
        result = await health.health_check(neo4j, celery, openai)
        assert result.status == 'degraded'
        assert result.components['neo4j'].status == 'unhealthy'
        assert result.components['celery'].status == 'healthy'
        assert result.components['openai'].status == 'healthy'
        assert result.components['redis'].status == 'healthy'

    @pytest.mark.asyncio
    async def test_health_check_one_degraded(self: Any, mock_adapters: Any, monkeypatch: Any) -> None:
        """Test health check when one component is degraded."""
        neo4j, celery, openai = mock_adapters

        class MockRedisClient:

            async def ping(self):
                return True

            async def info(self, section=None):
                return {'redis_version': '6.0.0', 'used_memory_human': '1M'}

            async def close(self) -> None:
                pass
        monkeypatch.setattr(health.redis, 'Redis', lambda **kwargs: MockRedisClient())

        async def mock_wait_for(coro, timeout):
            return await coro
        monkeypatch.setattr(asyncio, 'wait_for', mock_wait_for)
        celery.check_health.return_value = {'status': 'degraded', 'details': {'active_workers': 1, 'expected_workers': 2}}
        result = await health.health_check(neo4j, celery, openai)
        assert result.status == 'degraded'
        assert result.components['neo4j'].status == 'healthy'
        assert result.components['celery'].status == 'degraded'
        assert result.components['openai'].status == 'healthy'
        assert result.components['redis'].status == 'healthy'

    @pytest.mark.asyncio
    async def test_health_check_with_auto_fix(self: Any, mock_adapters: Any, monkeypatch: Any) -> None:
        """Test health check with auto_fix parameter when there's an Azure auth issue."""
        neo4j, celery, openai = mock_adapters

        class MockRedisClient:

            async def ping(self):
                return True

            async def info(self, section=None):
                return {'redis_version': '6.0.0', 'used_memory_human': '1M'}

            async def close(self) -> None:
                pass
        monkeypatch.setattr(health.redis, 'Redis', lambda **kwargs: MockRedisClient())

        async def mock_wait_for(coro, timeout):
            return await coro
        monkeypatch.setattr(asyncio, 'wait_for', mock_wait_for)
        openai.check_health.side_effect = [{'status': 'unhealthy', 'details': {'error': 'DefaultAzureCredential failed to retrieve a token from the included credentials', 'type': 'AuthenticationError', 'solution': 'az login --tenant abcd1234 --scope https://cognitiveservices.azure.com/.default'}}, {'status': 'healthy', 'details': {'models': 'text-embedding-ada-002'}}]
        result = await health.health_check(neo4j, celery, openai, auto_fix=True)
        assert result.status == 'healthy'
        assert result.components['openai'].status == 'healthy'
        assert openai.check_health.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_with_auto_fix_failure(self: Any, mock_adapters: Any, monkeypatch: Any) -> None:
        """Test health check when auto_fix attempt fails."""
        neo4j, celery, openai = mock_adapters

        class MockRedisClient:

            async def ping(self):
                return True

            async def info(self, section=None):
                return {'redis_version': '6.0.0', 'used_memory_human': '1M'}

            async def close(self) -> None:
                pass
        monkeypatch.setattr(health.redis, 'Redis', lambda **kwargs: MockRedisClient())

        async def mock_wait_for(coro, timeout):
            return await coro
        monkeypatch.setattr(asyncio, 'wait_for', mock_wait_for)
        openai.check_health.side_effect = [{'status': 'unhealthy', 'details': {'error': 'DefaultAzureCredential failed to retrieve a token from the included credentials', 'type': 'AuthenticationError', 'tenant_id': '12345678-1234-1234-1234-123456789012'}}, Exception('Could not authenticate with Azure CLI')]
        result = await health.health_check(neo4j, celery, openai, auto_fix=True)
        assert result.status == 'degraded'
        assert result.components['openai'].status == 'unhealthy'
        assert openai.check_health.call_count == 2
        assert result.components['openai'].details is not None
        assert 'renewal_error' in result.components['openai'].details
        assert 'renewal_attempted' in result.components['openai'].details
        assert result.components['openai'].details['renewal_attempted'] is True

    @pytest.mark.asyncio
    async def test_health_check_with_auto_fix_timeout(self: Any, mock_adapters: Any, monkeypatch: Any) -> None:
        """Test health check when auto_fix times out."""
        neo4j, celery, openai = mock_adapters

        class MockRedisClient:

            async def ping(self):
                return True

            async def info(self, section=None):
                return {'redis_version': '6.0.0', 'used_memory_human': '1M'}

            async def close(self) -> None:
                pass
        monkeypatch.setattr(health.redis, 'Redis', lambda **kwargs: MockRedisClient())
        call_count = 0

        async def mock_wait_for_with_timeout(coro, timeout):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise TimeoutError('Operation timed out')
            return await coro
        monkeypatch.setattr(asyncio, 'wait_for', mock_wait_for_with_timeout)
        openai.check_health.return_value = {'status': 'unhealthy', 'details': {'error': 'DefaultAzureCredential failed to retrieve a token from the included credentials', 'type': 'AuthenticationError', 'solution': 'az login --scope https://cognitiveservices.azure.com/.default'}}
        result = await health.health_check(neo4j, celery, openai, auto_fix=True)
        assert result.status == 'unhealthy'
        assert result.components['openai'].status == 'unhealthy'
        assert result.components['openai'].details is not None
        assert 'error' in result.components['openai'].details
        assert 'timed out' in result.components['openai'].details['error'].lower()