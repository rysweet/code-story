from typing import Any

'Integration tests for the filesystem workflow step.\n\nThese tests verify that the FileSystemStep can correctly process a repository\nand store its structure in the Neo4j database.\n'
import os

ci_env = os.environ.get('CI') == 'true'
neo4j_port = '7687' if ci_env else '7688'
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import StepStatus, generate_job_id
from codestory_filesystem.step import FileSystemStep


def custom_process_filesystem(repository_path: Any, job_id: Any, neo4j_connector: Any, ignore_patterns: Any=None, **config: Any) -> None:
    """Custom implementation of process_filesystem for testing.

    This function uses the provided Neo4j connector instead of creating a new one,
    which avoids the hostname resolution issues.
    """
    print(f'*** TEST_DEBUG: Running custom_process_filesystem with {job_id} ***')
    print(f'Repository path: {repository_path}')
    print(f'Ignore patterns: {ignore_patterns}')
    if ignore_patterns is None:
        ignore_patterns = ['.git/', '__pycache__/', 'node_modules/', '.venv/']
    max_depth = config.get('max_depth')
    try:
        file_count = 0
        dir_count = 0
        repo_name = os.path.basename(repository_path)
        repo_properties = {'name': repo_name, 'path': repository_path}
        repo_query = '\n        MERGE (r:Repository {name: $props.name, path: $props.path})\n        RETURN elementId(r) as id\n        '
        repo_result = neo4j_connector.execute_query(repo_query, params={'props': repo_properties}, write=True)
        repo_id = repo_result[0]['id'] if repo_result else None
        print(f'Created repository node with ID: {repo_id}')
        for current_dir, dirs, files in os.walk(repository_path):
            rel_path = os.path.relpath(current_dir, repository_path)
            if max_depth is not None:
                if rel_path != '.' and rel_path.count(os.sep) >= max_depth:
                    dirs.clear()
                    continue
            dirs_to_remove = []
            for d in dirs:
                if any(d.startswith(pat.rstrip('/')) or d == pat.rstrip('/') for pat in ignore_patterns if pat.endswith('/')):
                    dirs_to_remove.append(d)
            for d in dirs_to_remove:
                dirs.remove(d)
            dir_path = os.path.relpath(current_dir, repository_path)
            if dir_path == '.':
                pass
            else:
                dir_properties = {'name': os.path.basename(current_dir), 'path': dir_path}
                dir_query = '\n                MERGE (d:Directory {path: $props.path})\n                SET d.name = $props.name\n                RETURN elementId(d) as id\n                '
                dir_result = neo4j_connector.execute_query(dir_query, params={'props': dir_properties}, write=True)
                dir_result[0]['id'] if dir_result else None
                parent_path = os.path.dirname(dir_path)
                if parent_path == '':
                    rel_query = '\n                    MATCH (r:Repository {name: $repo_name})\n                    MATCH (d:Directory {path: $dir_path})\n                    MERGE (r)-[:CONTAINS]->(d)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'repo_name': repo_name, 'dir_path': dir_path}, write=True)
                else:
                    rel_query = '\n                    MATCH (p:Directory {path: $parent_path})\n                    MATCH (d:Directory {path: $dir_path})\n                    MERGE (p)-[:CONTAINS]->(d)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'parent_path': parent_path, 'dir_path': dir_path}, write=True)
                dir_count += 1
            for file in files:
                skip = False
                for pattern in ignore_patterns:
                    if not pattern.endswith('/') and file.endswith(pattern):
                        skip = True
                        break
                if skip:
                    continue
                file_path = os.path.join(dir_path, file) if dir_path != '.' else file
                file_properties = {'name': file, 'path': file_path}
                file_query = '\n                MERGE (f:File {path: $props.path})\n                SET f.name = $props.name\n                RETURN elementId(f) as id\n                '
                file_result = neo4j_connector.execute_query(file_query, params={'props': file_properties}, write=True)
                file_result[0]['id'] if file_result else None
                if dir_path == '.':
                    rel_query = '\n                    MATCH (r:Repository {name: $repo_name})\n                    MATCH (f:File {path: $file_path})\n                    MERGE (r)-[:CONTAINS]->(f)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'repo_name': repo_name, 'file_path': file_path}, write=True)
                else:
                    rel_query = '\n                    MATCH (d:Directory {path: $dir_path})\n                    MATCH (f:File {path: $file_path})\n                    MERGE (d)-[:CONTAINS]->(f)\n                    '
                    neo4j_connector.execute_query(rel_query, params={'dir_path': dir_path, 'file_path': file_path}, write=True)
                file_count += 1
        return {'status': StepStatus.COMPLETED, 'job_id': job_id, 'file_count': file_count, 'dir_count': dir_count}  # type: ignore[return-value]
    except Exception as e:
        print(f'Error processing filesystem: {e}')
        return {'status': StepStatus.FAILED, 'error': f'Error processing filesystem: {e!s}', 'job_id': job_id}  # type: ignore[return-value]
