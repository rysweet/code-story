"""Tests for the Code Story Service API endpoints.

This module contains tests for the API layer of the service.
"""

from unittest import mock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from codestory_service.api import ingest, graph, config, auth, health
from codestory_service.domain.auth import LoginRequest
from codestory_service.domain.graph import CypherQuery, QueryType, VectorQuery
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
    async def test_health_check_all_healthy(self, mock_adapters):
        """Test health check when all components are healthy."""
        neo4j, celery, openai = mock_adapters

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

    @pytest.mark.asyncio
    async def test_health_check_one_unhealthy(self, mock_adapters):
        """Test health check when one component is unhealthy."""
        neo4j, celery, openai = mock_adapters

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

    @pytest.mark.asyncio
    async def test_health_check_one_degraded(self, mock_adapters):
        """Test health check when one component is degraded."""
        neo4j, celery, openai = mock_adapters

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
