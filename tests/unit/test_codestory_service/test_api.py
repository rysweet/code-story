"""Tests for the Code Story Service API endpoints.

This module contains tests for the API layer of the service.
"""

from unittest import mock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from codestory_service.api import ingest, graph, config, auth, health
from codestory_service.domain.auth import LoginRequest
from codestory_service.domain.graph import (
    CypherQuery, 
    QueryType, 
    VectorQuery,
    VisualizationType,
    VisualizationTheme,
    VisualizationRequest,
    NodeFilter
)
from codestory_service.domain.ingestion import (
    IngestionRequest,
    IngestionSourceType,
    JobStatus,
)


class TestIngestAPI:
    """Tests for ingestion API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock ingestion service."""
        service = mock.AsyncMock()
        service.start_ingestion.return_value = mock.MagicMock(
            job_id="job123",
            status=JobStatus.PENDING,
            message="Job submitted successfully",
            eta=1620000000,
        )
        service.get_job_status.return_value = mock.MagicMock(
            job_id="job123", status=JobStatus.RUNNING, progress=0.5
        )
        return service

    @pytest.mark.asyncio
    async def test_start_ingestion(self, mock_service):
        """Test starting an ingestion job."""
        # Create request and user
        request = IngestionRequest(
            source_type=IngestionSourceType.LOCAL_PATH, source="/path/to/repo"
        )
        user = {"name": "testuser"}

        # Call the endpoint
        result = await ingest.start_ingestion(request, mock_service, user)

        # Check that service was called with correct parameters
        mock_service.start_ingestion.assert_called_once()
        actual_request = mock_service.start_ingestion.call_args[0][0]
        assert actual_request.source_type == IngestionSourceType.LOCAL_PATH
        assert actual_request.source == "/path/to/repo"
        assert actual_request.created_by == "testuser"

        # Check the result
        assert result.job_id == "job123"
        assert result.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_job_status(self, mock_service):
        """Test getting job status."""
        # Call the endpoint
        result = await ingest.get_job_status("job123", mock_service, {})

        # Check that service was called correctly
        mock_service.get_job_status.assert_called_once_with("job123")

        # Check the result
        assert result.job_id == "job123"
        assert result.status == JobStatus.RUNNING
        assert result.progress == 0.5

    @pytest.mark.asyncio
    async def test_cancel_job(self, mock_service):
        """Test cancelling a job."""
        # Setup mock service
        mock_service.cancel_job.return_value = mock.MagicMock(
            job_id="job123", status=JobStatus.CANCELLING
        )

        # Call the endpoint
        result = await ingest.cancel_job("job123", mock_service, {})

        # Check that service was called correctly
        mock_service.cancel_job.assert_called_once_with("job123")

        # Check the result
        assert result.job_id == "job123"
        assert result.status == JobStatus.CANCELLING