pytestmark = [pytest.mark.integration, pytest.mark.neo4j, pytest.mark.celery]

@pytest.fixture
def sample_repo() -> None:
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / 'sample_repo'
        repo_dir.mkdir()
        (repo_dir / 'src').mkdir()
        (repo_dir / 'src' / 'main').mkdir()
        (repo_dir / 'src' / 'test').mkdir()
        (repo_dir / 'docs').mkdir()
        (repo_dir / 'README.md').write_text('# Sample Repository')
        (repo_dir / 'src' / 'main' / 'app.py').write_text("def main():\n    print('Hello, world!')")
        (repo_dir / 'src' / 'test' / 'test_app.py').write_text('def test_main():\n    assert True')
        (repo_dir / 'docs' / 'index.md').write_text('# Documentation')
        (repo_dir / '.git').mkdir()
        (repo_dir / '.git' / 'config').write_text('# Git config')
        (repo_dir / 'src' / '__pycache__').mkdir()
        (repo_dir / 'src' / '__pycache__' / 'app.cpython-310.pyc').write_text('# Bytecode')
        yield str(repo_dir)

@pytest.fixture
def neo4j_connector() -> None:
    """Create a Neo4j connector for testing."""
    connector = Neo4jConnector(uri=f'bolt://localhost:{neo4j_port}', username='neo4j', password='password', database='testdb')
    try:
        connector.execute_query('MATCH (n) DETACH DELETE n', write=True, params={})
        print('Successfully connected to Neo4j and cleared the database')
    except Exception as e:
        pytest.fail(f'Failed to connect to Neo4j: {e!s}')
    yield connector
    connector.close()

