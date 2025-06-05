"""Simplified filesystem ingestion integration test that runs without full service startup."""
import logging
from pathlib import Path
import pytest

from codestory_filesystem.step import FileSystemStep

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
@pytest.fixture(autouse=True)
def celery_eager(monkeypatch):
    """Force Celery to run tasks synchronously for direct step tests."""
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    monkeypatch.setenv("CELERY_TASK_EAGER_PROPAGATES", "1")
# Patch the Celery app config directly for eager mode
    from codestory.ingestion_pipeline.celery_app import app
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
@pytest.fixture
def filesystem_dataset(tmp_path):
    """Fixture: creates a temp directory with >10 files and directories for realistic testing."""
    (tmp_path / "README.md").write_text("# Test Repo\n")
    (tmp_path / "app.py").write_text("print('Hello')")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main(): pass")
    (tmp_path / "src" / "utils.py").write_text("def util(): pass")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Guide")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "input.txt").write_text("input")
    (tmp_path / "data" / "output.txt").write_text("output")
    (tmp_path / "test1.txt").write_text("test1")
    (tmp_path / "test2.txt").write_text("test2")
    (tmp_path / "test3.txt").write_text("test3")
    (tmp_path / "test4.txt").write_text("test4")
    (tmp_path / "test5.txt").write_text("test5")
    return tmp_path

@pytest.fixture(autouse=True, scope="module")
def patch_celery_redis():
    import os
    from codestory.ingestion_pipeline.celery_app import app
    redis_uri = os.environ.get("REDIS_URL") or os.environ.get("REDIS_URI")
    app.conf.update(broker_url=redis_uri, result_backend=redis_uri)

def test_filesystem_step_direct(filesystem_dataset):
    """Test filesystem step execution directly (bypassing Celery)."""
    logger.info("Starting direct filesystem step test")
    test_repo_path = filesystem_dataset
    total_items = len(list(test_repo_path.rglob("*")))
    assert (
        total_items > 10
    ), f"Test repository should have >10 items, got {total_items}"
    step_params = {
        "ignore_patterns": [
            "node_modules/",
            ".git/",
            "__pycache__/",
            "*.pyc",
            "build/",
        ]
    }
    from codestory_filesystem.step import process_filesystem
    result = process_filesystem(str(test_repo_path), **step_params)
    assert result is not None, "Filesystem step should return results"
    assert "status" in result, "Result should contain status"
    assert (
        result["status"] == "success"
    ), f"Step should succeed, got: {result.get('status')}"
    if "files" in result:
        files = result["files"]
        assert len(files) > 0, "Should process some files"
        processed_paths = [f.get("path", "") for f in files]
        assert not any(
            "__pycache__" in path for path in processed_paths
        ), "Should not process __pycache__ files"
        assert not any(
            "build/" in path for path in processed_paths
        ), "Should not process build/ files"
        assert any(
            "README.md" in path for path in processed_paths
        ), "Should process README.md"
        assert any(
            "app.py" in path for path in processed_paths
        ), "Should process app.py"
    logger.info("Direct filesystem step test completed successfully")

def test_filesystem_step_with_various_file_types(filesystem_dataset):
    """Test filesystem step with various file types (bypassing Celery)."""
    logger.info("Testing filesystem step with various file types")
    test_repo_path = filesystem_dataset
    (test_repo_path / "text_file.txt").write_text("Simple text content")
    (test_repo_path / "markdown_file.md").write_text(
        "# Markdown\n\nContent here"
    )
    (test_repo_path / "json_file.json").write_text('{"key": "value"}')
    (test_repo_path / "yaml_file.yaml").write_text(
        "key: value\nlist:\n  - item1\n  - item2"
    )
    (test_repo_path / "python_file.py").write_text("# Python\nprint('hello')")
    (test_repo_path / "javascript_file.js").write_text(
        "// JavaScript\nconsole.log('hello');"
    )
    (test_repo_path / ".gitignore").write_text("")
    from codestory_filesystem.step import process_filesystem
    step_params = {"ignore_patterns": []}
    result = process_filesystem(str(test_repo_path), **step_params)
    assert result["status"] == "success", "Step should succeed"
    if "files" in result:
        files = result["files"]
        processed_extensions = set()
        for file_info in files:
            if "path" in file_info:
                path = Path(file_info["path"])
                if path.suffix:
                    processed_extensions.add(path.suffix)
        expected_extensions = {".txt", ".md", ".json", ".yaml", ".py", ".js"}
        found_extensions = processed_extensions & expected_extensions
        assert (
            len(found_extensions) >= 4
        ), f"Should process multiple file types, found: {found_extensions}"
    logger.info("Various file types test completed successfully")

def test_filesystem_step_error_handling(filesystem_dataset):
    """Test filesystem step error handling."""
    logger.info("Testing filesystem step error handling")
    filesystem_step = FileSystemStep()
    try:
        job_id = filesystem_step.run("/non/existent/path")
        result = filesystem_step.status(job_id)
    except ValueError as e:
        result = {"status": "error", "error": str(e)}
    assert result is not None, "Should return result even on error"
    logger.info("Error handling test completed")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
