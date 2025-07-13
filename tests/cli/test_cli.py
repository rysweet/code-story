import pytest

def test_import_cli_app_should_fail():
    """
    Importing codestory.cli.app should raise ImportError until implemented.
    """
    with pytest.raises(ImportError):
        import codestory.cli.app  # noqa: F401

@pytest.mark.skip(reason="CLI interface contract: enable after codestory.cli.app exists")
def test_cli_app_is_typer_instance():
    """
    If codestory.cli.app exists, it should expose a Typer app instance.
    """
    app_mod = pytest.importorskip("codestory.cli.app")
    import typer
    assert isinstance(app_mod.app, typer.Typer)

@pytest.mark.skip(reason="CLI entrypoint contract: enable after codestory.cli.main exists")
def test_cli_main_calls_app(monkeypatch):
    """
    If codestory.cli.main exists, running it should call app() and exit 0.
    """
    main_mod = pytest.importorskip("codestory.cli.main")
    app_mod = pytest.importorskip("codestory.cli.app")

    called = {}

    def fake_app():
        called["ran"] = True
        raise SystemExit(0)

    monkeypatch.setattr(app_mod, "app", fake_app)
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 0
    assert called.get("ran")