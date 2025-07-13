import pytest

def test_import_ingestion_pipeline():
    """
    Test that importing IngestionPipeline from codestory.pipeline fails (expected until implemented).
    """
    with pytest.raises(ImportError):
        from codestory.pipeline import IngestionPipeline  # noqa: F401

@pytest.mark.skip(reason="Interface tests will fail until IngestionPipeline is implemented")
class TestIngestionPipelineInterface:
    def test_steps_attribute(self):
        from codestory.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()
        assert hasattr(pipeline, "steps")
        assert isinstance(pipeline.steps, list)

    def test_run_method(self):
        from codestory.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()
        assert hasattr(pipeline, "run")
        # Should be a coroutine or method; actual type check will be refined after implementation

    def test_incremental_flag(self):
        from codestory.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()
        assert hasattr(pipeline, "incremental")
        # Should be a bool or property; actual type check will be refined after implementation