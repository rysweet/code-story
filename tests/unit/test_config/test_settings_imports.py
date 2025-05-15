"""Test that settings modules can be imported at the module level in test environments."""

import pytest


def test_settings_import():
    """Test importing settings at the module level."""
    import sys
    try:
        # This is the problematic import - ensure it works in test environment
        from codestory.ingestion_pipeline.celery_app import app, settings
        
        # If we got here without error, the test passes
        assert settings is not None
    except Exception as e:
        pytest.fail(f"Failed to import settings: {e}")
        
        
def test_settings_instance():
    """Test creating a settings instance directly."""
    from codestory.config.settings import Settings
    
    # Create a settings instance directly
    # This should work because we've patched Settings.__new__
    settings = Settings()
    
    # We should get a valid settings object
    assert settings is not None
    assert hasattr(settings, 'neo4j')
    assert hasattr(settings, 'redis')
    assert hasattr(settings, 'openai')
    assert hasattr(settings, 'azure_openai')
    assert hasattr(settings, 'service')
    assert hasattr(settings, 'ingestion')
    assert hasattr(settings, 'plugins')
    assert hasattr(settings, 'telemetry')
    assert hasattr(settings, 'interface')
    assert hasattr(settings, 'azure')


def test_get_settings():
    """Test getting a settings instance via get_settings()."""
    from codestory.config.settings import get_settings
    
    # Get a settings instance
    settings = get_settings()
    
    # We should get a valid settings object
    assert settings is not None
    assert hasattr(settings, 'neo4j')
    assert settings.neo4j.uri == "bolt://localhost:7687"
    assert settings.neo4j.username == "neo4j"
    assert settings.neo4j.password.get_secret_value() == "password"
    assert settings.neo4j.database == "testdb"
    
    # Check redis settings
    assert hasattr(settings, 'redis')
    assert settings.redis.uri == "redis://localhost:6379/0"
    
    # Check openai settings
    assert hasattr(settings, 'openai')
    assert settings.openai.api_key.get_secret_value() == "sk-test-key-openai"
    
    # Check azure openai settings
    assert hasattr(settings, 'azure_openai')
    assert settings.azure_openai.deployment_id == "gpt-4o"