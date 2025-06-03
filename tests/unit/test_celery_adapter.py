"""Unit tests for CeleryAdapter."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

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
        assert details == {"message": "Eager mode enabled, no workers needed"}
        
        # Assert that inspect was not called
        mock_inspect.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_with_eager_mode_enabled_via_env(self, celery_adapter):
        """Test that check_health returns healthy when CELERY_TASK_ALWAYS_EAGER env var is truthy."""
        # Ensure app config is False
        celery_adapter._app.conf.task_always_eager = False
        
        # Set environment variable
        with patch.dict(os.environ, {"CELERY_TASK_ALWAYS_EAGER": "1"}):
            # Mock the inspect method to ensure it's not called
            mock_inspect = MagicMock()
            celery_adapter._app.control.inspect = mock_inspect
            
            # Call check_health
            status, details = await celery_adapter.check_health()
            
            # Assert early return with healthy status
            assert status == "healthy"
            assert details == {"message": "Eager mode enabled, no workers needed"}
            
            # Assert that inspect was not called
            mock_inspect.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_with_eager_mode_env_true_string(self, celery_adapter):
        """Test that check_health returns healthy when CELERY_TASK_ALWAYS_EAGER is 'true'."""
        # Ensure app config is False
        celery_adapter._app.conf.task_always_eager = False
        
        # Set environment variable to 'true'
        with patch.dict(os.environ, {"CELERY_TASK_ALWAYS_EAGER": "true"}):
            # Mock the inspect method to ensure it's not called
            mock_inspect = MagicMock()
            celery_adapter._app.control.inspect = mock_inspect
            
            # Call check_health
            status, details = await celery_adapter.check_health()
            
            # Assert early return with healthy status
            assert status == "healthy"
            assert details == {"message": "Eager mode enabled, no workers needed"}
            
            # Assert that inspect was not called
            mock_inspect.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_health_without_eager_mode_calls_inspect(self, celery_adapter):
        """Test that check_health calls inspect when eager mode is disabled."""
        # Ensure eager mode is disabled
        celery_adapter._app.conf.task_always_eager = False
        
        # Clear environment variable
        with patch.dict(os.environ, {}, clear=True):
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
            mock_inspector.registered.assert_called_once()
            
            # Assert healthy response
            assert status == "healthy"
            assert "active_workers" in details
            assert "registered_tasks" in details