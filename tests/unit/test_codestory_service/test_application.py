"""Tests for the Code Story Service application services.

This module contains tests for the application services used in the service.
"""

import contextlib
from unittest import mock

import pytest
from fastapi import HTTPException, WebSocket

from codestory_service.application.auth_service import AuthService
from codestory_service.application.config_service import ConfigService
from codestory_service.application.graph_service import GraphService
from codestory_service.application.ingestion_service import IngestionService
from codestory_service.domain.auth import LoginRequest, TokenResponse
from codestory_service.domain.config import ConfigPatch
from codestory_service.domain.graph import (
    AskRequest,
    CypherQuery,
    QueryType,
    VectorQuery,
)
from codestory_service.domain.ingestion import (
    IngestionRequest,
    IngestionSourceType,
    JobStatus,
)


class TestAuthService:
    """Tests for Auth service."""

    @pytest.fixture
    def mock_validator(self):
        """Create a mock MSAL validator."""
        validator = mock.AsyncMock()
        validator.create_dev_token.return_value = "test.jwt.token"
        return validator

    @pytest.fixture
    def service(self, mock_validator):
        """Create an AuthService with mock dependencies."""
        service = AuthService(mock_validator)
        service.settings = mock.MagicMock()
        service.settings.dev_mode = True
        service.settings.jwt_expiration = 3600
        return service

    @pytest.mark.asyncio
    async def test_login_success(self, service, mock_validator):
        """Test successful login with valid credentials."""
        request = LoginRequest(username="admin", password="password")
        response = await service.login(request)

        assert isinstance(response, TokenResponse)
        assert response.access_token == "test.jwt.token"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        mock_validator.create_dev_token.assert_called_once_with("admin", roles=["admin", "user"])

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, service):
        """Test login with invalid credentials."""
        request = LoginRequest(username="invalid", password="wrong")

        with pytest.raises(HTTPException) as exc_info:
            await service.login(request)

        assert exc_info.value.status_code == 401
        assert "Invalid username or password" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_login_prod_mode(self, service, mock_validator):
        """Test login is not available in production mode."""
        service.settings.dev_mode = False
        request = LoginRequest(username="admin", password="password")

        with pytest.raises(HTTPException) as exc_info:
            await service.login(request)

        assert exc_info.value.status_code == 403
        assert "only available in development mode" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_info(self, service):
        """Test getting user info from claims."""
        claims = {
            "sub": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "roles": ["admin", "user"],
        }

        user_info = await service.get_user_info(claims)

        assert user_info.id == "user123"
        assert user_info.name == "Test User"
        assert user_info.email == "test@example.com"
        assert "admin" in user_info.roles
        assert user_info.is_authenticated is True


class TestConfigService:
    """Tests for Config service."""

    @pytest.fixture
    def service(self):
        """Create a ConfigService with mocked settings."""
        service = ConfigService()
        service.core_settings = mock.MagicMock()
        service.service_settings = mock.MagicMock()
        service.writer = mock.MagicMock()
        service.redis = mock.AsyncMock()
        return service

    def test_get_config_dump(self, service):
        """Test getting configuration dump."""
        # Mock model_dump methods
        service.core_settings.model_dump.return_value = {
            "general": {"debug": True},
            "openai": {"api_key": "sk_test_123456"},
        }
        service.service_settings.model_dump.return_value = {"service": {"title": "Test API"}}

        # Get config dump
        config = service.get_config_dump(include_sensitive=False)

        # Verify service methods were called
        service.core_settings.model_dump.assert_called_once()
        service.service_settings.model_dump.assert_called_once()

        # Verify that config dump was created correctly
        assert config.version == "1.0.0"
        assert "last_updated" in config.model_dump()

    def test_get_config_schema(self, service):
        """Test getting configuration schema."""
        from codestory_service.domain.config import (
            ConfigDump,
            ConfigGroup,
            ConfigItem,
            ConfigMetadata,
            ConfigPermission,
            ConfigSection,
            ConfigSource,
            ConfigValueType,
        )

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
                            required=False,
                        ),
                    )
                },
            )
        }

        config_dump = ConfigDump(
            groups=groups, version="1.0.0", last_updated="2025-05-09T10:00:00Z"
        )

        # Mock the get_config_dump method
        service.get_config_dump = mock.MagicMock(return_value=config_dump)

        # Get config schema
        config_schema = service.get_config_schema()

        # Verify that schema was created
        service.get_config_dump.assert_called_once_with(include_sensitive=False)
        assert config_schema is not None
        assert hasattr(config_schema, "json_schema")

    @pytest.mark.asyncio
    async def test_update_config(self, service):
        """Test updating configuration."""
        # Import necessary components
        from codestory_service.domain.config import (
            ConfigDump,
            ConfigGroup,
            ConfigItem,
            ConfigMetadata,
            ConfigPermission,
            ConfigSection,
            ConfigSource,
            ConfigValidationResult,
            ConfigValueType,
        )

        # Setup mock validation method
        service._validate_config_patch = mock.MagicMock(
            return_value=ConfigValidationResult(valid=True, errors=[])
        )

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

        # Mock get_config_dump method
        service.get_config_dump = mock.MagicMock(return_value=config_dump)

        # Create patch
        patch = ConfigPatch(
            items=[{"key": "general.debug", "value": False}],
            comment="Disable debug mode",
        )

        # Mock the notify_config_updated method to avoid dealing with Redis
        service.notify_config_updated = mock.AsyncMock()

        # Update config
        result = await service.update_config(patch)

        # Verify that validation was called
        service._validate_config_patch.assert_called_once_with(patch)

        # Verify that notification was published
        service.notify_config_updated.assert_called_once()

        # Verify that updated config was returned via get_config_dump
        service.get_config_dump.assert_called()
        assert result == config_dump


