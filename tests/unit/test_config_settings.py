from codestory.config.settings import get_settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.app_name == "code-story"
    assert settings.environment in ("development", "testing", "production")
    assert settings.neo4j.uri.startswith("bolt://")
    assert hasattr(settings.openai, "api_key")
    assert hasattr(settings, "ingestion")
    assert hasattr(settings, "service")
