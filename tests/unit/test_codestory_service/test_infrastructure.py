"""Tests for the Code Story Service infrastructure adapters.

This module contains tests for the infrastructure adapters used in the service.
"""

from unittest import mock

import pytest
from fastapi import HTTPException
from neo4j import GraphDatabase

from codestory.graphdb.exceptions import ConnectionError, QueryError
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.llm.client import OpenAIClient
from codestory.llm.exceptions import AuthenticationError
from codestory_service.domain.graph import CypherQuery, QueryType
from codestory_service.domain.ingestion import IngestionRequest, IngestionSourceType
from codestory_service.infrastructure.neo4j_adapter import Neo4jAdapter
from codestory_service.infrastructure.openai_adapter import OpenAIAdapter
from codestory_service.infrastructure.celery_adapter import CeleryAdapter
from codestory_service.infrastructure.msal_validator import MSALValidator


class TestNeo4jAdapter:
    """Tests for Neo4j adapter."""

    @pytest.fixture
    def mock_connector(self):
        """Create a mock Neo4jConnector."""
        connector = mock.MagicMock(spec=Neo4jConnector)
        connector.execute_query_async.return_value = [{"name": "test", "value": 123}]
        connector.check_connection_async.return_value = {
            "connected": True,
            "database": "neo4j",
            "components": [],
        }
        return connector

    @pytest.fixture
    def adapter(self, mock_connector):
        """Create a Neo4jAdapter with a mock connector."""
        return Neo4jAdapter(connector=mock_connector)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_connector):
        """Test health check returns healthy status when connection succeeds."""
        result = await adapter.check_health()
        assert result["status"] == "healthy"
        mock_connector.check_connection_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_connector):
        """Test health check returns unhealthy status when connection fails."""
        mock_connector.check_connection_async.side_effect = ConnectionError(
            "Failed to connect"
        )
        adapter = Neo4jAdapter(connector=mock_connector)

        result = await adapter.check_health()
        assert result["status"] == "unhealthy"
        assert "error" in result["details"]

    @pytest.mark.asyncio
    async def test_execute_cypher_query_success(self, adapter, mock_connector):
        """Test executing a Cypher query successfully."""
        query = CypherQuery(
            query="MATCH (n) RETURN n LIMIT 10",
            parameters={"limit": 10},
            query_type=QueryType.READ,
        )

        result = await adapter.execute_cypher_query(query)

        mock_connector.execute_query_async.assert_called_once_with(
            query.query, query.parameters, write=False
        )
        assert result.row_count > 0

    @pytest.mark.asyncio
    async def test_execute_cypher_query_error(self, adapter, mock_connector):
        """Test error handling when executing a Cypher query fails."""
        mock_connector.execute_query_async.side_effect = QueryError("Invalid query")

        query = CypherQuery(
            query="INVALID QUERY", parameters={}, query_type=QueryType.READ
        )

        with pytest.raises(HTTPException) as exc_info:
            await adapter.execute_cypher_query(query)

        assert exc_info.value.status_code == 400
        assert "Invalid query" in exc_info.value.detail


class TestOpenAIAdapter:
    """Tests for OpenAI adapter."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenAIClient."""
        client = mock.MagicMock()
        # Don't use spec=OpenAIClient here to allow mocking any method

        # Setup the response for create_embeddings_async
        mock_response = mock.MagicMock()
        mock_response.model_dump.return_value = {
            "object": "list",
            "data": [{"embedding": [0.1, 0.2, 0.3], "index": 0, "object": "embedding"}],
            "model": "text-embedding-ada-002",
            "usage": {"prompt_tokens": 8, "total_tokens": 8},
        }

        # Create an awaitable mock
        async def mock_create(**kwargs):
            return mock_response

        # Configure the mock's async client and embeddings
        mock_embeddings = mock.MagicMock()
        mock_embeddings.create = mock_create

        mock_async_client = mock.MagicMock()
        mock_async_client.embeddings = mock_embeddings

        client._async_client = mock_async_client
        return client

    @pytest.fixture
    def adapter(self, mock_client):
        """Create an OpenAIAdapter with a mock client."""
        return OpenAIAdapter(client=mock_client)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_client):
        """Test health check returns healthy status when API is responsive."""
        result = await adapter.check_health()
        assert result["status"] == "healthy"
        # We can't easily verify the call was made since we're using an async function directly

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_client):
        """Test health check returns unhealthy status when API fails."""

        # Replace the mock create function with one that raises an error
        async def mock_create_error(**kwargs):
            raise AuthenticationError("Invalid API key")

        mock_client._async_client.embeddings.create = mock_create_error
        adapter = OpenAIAdapter(client=mock_client)

        result = await adapter.check_health()
        assert result["status"] == "unhealthy"
        assert "error" in result["details"]

    @pytest.mark.asyncio
    async def test_create_embeddings_success(self, adapter, mock_client):
        """Test creating embeddings successfully."""
        embeddings = await adapter.create_embeddings(["Test text"])

        # We can't easily verify the call was made since we're using an async function directly
        assert len(embeddings) == 1
        assert isinstance(embeddings[0], list)

    @pytest.mark.asyncio
    async def test_create_embeddings_error(self, adapter, mock_client):
        """Test error handling when creating embeddings fails."""

        # Replace the mock create function with one that raises an error
        async def mock_create_error(**kwargs):
            # Match the exception import used in the adapter
            from codestory.llm.exceptions import AuthenticationError

            raise AuthenticationError("Invalid API key")

        mock_client._async_client.embeddings.create = mock_create_error

        with pytest.raises(HTTPException) as exc_info:
            await adapter.create_embeddings(["Test text"])

        # According to the adapter implementation, it maps AuthenticationError to 401
        assert exc_info.value.status_code == 502  # Maps to BAD_GATEWAY in our adapter
        assert "Invalid API key" in exc_info.value.detail


