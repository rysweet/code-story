"""Tests for the Code Story Service application services.

This module contains tests for the application services used in the service.
"""

from unittest import mock

import pytest
from fastapi import HTTPException, WebSocket

from codestory_service.domain.auth import LoginRequest, TokenResponse
from codestory_service.domain.config import ConfigPatch
from codestory_service.domain.graph import CypherQuery, QueryType, VectorQuery, AskRequest
from codestory_service.domain.ingestion import IngestionRequest, IngestionSourceType, JobStatus
from codestory_service.application.auth_service import AuthService
from codestory_service.application.config_service import ConfigService
from codestory_service.application.graph_service import GraphService
from codestory_service.application.ingestion_service import IngestionService


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
        mock_validator.create_dev_token.assert_called_once_with(
            "admin",
            roles=["admin", "user"]
        )
    
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
            "roles": ["admin", "user"]
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
        # Mock export_settings function
        with mock.patch("codestory_service.application.config_service.export_settings") as mock_export:
            mock_export.return_value = {
                "general.debug": True,
                "service.title": "Test API",
                "openai.api_key": "sk_test_123456"
            }
            
            # Get config dump
            config = service.get_config_dump(include_sensitive=False)
            
            # Verify that sensitive values are redacted
            openai_group = config.groups.get("OPENAI")
            assert openai_group is not None
            api_key_item = openai_group.items.get("api_key")
            assert api_key_item is not None
            assert api_key_item.value == "***REDACTED***"
    
    def test_get_config_schema(self, service):
        """Test getting configuration schema."""
        # Mock get_config_dump method
        with mock.patch.object(service, "get_config_dump") as mock_get_dump:
            from codestory_service.domain.config import (
                ConfigDump, ConfigGroup, ConfigItem, ConfigMetadata,
                ConfigSection, ConfigValueType, ConfigPermission, ConfigSource
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
                                permission=ConfigPermission.READ_WRITE
                            )
                        )
                    }
                )
            }
            
            config_dump = ConfigDump(
                groups=groups,
                version="1.0.0",
                last_updated="2025-05-09T10:00:00Z"
            )
            
            mock_get_dump.return_value = config_dump
            
            # Get config schema
            schema = service.get_config_schema()
            
            # Verify that schema contains expected sections and properties
            assert "schema" in schema.model_dump()
            assert schema.schema["properties"]["general"]["properties"]["debug"]["type"] == "boolean"
    
    @pytest.mark.asyncio
    async def test_update_config(self, service):
        """Test updating configuration."""
        # Mock _validate_config_patch method
        from codestory_service.domain.config import ConfigValidationResult
        with mock.patch.object(service, "_validate_config_patch") as mock_validate:
            mock_validate.return_value = ConfigValidationResult(valid=True, errors=[])
            
            # Mock get_config_dump method
            with mock.patch.object(service, "get_config_dump") as mock_get_dump:
                from codestory_service.domain.config import (
                    ConfigDump, ConfigGroup, ConfigItem, ConfigMetadata,
                    ConfigSection, ConfigValueType, ConfigPermission, ConfigSource
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
                                    permission=ConfigPermission.READ_WRITE
                                )
                            )
                        }
                    )
                }
                
                config_dump = ConfigDump(
                    groups=groups,
                    version="1.0.0",
                    last_updated="2025-05-09T10:00:00Z"
                )
                
                mock_get_dump.return_value = config_dump
                
                # Create patch
                patch = ConfigPatch(
                    items=[
                        {"key": "general.debug", "value": False}
                    ],
                    comment="Disable debug mode"
                )
                
                # Update config
                result = await service.update_config(patch)
                
                # Verify that config was updated
                service.writer.update_setting.assert_called_once_with(
                    "general", "debug", False, comment="Disable debug mode"
                )
                
                # Verify that notification was published
                await service.redis.publish.assert_called_once()
                
                # Verify that updated config was returned
                assert isinstance(result, ConfigDump)


class TestGraphService:
    """Tests for Graph service."""
    
    @pytest.fixture
    def mock_neo4j(self):
        """Create a mock Neo4j adapter."""
        adapter = mock.AsyncMock()
        adapter.execute_cypher_query.return_value = mock.MagicMock(
            columns=["name", "value"],
            rows=[["test", 123]],
            row_count=1
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
            query_type=QueryType.READ
        )
        
        result = await service.execute_cypher_query(query)
        
        mock_neo4j.execute_cypher_query.assert_called_once_with(query)
        assert result.row_count == 1
        assert result.columns == ["name", "value"]
    
    @pytest.mark.asyncio
    async def test_execute_vector_search(self, service, mock_neo4j, mock_openai):
        """Test executing a vector search."""
        query = VectorQuery(
            query="Find authentication functions",
            limit=10
        )
        
        await service.execute_vector_search(query)
        
        mock_openai.create_embeddings.assert_called_once_with(["Find authentication functions"])
        mock_neo4j.execute_vector_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_answer_question(self, service, mock_neo4j, mock_openai):
        """Test answering a natural language question."""
        request = AskRequest(
            question="How does authentication work?",
            context_size=3
        )
        
        # Setup vector search results
        mock_neo4j.execute_vector_search.return_value = mock.MagicMock(
            results=[
                mock.MagicMock(id="node1", score=0.9),
                mock.MagicMock(id="node2", score=0.8),
                mock.MagicMock(id="node3", score=0.7)
            ]
        )
        
        # Setup node fetch results
        mock_neo4j.execute_cypher_query.return_value = mock.MagicMock(
            rows=[
                [{"id": "node1", "name": "Auth Module", "content": "Authentication code"}]
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
            job_id="job123",
            status=JobStatus.PENDING,
            eta=1620000000
        )
        adapter.get_job_status.return_value = mock.MagicMock(
            job_id="job123",
            status=JobStatus.RUNNING,
            progress=0.5
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
        request = IngestionRequest(
            source_type=IngestionSourceType.LOCAL_PATH,
            source="/path/to/repo"
        )
        
        result = await service.start_ingestion(request)
        
        mock_celery.start_ingestion.assert_called_once_with(request)
        assert result.job_id == "job123"
        assert result.status == JobStatus.PENDING
        
        # Check that progress event was published
        await service.redis.publish.assert_called_once()
        await service.redis.set.assert_called_once()
    
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
        
        # Mock pubsub
        pubsub = mock.AsyncMock()
        pubsub.get_message.side_effect = [
            None,  # First call returns None (timeout)
            {"type": "message", "data": '{"progress": 0.5}'},  # Second call returns message
            Exception("Connection closed")  # Third call raises exception
        ]
        service.redis.pubsub.return_value = pubsub
        
        # Mock get latest event
        service.redis.get.return_value = '{"progress": 0.2}'
        
        # Call subscribe method
        await service.subscribe_to_progress(websocket, "job123")
        
        # Check that websocket received messages
        websocket.send_text.assert_called_with('{"progress": 0.5}')
        
        # Check that heartbeat was sent
        websocket.send_json.assert_called_with({"type": "heartbeat"})
        
        # Check that pubsub was closed
        await pubsub.unsubscribe.assert_called_once()
        await pubsub.close.assert_called_once()