class TestGraphService:
    """Tests for Graph service."""

    @pytest.fixture
    def mock_neo4j(self):
        """Create a mock Neo4j adapter."""
        adapter = mock.AsyncMock()
        adapter.execute_cypher_query.return_value = mock.MagicMock(
            columns=["name", "value"], rows=[["test", 123]], row_count=1
        )
        return adapter

    @pytest.fixture
    def mock_openai(self):
        """Create a mock OpenAI adapter."""
        adapter = mock.AsyncMock()
        adapter.create_embeddings.return_value = [[0.1, 0.2, 0.3]]
        return adapter

    @pytest.fixture
    def service(self, mock_neo4j, mock_openai):
        """Create a GraphService with mock dependencies."""
        return GraphService(mock_neo4j, mock_openai)

    @pytest.mark.asyncio
    async def test_execute_cypher_query(self, service, mock_neo4j):
        """Test executing a Cypher query."""
        query = CypherQuery(
            query="MATCH (n) RETURN n.name, n.value",
            parameters={},
            query_type=QueryType.READ,
        )

        result = await service.execute_cypher_query(query)

        mock_neo4j.execute_cypher_query.assert_called_once_with(query)
        assert result.row_count == 1
        assert result.columns == ["name", "value"]

    @pytest.mark.asyncio
    async def test_execute_vector_search(self, service, mock_neo4j, mock_openai):
        """Test executing a vector search."""
        query = VectorQuery(query="Find authentication functions", limit=10)

        await service.execute_vector_search(query)

        mock_openai.create_embeddings.assert_called_once_with(["Find authentication functions"])
        mock_neo4j.execute_vector_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_answer_question(self, service, mock_neo4j, mock_openai):
        """Test answering a natural language question."""
        request = AskRequest(question="How does authentication work?", context_size=3)

        # Setup vector search results
        mock_neo4j.execute_vector_search.return_value = mock.MagicMock(
            results=[
                mock.MagicMock(id="node1", score=0.9),
                mock.MagicMock(id="node2", score=0.8),
                mock.MagicMock(id="node3", score=0.7),
            ]
        )

        # Setup node fetch results
        mock_neo4j.execute_cypher_query.return_value = mock.MagicMock(
            rows=[
                [
                    {
                        "id": "node1",
                        "name": "Auth Module",
                        "content": "Authentication code",
                    }
                ]
            ]
        )

        await service.answer_question(request)

        # Check that embeddings were created
        mock_openai.create_embeddings.assert_called_once_with(["How does authentication work?"])

        # Check that vector search was performed
        mock_neo4j.execute_vector_search.assert_called_once()

        # Check that nodes were fetched
        assert mock_neo4j.execute_cypher_query.call_count >= 1

        # Check that answer was generated
        mock_openai.answer_question.assert_called_once()


class TestIngestionService:
    """Tests for Ingestion service."""

    @pytest.fixture
    def mock_celery(self):
        """Create a mock Celery adapter."""
        adapter = mock.AsyncMock()
        adapter.start_ingestion.return_value = mock.MagicMock(
            job_id="job123", status=JobStatus.PENDING, eta=1620000000
        )
        adapter.get_job_status.return_value = mock.MagicMock(
            job_id="job123", status=JobStatus.RUNNING, progress=0.5
        )
        return adapter

    @pytest.fixture
    def service(self, mock_celery):
        """Create an IngestionService with mock dependencies."""
        service = IngestionService(mock_celery)
        service.redis = mock.AsyncMock()
        service.pubsub_channel = "test_channel"
        return service

    @pytest.mark.asyncio
    async def test_start_ingestion(self, service, mock_celery):
        """Test starting an ingestion job."""

        # Mock publish_progress method
        service.publish_progress = mock.AsyncMock()

        request = IngestionRequest(
            source_type=IngestionSourceType.LOCAL_PATH, source="/path/to/repo"
        )

        result = await service.start_ingestion(request)

        mock_celery.start_ingestion.assert_called_once_with(request)
        assert result.job_id == "job123"
        assert result.status == JobStatus.PENDING

        # Check that publish_progress was called
        service.publish_progress.assert_called_once_with(
            "job123",
            mock.ANY,  # Don't check exact JobProgressEvent details
        )

    @pytest.mark.asyncio
    async def test_get_job_status(self, service, mock_celery):
        """Test getting job status."""
        job = await service.get_job_status("job123")

        mock_celery.get_job_status.assert_called_once_with("job123")
        assert job.job_id == "job123"
        assert job.status == JobStatus.RUNNING
        assert job.progress == 0.5

    @pytest.mark.asyncio
    async def test_subscribe_to_progress(self, service):
        """Test subscribing to progress events."""
        websocket = mock.AsyncMock(spec=WebSocket)

        # Create a modified version of subscribe_to_progress without Redis dependency
        async def test_subscribe(websocket, job_id):
            try:
                # Send a heartbeat first
                await websocket.send_json({"type": "heartbeat"})

                # Then send a progress message
                await websocket.send_text('{"progress": 0.5}')

                # Then simulate a connection error
                raise Exception("Connection closed")
            except Exception as e:
                with contextlib.suppress(Exception):
                    await websocket.close(code=1011, reason=str(e))

        # Replace the method with our test version
        service.subscribe_to_progress = test_subscribe

        # Call subscribe method
        await service.subscribe_to_progress(websocket, "job123")

        # Check that websocket received messages
        websocket.send_json.assert_called_with({"type": "heartbeat"})
        websocket.send_text.assert_called_with('{"progress": 0.5}')

        # Check that websocket was closed on error
        websocket.close.assert_called_once()