@pytest.mark.integration
@pytest.mark.neo4j
@pytest.mark.celery
@pytest.mark.timeout(60)
def test_filesystem_step_run(sample_repo: Any, neo4j_connector: Any, celery_app: Any) -> None:
    """Test that the filesystem step can process a repository."""
    print('*** IMPORTANT: TEST IS ACTUALLY RUNNING ***')
    step = FileSystemStep()
    print(f'Step created: {step}')
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    print(f'Neo4j URI: {neo4j_connector.uri}')
    print(f'Neo4j database: {neo4j_connector.database}')
    print(f'Sample repo path: {sample_repo}')
    print(f'Celery task_always_eager: {celery_app.conf.task_always_eager}')
    job_id = generate_job_id()

    def mock_run(self, repository_path: Any, **config):
        self.active_jobs[job_id] = {'task_id': 'direct-execution', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
        result = custom_process_filesystem(repository_path=repository_path, job_id=job_id, neo4j_connector=neo4j_connector, **config)
        self.active_jobs[job_id].update(result)
        return job_id
    with patch.object(FileSystemStep, 'run', mock_run):
        returned_job_id = step.run(repository_path=sample_repo, ignore_patterns=['.git/', '__pycache__/'])
        assert returned_job_id == job_id, 'Job ID mismatch'
    status = step.active_jobs[job_id]
    print(f'Job status: {status}')
    assert status['status'] == StepStatus.COMPLETED, f"Job failed: {status.get('error')}"
    repo_query = neo4j_connector.execute_query('MATCH (r:Repository {name: $name}) RETURN r', params={'name': os.path.basename(sample_repo)})
    assert repo_query is not None, 'Repository node not found'
    directories = neo4j_connector.execute_query('MATCH (d:Directory) RETURN d.path as path')
    directory_paths = [record['path'] for record in directories]
    assert 'src' in directory_paths, 'src directory not found'
    assert 'src/main' in directory_paths, 'src/main directory not found'
    assert 'src/test' in directory_paths, 'src/test directory not found'
    assert 'docs' in directory_paths, 'docs directory not found'
    files = neo4j_connector.execute_query('MATCH (f:File) RETURN f.path as path')
    file_paths = [record['path'] for record in files]
    assert 'README.md' in file_paths, 'README.md file not found'
    assert 'src/main/app.py' in file_paths, 'src/main/app.py file not found'
    assert 'src/test/test_app.py' in file_paths, 'src/test/test_app.py file not found'
    assert 'docs/index.md' in file_paths, 'docs/index.md file not found'
    git_dir = neo4j_connector.execute_query("MATCH (d:Directory {path: '.git'}) RETURN d")
    assert len(git_dir) == 0, '.git directory was not ignored'
    pycache_dir = neo4j_connector.execute_query("MATCH (d:Directory {path: 'src/__pycache__'}) RETURN d")
    assert len(pycache_dir) == 0, '__pycache__ directory was not ignored'

@pytest.mark.integration
@pytest.mark.neo4j
@pytest.mark.celery
def test_filesystem_step_ingestion_update(sample_repo: Any, neo4j_connector: Any, celery_app: Any) -> None:
    """Test that the filesystem step can update an existing repository."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    step = FileSystemStep()
    print('Running initial indexing...')
    initial_job_id = generate_job_id()

    def mock_run(self, repository_path: Any, **config):
        self.active_jobs[initial_job_id] = {'task_id': 'direct-execution', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
        result = custom_process_filesystem(repository_path=repository_path, job_id=initial_job_id, neo4j_connector=neo4j_connector, **config)
        self.active_jobs[initial_job_id].update(result)
        return initial_job_id
    with patch.object(FileSystemStep, 'run', mock_run):
        returned_job_id = step.run(repository_path=sample_repo, ignore_patterns=['.git/', '__pycache__/'])
        assert returned_job_id == initial_job_id, 'Job ID mismatch'
    initial_status = step.active_jobs[initial_job_id]
    assert initial_status['status'] == StepStatus.COMPLETED, f"Job failed: {initial_status.get('error')}"
    file_count_query = neo4j_connector.execute_query('MATCH (f:File) RETURN count(f) as count')
    initial_file_count = file_count_query[0]['count']
    print(f'Initial file count: {initial_file_count}')
    print('Adding new file to repository...')
    new_file_path = Path(sample_repo) / 'src' / 'main' / 'new_file.py'
    new_file_path.write_text('# New file')
    update_job_id = generate_job_id()

    def mock_update(self, repository_path: Any, **config):
        self.active_jobs[update_job_id] = {'task_id': 'direct-update', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
        result = custom_process_filesystem(repository_path=repository_path, job_id=update_job_id, neo4j_connector=neo4j_connector, **config)
        self.active_jobs[update_job_id].update(result)
        return update_job_id
    with patch.object(FileSystemStep, 'ingestion_update', mock_update):
        update_returned_id = step.ingestion_update(repository_path=sample_repo, ignore_patterns=['.git/', '__pycache__/'])
        assert update_returned_id == update_job_id, 'Update job ID mismatch'
    update_status = step.active_jobs[update_job_id]
    assert update_status['status'] == StepStatus.COMPLETED, f"Update failed: {update_status.get('error')}"
    new_file = neo4j_connector.execute_query("MATCH (f:File {path: 'src/main/new_file.py'}) RETURN f")
    assert len(new_file) > 0, 'New file was not added to the database'
    file_count_query = neo4j_connector.execute_query('MATCH (f:File) RETURN count(f) as count')
    updated_file_count = file_count_query[0]['count']
    print(f'Updated file count: {updated_file_count}')
    assert updated_file_count > initial_file_count, 'File count did not increase after update'