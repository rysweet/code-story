from typing import Any

"Tests for the Code Story Service domain models.\n\nThis module contains tests for the domain models used in the service.\n"
from datetime import datetime
from unittest import mock

import pytest
from pydantic import ValidationError

from codestory.ingestion_pipeline.step import StepStatus
from codestory_service.domain.auth import LoginRequest, TokenResponse, UserInfo
from codestory_service.domain.config import (
    ConfigItem,
    ConfigMetadata,
    ConfigPatch,
    ConfigPermission,
    ConfigSection,
    ConfigValueType,
)
from codestory_service.domain.graph import CypherQuery, PathRequest, VectorQuery
from codestory_service.domain.ingestion import (
    IngestionRequest,
    IngestionSourceType,
    IngestionStarted,
    JobStatus,
    StepProgress,
)


class TestAuthModels:
    """Tests for authentication domain models."""

    def test_login_request_validation(self: Any) -> None:
        """Test that LoginRequest validates inputs correctly."""
        valid_request = LoginRequest(username="testuser", password="password123")
        assert valid_request.username == "testuser"
        assert valid_request.password == "password123"
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="password123")
        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="")

    def test_token_response(self: Any) -> None:
        """Test TokenResponse model."""
        token = TokenResponse(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="Bearer",
            expires_in=3600,
            scope="api",
        )
        assert token.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.scope == "api"

    def test_user_info(self: Any) -> None:
        """Test UserInfo model."""
        user = UserInfo(
            id="user123",
            name="Test User",
            email="test@example.com",
            roles=["admin", "user"],
            is_authenticated=True,
        )
        assert user.id == "user123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert "admin" in user.roles
        assert user.is_authenticated is True


class TestConfigModels:
    """Tests for configuration domain models."""

    def test_config_item_is_sensitive(self: Any) -> None:
        """Test that ConfigItem correctly identifies sensitive items."""
        sensitive_meta = ConfigMetadata(section=ConfigSection.SECURITY, key="password", type=ConfigValueType.SECRET, description="API password", source="env", permission=ConfigPermission.SENSITIVE)  # type: ignore[arg-type]
        sensitive_item = ConfigItem(value="secret123", metadata=sensitive_meta)
        assert sensitive_item.is_sensitive is True
        non_sensitive_meta = ConfigMetadata(section=ConfigSection.GENERAL, key="debug", type=ConfigValueType.BOOLEAN, description="Debug mode", source="config_file", permission=ConfigPermission.READ_WRITE)  # type: ignore[arg-type]
        non_sensitive_item = ConfigItem(value=True, metadata=non_sensitive_meta)
        assert non_sensitive_item.is_sensitive is False

    def test_config_item_redact_if_sensitive(self: Any) -> None:
        """Test that ConfigItem redacts sensitive values."""
        sensitive_meta = ConfigMetadata(section=ConfigSection.SECURITY, key="password", type=ConfigValueType.SECRET, description="API password", source="env", permission=ConfigPermission.SENSITIVE)  # type: ignore[arg-type]
        sensitive_item = ConfigItem(value="secret123", metadata=sensitive_meta)
        redacted_item = sensitive_item.redact_if_sensitive()
        assert redacted_item.value == "***REDACTED***"
        assert redacted_item.metadata == sensitive_meta
        non_sensitive_meta = ConfigMetadata(section=ConfigSection.GENERAL, key="debug", type=ConfigValueType.BOOLEAN, description="Debug mode", source="config_file", permission=ConfigPermission.READ_WRITE)  # type: ignore[arg-type]
        non_sensitive_item = ConfigItem(value=True, metadata=non_sensitive_meta)
        non_redacted_item = non_sensitive_item.redact_if_sensitive()
        assert non_redacted_item.value is True

    def test_config_patch_validation(self: Any) -> None:
        """Test that ConfigPatch validates inputs correctly."""
        valid_patch = ConfigPatch(
            items=[
                {"key": "general.debug", "value": True},
                {"key": "service.title", "value": "New Title"},
            ],
            comment="Update settings",
        )
        assert len(valid_patch.items) == 2
        assert valid_patch.comment == "Update settings"
        with pytest.raises(ValidationError):
            ConfigPatch(items=[], comment="Empty patch")