class TestGraphAPI:
    """Tests for graph API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock graph service."""
        service = mock.AsyncMock()
        service.execute_cypher_query.return_value = mock.MagicMock(
            columns=["name", "value"], rows=[["test", 123]], row_count=1
        )
        service.execute_vector_search.return_value = mock.MagicMock(
            results=[mock.MagicMock(id="node1", score=0.9)], total_count=1
        )
        return service

    @pytest.mark.asyncio
    async def test_execute_cypher_query(self, mock_service):
        """Test executing a Cypher query."""
        # Create query and user
        query = CypherQuery(
            query="MATCH (n) RETURN n.name, n.value",
            parameters={},
            query_type=QueryType.READ,
        )
        user = {"roles": ["user"]}

        # Call the endpoint
        result = await graph.execute_cypher_query(query, mock_service, user)

        # Check that service was called correctly
        mock_service.execute_cypher_query.assert_called_once_with(query)

        # Check the result
        assert result.columns == ["name", "value"]
        assert result.row_count == 1

    @pytest.mark.asyncio
    async def test_execute_cypher_query_write_permission(self, mock_service):
        """Test that only admins can execute write queries."""
        # Create query and user without admin role
        query = CypherQuery(
            query="CREATE (n:Test) RETURN n", parameters={}, query_type=QueryType.WRITE
        )
        user = {"roles": ["user"]}

        # Call the endpoint with non-admin user
        with pytest.raises(HTTPException) as exc_info:
            await graph.execute_cypher_query(query, mock_service, user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin permissions" in exc_info.value.detail

        # Call with admin user should work
        admin_user = {"roles": ["admin"]}
        await graph.execute_cypher_query(query, mock_service, admin_user)
        mock_service.execute_cypher_query.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_execute_vector_search(self, mock_service):
        """Test executing a vector search."""
        # Create query and user
        query = VectorQuery(query="Find authentication functions", limit=10)
        user = {"roles": ["user"]}

        # Call the endpoint
        result = await graph.execute_vector_search(query, mock_service, user)

        # Check that service was called correctly
        mock_service.execute_vector_search.assert_called_once_with(query)

        # Check the result
        assert result.total_count == 1


class TestConfigAPI:
    """Tests for configuration API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock config service."""
        from codestory_service.domain.config import (
            ConfigDump,
            ConfigGroup,
            ConfigItem,
            ConfigMetadata,
            ConfigSection,
            ConfigValueType,
            ConfigPermission,
            ConfigSource,
        )

        service = mock.MagicMock()

        # Create a sample config dump
        groups = {
            ConfigSection.GENERAL: ConfigGroup(
                section=ConfigSection.GENERAL,
                items={
                    "debug": ConfigItem(
                        value=True,
                        metadata=ConfigMetadata(
                            section=ConfigSection.GENERAL,
                            key="debug",
                            type=ConfigValueType.BOOLEAN,
                            description="Debug mode",
                            source=ConfigSource.CONFIG_FILE,
                            permission=ConfigPermission.READ_WRITE,
                        ),
                    )
                },
            )
        }

        config_dump = ConfigDump(
            groups=groups, version="1.0.0", last_updated="2025-05-09T10:00:00Z"
        )

        service.get_config_dump.return_value = config_dump
        service.update_config = mock.AsyncMock(return_value=config_dump)

        return service

    def test_get_config(self, mock_service):
        """Test getting configuration."""
        from codestory_service.domain.config import ConfigSection

        # Call the endpoint
        result = config.get_config(
            include_sensitive=False,
            config_service=mock_service,
            user={"roles": ["user"]},
        )

        # Check that service was called correctly
        mock_service.get_config_dump.assert_called_once_with(include_sensitive=False)

        # Check the result
        assert result.version == "1.0.0"
        assert ConfigSection.GENERAL in result.groups

    def test_get_config_sensitive(self, mock_service):
        """Test that only admins can view sensitive values."""
        from codestory_service.domain.config import ConfigSection

        # Call the endpoint with non-admin user
        with pytest.raises(HTTPException) as exc_info:
            config.get_config(
                include_sensitive=True,
                config_service=mock_service,
                user={"name": "user", "roles": ["user"]},
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

        # Call with admin user should work
        admin_user = {"roles": ["admin"]}
        result = config.get_config(
            include_sensitive=True, config_service=mock_service, user=admin_user
        )

        mock_service.get_config_dump.assert_called_with(include_sensitive=True)

    @pytest.mark.asyncio
    async def test_update_config(self, mock_service):
        """Test updating configuration."""
        from codestory_service.domain.config import ConfigPatch, ConfigSection

        # Create patch and user
        patch = ConfigPatch(
            items=[{"key": "general.debug", "value": False}],
            comment="Disable debug mode",
        )
        user = {"roles": ["admin"]}

        # Call the endpoint
        result = await config.update_config(patch, mock_service, user)

        # Check that service was called correctly
        mock_service.update_config.assert_awaited_once_with(patch)

        # Check the result
        assert result.version == "1.0.0"
        assert ConfigSection.GENERAL in result.groups


class TestAuthAPI:
    """Tests for authentication API endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock auth service."""
        service = mock.AsyncMock()
        service.login.return_value = mock.MagicMock(
            access_token="test.jwt.token",
            token_type="Bearer",
            expires_in=3600,
            scope="api",
        )
        service.get_user_info.return_value = mock.MagicMock(
            id="user123", name="Test User", roles=["user"], is_authenticated=True
        )
        return service

    @pytest.mark.asyncio
    async def test_login(self, mock_service):
        """Test login endpoint."""
        # Create request
        request = LoginRequest(username="testuser", password="password")

        # Call the endpoint
        result = await auth.login(request, mock_service)

        # Check that service was called correctly
        mock_service.login.assert_called_once_with(request)

        # Check the result
        assert result.access_token == "test.jwt.token"
        assert result.token_type == "Bearer"
        assert result.expires_in == 3600

    @pytest.mark.asyncio
    async def test_get_user_info(self, mock_service):
        """Test getting user info."""
        from codestory_service.domain.auth import UserInfo

        # Create user
        user = {"sub": "user123", "name": "Test User", "roles": ["user"]}

        # Mock the service return value
        mock_service.get_user_info.return_value = UserInfo(
            id="user123", name="Test User", roles=["user"], is_authenticated=True
        )

        # Call the endpoint
        result = await auth.get_user_info(mock_service, user)

        # Check that service was called correctly
        mock_service.get_user_info.assert_called_once_with(user)

        # Check the result
        assert result.id == "user123"
        assert result.name == "Test User"
        assert result.is_authenticated is True


class TestVisualizationAPI:
    """Tests for visualization API."""

    @pytest.fixture
    def mock_graph_service(self):
        """Create a mock graph service for visualization tests."""
        service = mock.AsyncMock()
        service.generate_visualization.return_value = "<html>Test Visualization</html>"
        return service

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        return mock.MagicMock()

    @pytest.mark.asyncio
    async def test_generate_visualization(self, mock_request, mock_graph_service):
        """Test generate visualization endpoint."""
        # Call the endpoint
        result = await graph.generate_visualization(
            type=graph.VisualizationType.FORCE,
            theme=graph.VisualizationTheme.DARK,
            focus_node_id=None,
            depth=2,
            max_nodes=100,
            node_types=None,
            search_query=None,
            include_orphans=False,
            graph_service=mock_graph_service,
            user={"id": "test-user"},
        )

        # Check that the graph service was called with expected parameters
        mock_graph_service.generate_visualization.assert_called_once()
        request_arg = mock_graph_service.generate_visualization.call_args[0][0]
        assert request_arg.type == graph.VisualizationType.FORCE
        assert request_arg.theme == graph.VisualizationTheme.DARK
        assert request_arg.filter is None  # Default filter
        
        # Check the result
        assert result.status_code == 200
        assert result.media_type == "text/html"
        assert result.body == b"<html>Test Visualization</html>"

    @pytest.mark.asyncio
    async def test_generate_visualization_with_filters(self, mock_request, mock_graph_service):
        """Test generate visualization endpoint with filters."""
        # Call the endpoint with filters
        result = await graph.generate_visualization(
            type=graph.VisualizationType.HIERARCHY,
            theme=graph.VisualizationTheme.LIGHT,
            focus_node_id="node123",
            depth=3,
            max_nodes=50,
            node_types="File,Class,Function",
            search_query="test",
            include_orphans=True,
            graph_service=mock_graph_service,
            user={"id": "test-user"},
        )

        # Check that the graph service was called with expected parameters
        mock_graph_service.generate_visualization.assert_called_once()
        request_arg = mock_graph_service.generate_visualization.call_args[0][0]
        assert request_arg.type == graph.VisualizationType.HIERARCHY
        assert request_arg.theme == graph.VisualizationTheme.LIGHT
        assert request_arg.focus_node_id == "node123"
        assert request_arg.depth == 3
        assert request_arg.filter.max_nodes == 50
        assert request_arg.filter.node_types == ["File", "Class", "Function"]
        assert request_arg.filter.search_query == "test"
        assert request_arg.filter.include_orphans is True
        
        # Check the result
        assert result.status_code == 200
        assert result.media_type == "text/html"

    @pytest.mark.asyncio
    async def test_generate_visualization_error(self, mock_request, mock_graph_service):
        """Test generate visualization endpoint with error."""
        # Mock the graph service to raise an exception
        mock_graph_service.generate_visualization.side_effect = Exception("Test error")

        # Call the endpoint
        with pytest.raises(HTTPException) as excinfo:
            await graph.generate_visualization(
                type=graph.VisualizationType.FORCE,
                theme=graph.VisualizationTheme.DARK,
                focus_node_id=None,
                depth=2,
                max_nodes=100,
                node_types=None,
                search_query=None,
                include_orphans=False,
                graph_service=mock_graph_service,
                user={"id": "test-user"},
            )

        # Check the exception
        assert excinfo.value.status_code == 500
        assert "Error generating visualization" in str(excinfo.value.detail)


class TestHealthAPI:
    """Tests for health API endpoints."""

    @pytest.fixture
    def mock_adapters(self):
        """Create mock adapters for health check."""
        neo4j = mock.AsyncMock()
        neo4j.check_health.return_value = {
            "status": "healthy",
            "details": {"database": "neo4j"},
        }

        celery = mock.AsyncMock()
        celery.check_health.return_value = {
            "status": "healthy",
            "details": {"active_workers": 2},
        }

        openai = mock.AsyncMock()
        openai.check_health.return_value = {
            "status": "healthy",
            "details": {"models": "text-embedding-ada-002"},
        }

        return neo4j, celery, openai

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, mock_adapters, monkeypatch):
        """Test health check when all components are healthy."""
        neo4j, celery, openai = mock_adapters
        
        # Create a custom class to mock Redis more accurately
        class MockRedisClient:
            async def ping(self):
                return True
                
            async def info(self):
                return {"redis_version": "6.0.0", "used_memory_human": "1M"}
                
            async def close(self):
                pass
        
        # Replace the Redis class with our mock
        monkeypatch.setattr(health.redis, "Redis", lambda **kwargs: MockRedisClient())

        # Call the endpoint
        result = await health.health_check(neo4j, celery, openai)

        # Check that adapters were called
        neo4j.check_health.assert_called_once()
        celery.check_health.assert_called_once()
        openai.check_health.assert_called_once()

        # Check the result
        assert result.status == "healthy"
        assert "neo4j" in result.components
        assert "celery" in result.components
        assert "openai" in result.components
        assert "redis" in result.components
        assert result.components["redis"].status == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_one_unhealthy(self, mock_adapters, monkeypatch):
        """Test health check when one component is unhealthy."""
        neo4j, celery, openai = mock_adapters
        
        # Create a custom class to mock Redis more accurately
        class MockRedisClient:
            async def ping(self):
                return True
                
            async def info(self):
                return {"redis_version": "6.0.0", "used_memory_human": "1M"}
                
            async def close(self):
                pass
        
        # Replace the Redis class with our mock
        monkeypatch.setattr(health.redis, "Redis", lambda **kwargs: MockRedisClient())

        # Make one component unhealthy
        neo4j.check_health.return_value = {
            "status": "unhealthy",
            "details": {"error": "Database connection failed"},
        }

        # Call the endpoint
        result = await health.health_check(neo4j, celery, openai)

        # Check the result
        assert result.status == "unhealthy"
        assert result.components["neo4j"].status == "unhealthy"
        assert result.components["celery"].status == "healthy"
        assert result.components["openai"].status == "healthy"
        assert result.components["redis"].status == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_one_degraded(self, mock_adapters, monkeypatch):
        """Test health check when one component is degraded."""
        neo4j, celery, openai = mock_adapters
        
        # Create a custom class to mock Redis more accurately
        class MockRedisClient:
            async def ping(self):
                return True
                
            async def info(self):
                return {"redis_version": "6.0.0", "used_memory_human": "1M"}
                
            async def close(self):
                pass
        
        # Replace the Redis class with our mock
        monkeypatch.setattr(health.redis, "Redis", lambda **kwargs: MockRedisClient())

        # Make one component degraded
        celery.check_health.return_value = {
            "status": "degraded",
            "details": {"active_workers": 1, "expected_workers": 2},
        }

        # Call the endpoint
        result = await health.health_check(neo4j, celery, openai)

        # Check the result
        assert result.status == "degraded"
        assert result.components["neo4j"].status == "healthy"
        assert result.components["celery"].status == "degraded"
        assert result.components["openai"].status == "healthy"
        assert result.components["redis"].status == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_with_auto_fix(self, mock_adapters, monkeypatch):
        """Test health check with auto_fix parameter when there's an Azure auth issue."""
        neo4j, celery, openai = mock_adapters
        
        # Create a custom class to mock Redis more accurately
        class MockRedisClient:
            async def ping(self):
                return True
                
            async def info(self):
                return {"redis_version": "6.0.0", "used_memory_human": "1M"}
                
            async def close(self):
                pass
        
        # Replace the Redis class with our mock
        monkeypatch.setattr(health.redis, "Redis", lambda **kwargs: MockRedisClient())
        
        # Make OpenAI component have an auth issue
        openai.check_health.return_value = {
            "status": "unhealthy",
            "details": {
                "error": "DefaultAzureCredential failed to retrieve a token from the included credentials",
                "type": "AuthenticationError",
                "solution": "az login --tenant abcd1234 --scope https://cognitiveservices.azure.com/.default"
            },
        }
        
        # Mock subprocess.Popen to avoid actually running az login
        mock_popen = mock.Mock()
        monkeypatch.setattr(health.subprocess, "Popen", mock_popen)

        # Mock subprocess.run to avoid actually running the renewal script
        mock_run = mock.Mock()
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="Authentication renewal succeeded",
            stderr=""
        )
        monkeypatch.setattr(health.subprocess, "run", mock_run)

        # Call the endpoint with auto_fix=True
        result = await health.health_check(neo4j, celery, openai, auto_fix=True)

        # Check the result
        assert result.status == "unhealthy"
        assert result.components["openai"].status == "unhealthy"
        
        # Verify that renewal was attempted
        assert result.components["openai"].details.get("renewal_attempted") is True
        assert result.components["openai"].details.get("renewal_success") is True
        
        # Verify subprocess.run was called to run the renewal script
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        renewal_cmd = args[0]
        assert "azure_auth_renew.py" in str(renewal_cmd)
        
        # Verify subprocess.Popen was called to run the background container injection
        mock_popen.assert_called_once()
        args, _ = mock_popen.call_args
        background_cmd = args[0]
        assert "azure_auth_renew.py" in str(background_cmd)
        assert "--container" in str(background_cmd)
        assert "all" in str(background_cmd)
        
    @pytest.mark.asyncio
    async def test_health_check_with_auto_fix_failure(self, mock_adapters, monkeypatch):
        """Test health check when auto_fix attempt fails."""
        neo4j, celery, openai = mock_adapters
        
        # Create a custom class to mock Redis more accurately
        class MockRedisClient:
            async def ping(self):
                return True
                
            async def info(self):
                return {"redis_version": "6.0.0", "used_memory_human": "1M"}
                
            async def close(self):
                pass
        
        # Replace the Redis class with our mock
        monkeypatch.setattr(health.redis, "Redis", lambda **kwargs: MockRedisClient())
        
        # Make OpenAI component have an auth issue
        openai.check_health.return_value = {
            "status": "unhealthy",
            "details": {
                "error": "DefaultAzureCredential failed to retrieve a token from the included credentials",
                "type": "AuthenticationError",
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "solution": "az login --tenant 12345678-1234-1234-1234-123456789012 --scope https://cognitiveservices.azure.com/.default"
            },
        }
        
        # Mock subprocess.Popen to avoid actually running background tasks
        mock_popen = mock.Mock()
        monkeypatch.setattr(health.subprocess, "Popen", mock_popen)

        # Mock subprocess.run to simulate a failure in the renewal script
        mock_run = mock.Mock()
        mock_run.return_value = mock.Mock(
            returncode=1,
            stdout="",
            stderr="Error: Could not authenticate with Azure CLI"
        )
        monkeypatch.setattr(health.subprocess, "run", mock_run)

        # Call the endpoint with auto_fix=True
        result = await health.health_check(neo4j, celery, openai, auto_fix=True)

        # Check the result
        assert result.status == "unhealthy"
        assert result.components["openai"].status == "unhealthy"
        
        # Verify that renewal was attempted but failed
        assert result.components["openai"].details.get("renewal_attempted") is True
        assert result.components["openai"].details.get("renewal_success") is False
        
        # Verify subprocess.run was called with correct tenant ID
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        renewal_cmd = args[0]
        assert "azure_auth_renew.py" in str(renewal_cmd)
        assert "--tenant" in str(renewal_cmd)
        assert "12345678-1234-1234-1234-123456789012" in str(renewal_cmd)
        
        # Verify we have error information in the result
        assert "renewal_stderr" in result.components["openai"].details
        assert "Error: Could not authenticate with Azure CLI" in result.components["openai"].details["renewal_stderr"]
        
    @pytest.mark.asyncio
    async def test_health_check_with_auto_fix_timeout(self, mock_adapters, monkeypatch):
        """Test health check when auto_fix times out."""
        neo4j, celery, openai = mock_adapters
        
        # Create a custom class to mock Redis more accurately
        class MockRedisClient:
            async def ping(self):
                return True
                
            async def info(self):
                return {"redis_version": "6.0.0", "used_memory_human": "1M"}
                
            async def close(self):
                pass
        
        # Replace the Redis class with our mock
        monkeypatch.setattr(health.redis, "Redis", lambda **kwargs: MockRedisClient())
        
        # Make OpenAI component have an auth issue
        openai.check_health.return_value = {
            "status": "unhealthy",
            "details": {
                "error": "DefaultAzureCredential failed to retrieve a token from the included credentials",
                "type": "AuthenticationError",
                "solution": "az login --scope https://cognitiveservices.azure.com/.default"
            },
        }
        
        # Mock subprocess.Popen to avoid actually running background tasks
        mock_popen = mock.Mock()
        monkeypatch.setattr(health.subprocess, "Popen", mock_popen)

        # Mock subprocess.run to simulate a timeout
        def mock_run_timeout(*args, **kwargs):
            raise health.subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get('timeout', 120))
            
        monkeypatch.setattr(health.subprocess, "run", mock_run_timeout)

        # Call the endpoint with auto_fix=True
        result = await health.health_check(neo4j, celery, openai, auto_fix=True)

        # Check the result
        assert result.status == "unhealthy"
        assert result.components["openai"].status == "unhealthy"
        
        # Verify that renewal was attempted but timed out
        assert result.components["openai"].details.get("renewal_attempted") is True
        assert result.components["openai"].details.get("renewal_success") is False
        assert "renewal_error" in result.components["openai"].details
        assert "timed out" in result.components["openai"].details["renewal_error"]