class TestCeleryAdapter:
    """Tests for Celery adapter."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock Celery app."""
        app = mock.MagicMock()
        inspector = mock.MagicMock()
        inspector.active.return_value = {"worker1": ["task1", "task2"]}
        inspector.registered.return_value = {"worker1": ["task1", "task2", "task3"]}
        app.control.inspect.return_value = inspector

        # Mock AsyncResult
        async_result = mock.MagicMock()
        async_result.id = "job123"
        async_result.state = "PENDING"
        app.AsyncResult.return_value = async_result

        # Mock apply_async
        task = mock.MagicMock()
        task.id = "job123"
        task.apply_async.return_value = task
        app.tasks = {"run_ingestion_pipeline": task}

        return app

    @pytest.fixture
    def adapter(self, mock_app):
        """Create a CeleryAdapter with a mock app."""
        adapter = CeleryAdapter()
        adapter.app = mock_app
        # Make the run_ingestion_pipeline task available
        from codestory_service.infrastructure.celery_adapter import (
            run_ingestion_pipeline,
        )

        # Replace the actual run_ingestion_pipeline with the mock task
        adapter._run_ingestion_pipeline = mock_app.tasks["run_ingestion_pipeline"]
        return adapter

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, adapter, mock_app):
        """Test health check returns healthy status when workers are active."""
        result = await adapter.check_health()
        assert result["status"] == "healthy"
        assert result["details"]["active_workers"] > 0

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_app):
        """Test health check returns unhealthy status when no workers are active."""
        inspector = mock_app.control.inspect.return_value
        inspector.active.return_value = {}
        inspector.registered.return_value = {}

        adapter = CeleryAdapter()
        adapter.app = mock_app

        result = await adapter.check_health()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_get_job_status(self, adapter, mock_app):
        """Test getting job status."""
        job = await adapter.get_job_status("job123")

        mock_app.AsyncResult.assert_called_once_with("job123")
        assert job.job_id == "job123"
        assert job.status == "pending"

    @pytest.mark.asyncio
    async def test_start_ingestion(self, adapter, mock_app):
        """Test starting an ingestion job."""
        request = IngestionRequest(
            source_type=IngestionSourceType.LOCAL_PATH, source="/path/to/repo"
        )

        response = await adapter.start_ingestion(request)

        assert response.job_id == "job123"
        assert response.status == "pending"


class TestMSALValidator:
    """Tests for MSAL validator."""

    @pytest.fixture
    def validator(self):
        """Create an MSALValidator."""
        with mock.patch(
            "codestory_service.infrastructure.msal_validator.get_service_settings"
        ) as mock_settings:
            # Setup settings with concrete values
            settings = mock.MagicMock()
            settings.jwt_expiration = 3600  # Use a concrete value
            mock_settings.return_value = settings

            validator = MSALValidator()
            validator.auth_enabled = False
            validator.dev_mode = True
            validator.jwt_secret = "test_secret"
            validator.jwt_algorithm = "HS256"
            validator.settings = settings
            return validator

    @pytest.mark.asyncio
    async def test_validate_token_auth_disabled(self, validator):
        """Test token validation when auth is disabled."""
        claims = await validator.validate_token("invalid_token")

        assert "sub" in claims
        assert claims["roles"] == ["user"]
        # Note: is_authenticated is not present in the default claims

    @pytest.mark.asyncio
    async def test_create_dev_token(self, validator):
        """Test creating a development token."""
        token = await validator.create_dev_token("testuser", roles=["admin"])

        assert isinstance(token, str)
        assert len(token) > 0