class TestGraphModels:
    """Tests for graph domain models."""

    def test_cypher_query_validation(self: Any) -> None:
        """Test that CypherQuery validates inputs correctly."""
        valid_query = CypherQuery(
            query="MATCH (n) RETURN n LIMIT 10", parameters={"limit": 10}
        )
        assert valid_query.query == "MATCH (n) RETURN n LIMIT 10"
        assert valid_query.parameters == {"limit": 10}
        with pytest.raises(ValidationError):
            CypherQuery(query="", parameters={})

    def test_vector_query_validation(self: Any) -> None:
        """Test that VectorQuery validates inputs correctly."""
        valid_query = VectorQuery(
            query="Find functions related to authentication", limit=20, min_score=0.6
        )
        assert valid_query.query == "Find functions related to authentication"
        assert valid_query.limit == 20
        assert valid_query.min_score == 0.6
        with pytest.raises(ValidationError):
            VectorQuery(query="a", limit=10)
        with pytest.raises(ValidationError):
            VectorQuery(query="Valid query", min_score=1.5)

    def test_path_request_validation(self: Any) -> None:
        """Test that PathRequest validates inputs correctly."""
        valid_request = PathRequest(
            start_node_id="node1", end_node_id="node2", max_depth=5
        )
        assert valid_request.start_node_id == "node1"
        assert valid_request.end_node_id == "node2"
        assert valid_request.max_depth == 5
        with pytest.raises(ValidationError):
            PathRequest(start_node_id="node1", end_node_id="node2", max_depth=100)


class TestIngestionModels:
    """Tests for ingestion domain models."""

    def test_ingestion_request_validation(self: Any) -> None:
        """Test that IngestionRequest validates inputs correctly."""
        with mock.patch("os.path.exists", return_value=True):
            valid_request = IngestionRequest(source_type=IngestionSourceType.LOCAL_PATH, source="/path/to/repo", options={"ignore_patterns": ["node_modules", ".git"]}, steps=["filesystem", "summarizer"])  # type: ignore[call-arg]
            assert valid_request.source_type == IngestionSourceType.LOCAL_PATH
            assert valid_request.source == "/path/to/repo"
            assert "ignore_patterns" in valid_request.options
            assert "filesystem" in valid_request.steps
            with pytest.raises(ValidationError):
                IngestionRequest(source_type=IngestionSourceType.LOCAL_PATH, source="")  # type: ignore[call-arg]
            with pytest.raises(ValueError):
                IngestionRequest(source_type=IngestionSourceType.GITHUB_REPO, source="invalid-format")  # type: ignore[call-arg]

    def test_ingestion_started(self: Any) -> None:
        """Test IngestionStarted model."""
        started = IngestionStarted(
            job_id="job123",
            status=JobStatus.PENDING,
            source="/path/to/repo",
            steps=["filesystem", "summarizer", "docgrapher"],
            message="Job submitted successfully",
            eta=1620000000,
        )
        assert started.job_id == "job123"
        assert started.status == JobStatus.PENDING
        assert started.message == "Job submitted successfully"
        assert started.eta == 1620000000

    def test_step_progress(self: Any) -> None:
        """Test StepProgress model."""
        progress = StepProgress(name="filesystem", status=StepStatus.RUNNING, progress=75.0, message="Processing files", started_at=datetime.now())  # type: ignore[call-arg]
        assert progress.name == "filesystem"
        assert progress.status == StepStatus.RUNNING
        assert progress.progress == 75.0
        assert progress.message == "Processing files"
        assert progress.started_at is not None
