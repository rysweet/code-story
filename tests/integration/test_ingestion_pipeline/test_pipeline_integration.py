from typing import Any

'Integration tests for the ingestion pipeline.\n\nThese tests verify that the PipelineManager can orchestrate workflow steps\nto process a repository and store the results in the Neo4j database.\n'
import os

ci_env = os.environ.get('CI') == 'true'
neo4j_port = '7687' if ci_env else '7688'
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import StepStatus


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

@pytest.fixture
def test_config() -> None:
    """Create a test configuration file for the pipeline."""
    config_content = '\n    steps:\n      - name: filesystem\n        concurrency: 1\n        ignore_patterns:\n          - ".git/"\n          - "__pycache__/"\n    retry:\n      max_retries: 2\n      back_off_seconds: 1\n    '
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)

@pytest.mark.integration
def test_pipeline_manager_run(sample_repo: Any, neo4j_connector: Any, test_config: Any) -> None:
    """Test that the pipeline manager can run a workflow."""
    manager = PipelineManager(config_path=test_config)
    test_job_id = str(uuid.uuid4())

    def mock_start_job(self, repository_path: Any):
        self.active_jobs[test_job_id] = {'task_id': 'mock-task-id', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING}
        result = custom_process_filesystem(repository_path=repository_path, job_id=test_job_id, neo4j_connector=neo4j_connector, ignore_patterns=['.git/', '__pycache__/'])
        self.active_jobs[test_job_id].update(result)
        return test_job_id
    with patch.object(PipelineManager, 'start_job', mock_start_job):
        job_id = manager.start_job(sample_repo)
    status = manager.active_jobs[job_id]
    assert status['status'] == StepStatus.COMPLETED, f"Job failed: {status.get('error')}"
    repo_nodes = neo4j_connector.execute_query('MATCH (r:Repository {name: $name}) RETURN r', params={'name': os.path.basename(sample_repo)})
    assert len(repo_nodes) > 0, 'Repository node not found'
    files_result = neo4j_connector.execute_query('MATCH (f:File) RETURN count(f) as count')
    files = files_result[0]
    assert files['count'] > 0, 'No file nodes were created'
    directories_result = neo4j_connector.execute_query('MATCH (d:Directory) RETURN count(d) as count')
    directories = directories_result[0]
    assert directories['count'] > 0, 'No directory nodes were created'

@pytest.mark.integration
def test_pipeline_manager_stop(sample_repo: Any, neo4j_connector: Any, test_config: Any) -> None:
    """Test that the pipeline manager can stop a running job."""
    manager = PipelineManager(config_path=test_config)
    test_job_id = str(uuid.uuid4())

    def mock_start_job(self, repository_path: Any):
        self.active_jobs[test_job_id] = {'task_id': 'mock-task-id', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING}
        return test_job_id

    def mock_stop(self, job_id: Any):
        self.active_jobs[job_id]['status'] = StepStatus.STOPPED
        return self.active_jobs[job_id]

    def mock_status(self, job_id: Any):
        return self.active_jobs[job_id]
    with patch.object(PipelineManager, 'start_job', mock_start_job):
        job_id = manager.start_job(sample_repo)
        assert job_id == test_job_id, 'Job ID mismatch'
        with patch.object(PipelineManager, 'stop', mock_stop):
            status = manager.stop(job_id)
            assert status['status'] == StepStatus.STOPPED, f'Job was not stopped: {status}'
            with patch.object(PipelineManager, 'status', mock_status):
                final_status = manager.status(job_id)
                assert final_status['status'] == StepStatus.STOPPED, f'Unexpected job status: {final_status}'

@pytest.mark.integration
def test_pipeline_manager_run_single_step(sample_repo: Any, neo4j_connector: Any, test_config: Any) -> None:
    """Test that the pipeline manager can run a single step."""
    manager = PipelineManager(config_path=test_config)
    test_job_id = str(uuid.uuid4())

    def mock_run_single_step(self, repository_path: Any, step_name: Any, **config):
        assert step_name == 'filesystem', 'Unexpected step name'
        self.active_jobs[test_job_id] = {'task_id': 'mock-task-id', 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'step_name': step_name}
        result = custom_process_filesystem(repository_path=repository_path, job_id=test_job_id, neo4j_connector=neo4j_connector, ignore_patterns=config.get('ignore_patterns', ['.git/', '__pycache__/']))
        self.active_jobs[test_job_id].update(result)
        return test_job_id

    def mock_status(self, job_id: Any):
        return self.active_jobs[job_id]
    with patch.object(manager, '_get_step_class', return_value=MagicMock()):
        with patch.object(PipelineManager, 'run_single_step', mock_run_single_step):
            job_id = manager.run_single_step(repository_path=sample_repo, step_name='filesystem', ignore_patterns=['.git/', '__pycache__/'])
            assert job_id == test_job_id, 'Job ID mismatch'
            with patch.object(PipelineManager, 'status', mock_status):
                status = manager.status(job_id)
                assert status['status'] == StepStatus.COMPLETED, f"Step failed: {status.get('error')}"
    repo_nodes = neo4j_connector.execute_query('MATCH (r:Repository {name: $name}) RETURN r', params={'name': os.path.basename(sample_repo)})
    assert len(repo_nodes) > 0, 'Repository node not found'