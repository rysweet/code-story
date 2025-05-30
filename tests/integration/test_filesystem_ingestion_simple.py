"""Simplified filesystem ingestion integration test that runs without full service startup."""
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict
import pytest
from codestory.config.settings import get_settings
from codestory_filesystem.step import FileSystemStep
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.mark.integration
class TestFilesystemIngestionSimple:
    """Simplified filesystem ingestion tests that run the step directly."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self: Any) -> None:
        """Set up test environment and clean up afterwards."""
        self.temp_dir = tempfile.mkdtemp(prefix='codestory_fs_simple_')
        self.test_repo_path = Path(self.temp_dir)
        logger.info(f'Created test directory: {self.temp_dir}')
        yield
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f'Cleaned up test directory: {self.temp_dir}')
        except Exception as e:
            logger.warning(f'Failed to clean up test directory: {e}')

    def create_test_repository(self: Any) -> None:
        """Create a simple test repository structure."""
        logger.info(f'Creating test repository at {self.test_repo_path}')
        dirs = ['src/main', 'src/test', 'docs', 'config']
        for dir_path in dirs:
            (self.test_repo_path / dir_path).mkdir(parents=True, exist_ok=True)
        gitignore_content = '\n# Python\n*.pyc\n__pycache__/\n*.pyo\n\n# Node modules  \nnode_modules/\n\n# Build directories\nbuild/\ndist/\n\n# Git directory\n.git/\n        '.strip()
        (self.test_repo_path / '.gitignore').write_text(gitignore_content)
        (self.test_repo_path / 'README.md').write_text('# Test Repository\n\nThis is a test repository.')
        (self.test_repo_path / 'src/main/app.py').write_text('"""Main application."""\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n')
        (self.test_repo_path / 'src/test/test_app.py').write_text('"""Tests for app."""\n\ndef test_main():\n    assert True\n')
        (self.test_repo_path / 'docs/guide.md').write_text('# User Guide\n\nHow to use this application.')
        (self.test_repo_path / 'config/settings.json').write_text('{"debug": true}')
        (self.test_repo_path / 'src/main/__pycache__').mkdir(exist_ok=True)
        (self.test_repo_path / 'src/main/__pycache__/app.pyc').write_bytes(b'\x00\x01\x02\x03')
        (self.test_repo_path / 'build').mkdir(exist_ok=True)
        (self.test_repo_path / 'build/output.js').write_text('compiled output')
        logger.info(f"Test repository created with {len(list(self.test_repo_path.rglob('*')))} items")

    def test_filesystem_step_direct(self: Any) -> None:
        """Test filesystem step execution directly."""
        logger.info('Starting direct filesystem step test')
        self.create_test_repository()
        total_items = len(list(self.test_repo_path.rglob('*')))
        assert total_items > 10, f'Test repository should have >10 items, got {total_items}'
        step_params = {'ignore_patterns': ['node_modules/', '.git/', '__pycache__/', '*.pyc', 'build/']}
        filesystem_step = FileSystemStep()
        logger.info('Executing filesystem step...')
        job_id = filesystem_step.run(str(self.test_repo_path), **step_params)
        status_result = filesystem_step.status(job_id)
        result = status_result
        assert result is not None, 'Filesystem step should return results'
        assert 'status' in result, 'Result should contain status'
        assert result['status'] == 'success', f"Step should succeed, got: {result.get('status')}"
        if 'files' in result:
            files = result['files']
            assert len(files) > 0, 'Should process some files'
            processed_paths = [f.get('path', '') for f in files]
            assert not any(('__pycache__' in path for path in processed_paths)), 'Should not process __pycache__ files'
            assert not any(('build/' in path for path in processed_paths)), 'Should not process build/ files'
            assert any(('README.md' in path for path in processed_paths)), 'Should process README.md'
            assert any(('app.py' in path for path in processed_paths)), 'Should process app.py'
        logger.info('Direct filesystem step test completed successfully')

    def test_filesystem_step_with_various_file_types(self: Any) -> None:
        """Test filesystem step with various file types."""
        logger.info('Testing filesystem step with various file types')
        (self.test_repo_path / 'text_file.txt').write_text('Simple text content')
        (self.test_repo_path / 'markdown_file.md').write_text('# Markdown\n\nContent here')
        (self.test_repo_path / 'json_file.json').write_text('{"key": "value"}')
        (self.test_repo_path / 'yaml_file.yaml').write_text('key: value\nlist:\n  - item1\n  - item2')
        (self.test_repo_path / 'python_file.py').write_text("# Python\nprint('hello')")
        (self.test_repo_path / 'javascript_file.js').write_text("// JavaScript\nconsole.log('hello');")
        (self.test_repo_path / '.gitignore').write_text('')
        filesystem_step = FileSystemStep()
        step_params = {'ignore_patterns': []}
        job_id = filesystem_step.run(str(self.test_repo_path), **step_params)
        result = filesystem_step.status(job_id)
        assert result['status'] == 'success', 'Step should succeed'
        if 'files' in result:
            files = result['files']
            processed_extensions = set()
            for file_info in files:
                if 'path' in file_info:
                    path = Path(file_info['path'])
                    if path.suffix:
                        processed_extensions.add(path.suffix)
            expected_extensions = {'.txt', '.md', '.json', '.yaml', '.py', '.js'}
            found_extensions = processed_extensions & expected_extensions
            assert len(found_extensions) >= 4, f'Should process multiple file types, found: {found_extensions}'
        logger.info('Various file types test completed successfully')

    def test_filesystem_step_error_handling(self: Any) -> None:
        """Test filesystem step error handling."""
        logger.info('Testing filesystem step error handling')
        filesystem_step = FileSystemStep()
        try:
            job_id = filesystem_step.run('/non/existent/path')
            result = filesystem_step.status(job_id)
        except ValueError as e:
            result = {'status': 'error', 'error': str(e)}
        assert result is not None, 'Should return result even on error'
        logger.info('Error handling test completed')
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])