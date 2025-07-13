import pytest

# Contract: Importing Settings must succeed
def test_import_settings():
    from codestory.config import Settings

# Contract: Instantiating Settings with no env vars should fail (ValidationError or NotImplementedError)
def test_settings_instantiation_fails_without_env(monkeypatch):
    from codestory.config import Settings

    # Ensure relevant env vars are unset
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_USER", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    with pytest.raises((Exception,)):
        Settings()

# Contract: Settings exposes required attributes (skipped until implemented)
@pytest.mark.skip(reason="Settings attributes not implemented yet")
def test_settings_has_neo4j_uri(monkeypatch):
    from codestory.config import Settings
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    s = Settings()
    assert isinstance(s.neo4j_uri, str)

@pytest.mark.skip(reason="Settings attributes not implemented yet")
def test_settings_has_neo4j_user(monkeypatch):
    from codestory.config import Settings
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    s = Settings()
    assert isinstance(s.neo4j_user, str)

@pytest.mark.skip(reason="Settings attributes not implemented yet")
def test_settings_has_neo4j_password(monkeypatch):
    from codestory.config import Settings
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    s = Settings()
    assert isinstance(s.neo4j_password, str)