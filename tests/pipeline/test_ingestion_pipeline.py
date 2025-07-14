import pytest
import asyncio


class TestIngestionPipelineInterface:
    def test_steps_attribute(self):
        from codestory.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        assert hasattr(pipeline, "steps")
        assert isinstance(pipeline.steps, list)

    def test_incremental_flag(self):
        from codestory.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        assert hasattr(pipeline, "incremental")
        assert isinstance(pipeline.incremental, bool)

    def test_run_method(self):
        from codestory.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        assert hasattr(pipeline, "run")
        # Should be a coroutine function
        assert asyncio.iscoroutinefunction(pipeline.run)

    @pytest.mark.asyncio
    async def test_run_raises_not_implemented(self):
        from codestory.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        with pytest.raises(NotImplementedError, match="Pipeline steps not wired yet"):
            await pipeline.run("dummy_path")
