"""Unit tests for CeleryAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import get_test_config

import pytest

from codestory_service.infrastructure.celery_adapter import CeleryAdapter


class TestCeleryAdapter:
    """Test cases for CeleryAdapter."""

    @pytest.fixture
    def mock_celery_app(self):
        """Create a mock Celery app."""
        app = MagicMock()
        app.conf.task_always_eager = False
        app.control.inspect.return_value = MagicMock()
        return app

    @pytest.fixture
    def celery_adapter(self, mock_celery_app):
        """Create a CeleryAdapter instance with mocked app."""
        with patch('codestory_service.infrastructure.celery_adapter.celery_app', mock_celery_app):
            return CeleryAdapter()

    @pytest.mark.asyncio
    async def test_check_health_with_eager_mode_enabled_via_config(self, celery_adapter):
        """Test that check_health returns healthy when task_always_eager is True."""
        # Set eager mode via app config
        celery_adapter._app.conf.task_always_eager = True
        
        # Mock the inspect method to ensure it's not called
        mock_inspect = MagicMock()
        celery_adapter._app.control.inspect = mock_inspect
        
        # Call check_health
        status, details = await celery_adapter.check_health()
        
        # Assert early return with healthy status
        assert status == "healthy"
        assert details["active_workers"] == 0
        assert details["registered_workers"] == 0
        assert details["registered_tasks"] == 0
        assert "message" in details
        # Assert that inspect was not called
        mock_inspect.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_with_eager_mode_enabled_via_env(self, celery_adapter):
        """Test that check_health returns healthy when CELERY_TASK_ALWAYS_EAGER env var is truthy."""
        # Ensure app config is False
        celery_adapter._app.conf.task_always_eager = False
        
        # Set environment variable
        config = get_test_config()
        config.set("CELERY_TASK_ALWAYS_EAGER", "1")
        # Mock the inspect method to ensure it's not called
        mock_inspect = MagicMock()
        celery_adapter._app.control.inspect = mock_inspect
        
        # Call check_health
        status, details = await celery_adapter.check_health()
        
        # Assert early return with healthy status
        assert status == "healthy"
        assert details["active_workers"] == 0
        assert details["registered_workers"] == 0
        assert details["registered_tasks"] == 0
        assert "message" in details
        # Assert that inspect was not called
        mock_inspect.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_with_eager_mode_env_true_string(self, celery_adapter):
        """Test that check_health returns healthy when CELERY_TASK_ALWAYS_EAGER is 'true'."""
        # Ensure app config is False
        celery_adapter._app.conf.task_always_eager = False
        
        # Set environment variable to 'true'
        config = get_test_config()
        config.set("CELERY_TASK_ALWAYS_EAGER", "true")
        # Mock the inspect method to ensure it's not called
        mock_inspect = MagicMock()
        celery_adapter._app.control.inspect = mock_inspect
        
        # Call check_health
        status, details = await celery_adapter.check_health()
        
        # Assert early return with healthy status
        assert status == "healthy"
        assert details["active_workers"] == 0
        assert details["registered_workers"] == 0
        assert details["registered_tasks"] == 0
        assert "message" in details
        # Assert that inspect was not called
        mock_inspect.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_without_eager_mode_calls_inspect(self, celery_adapter):
        """Test that check_health calls inspect when eager mode is disabled and returns all required keys with correct types."""
        # Ensure eager mode is disabled
        celery_adapter._app.conf.task_always_eager = False

        # Clear environment variable
        config = get_test_config()
        config.set("CELERY_TASK_ALWAYS_EAGER", "")
        # Mock successful inspect response
        mock_inspector = MagicMock()
        mock_inspector.active.return_value = {"worker1": []}
        mock_inspector.registered.return_value = {"worker1": ["task1"]}
        celery_adapter._app.control.inspect.return_value = mock_inspector

        # Call check_health
        status, details = await celery_adapter.check_health()

        # Assert inspect was called
        celery_adapter._app.control.inspect.assert_called_once()
        mock_inspector.active.assert_called_once()
        assert mock_inspector.registered.call_count == 2

        # Assert healthy response and all required keys/types
        assert status == "healthy"
        assert set(details.keys()) >= {"active_workers", "registered_workers", "registered_tasks", "message"}
        assert isinstance(details["active_workers"], int)
        assert isinstance(details["registered_workers"], int)
        assert isinstance(details["registered_tasks"], int)
        # Values should match the mock
        assert details["active_workers"] == 1
        assert details["registered_workers"] == 1
        assert details["registered_tasks"] == 1
        assert isinstance(details["message"], str)
import sys
import types
import asyncio

import pytest
from unittest.mock import patch, MagicMock

from codestory_service.use_real_adapters import get_real_celery_adapter

@pytest.mark.asyncio
async def test_get_real_celery_adapter_eager_mode_skips_strict_health(monkeypatch):
    """Test get_real_celery_adapter does not raise in eager mode even if health is unhealthy."""
    # Patch CeleryAdapter to simulate unhealthy status
    class FakeCeleryAdapter:
        _app = MagicMock()
        _app.conf = MagicMock()
        _app.conf.task_always_eager = False  # Simulate eager via env, not config

        async def check_health(self):
            return "unhealthy", {"error": "No workers"}

    # Patch CeleryAdapter in the target module
    monkeypatch.setattr(
        "codestory_service.use_real_adapters.CeleryAdapter", FakeCeleryAdapter
    )

    # Patch os.getenv to simulate CELERY_TASK_ALWAYS_EAGER=1
    config = get_test_config()
    config.set("CELERY_TASK_ALWAYS_EAGER", "1")

    # Should not raise, even though health is "unhealthy"
    adapter = await get_real_celery_adapter()
    assert isinstance(adapter, FakeCeleryAdapter)