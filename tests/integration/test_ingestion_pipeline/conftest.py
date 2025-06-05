import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def filesystem_dataset():
    """
    Creates a temporary directory with a test repository structure for filesystem ingestion tests.
    Yields the path to the root of the test repository, then cleans up after the test.
    """
    temp_dir = tempfile.mkdtemp(prefix="codestory_fs_simple_")
    test_repo_path = Path(temp_dir)
    # Create test repository structure
    dirs = ["src/main", "src/test", "docs", "config"]
    for dir_path in dirs:
        (test_repo_path / dir_path).mkdir(parents=True, exist_ok=True)
    gitignore_content = "\n# Python\n*.pyc\n__pycache__/\n*.pyo\n\n# Node modules  \nnode_modules/\n\n# Build directories\nbuild/\ndist/\n\n# Git directory\n.git/\n        ".strip()
    (test_repo_path / ".gitignore").write_text(gitignore_content)
    (test_repo_path / "README.md").write_text(
        "# Test Repository\n\nThis is a test repository."
    )
    (test_repo_path / "src/main/app.py").write_text(
        '"""Main application."""\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n'
    )
    (test_repo_path / "src/test/test_app.py").write_text(
        '"""Tests for app."""\n\ndef test_main():\n    assert True\n'
    )
    (test_repo_path / "docs/guide.md").write_text(
        "# User Guide\n\nHow to use this application."
    )
    (test_repo_path / "config/settings.json").write_text('{"debug": true}')
    (test_repo_path / "src/main/__pycache__").mkdir(exist_ok=True)
    (test_repo_path / "src/main/__pycache__/app.pyc").write_bytes(
        b"\x00\x01\x02\x03"
    )
    (test_repo_path / "build").mkdir(exist_ok=True)
    (test_repo_path / "build/output.js").write_text("compiled output")
    try:
        yield test_repo_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)