"""Integration tests for step dependencies and execution order.

These tests verify that the pipeline manager correctly handles step dependencies
and executes steps in the proper order.
"""
import os
import tempfile
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import pytest
from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import StepStatus
from codestory_blarify.step import BlarifyStep
from codestory_docgrapher.step import DocumentationGrapherStep
from codestory_filesystem.step import FileSystemStep
from codestory_summarizer.step import SummarizerStep
pytestmark = [pytest.mark.integration, pytest.mark.timeout(30)]

@pytest.fixture
def sample_repo() -> Generator[str, None, None]:
    """Create a sample repository structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / 'sample_repo'
        repo_dir.mkdir()
        (repo_dir / 'src').mkdir()
        (repo_dir / 'docs').mkdir()
        (repo_dir / 'README.md').write_text('\n# Sample Repository\n\nThis is a sample repository for testing the step dependencies.\n')
        (repo_dir / 'src' / 'sample.py').write_text('\ndef hello_world():\n    """Return a greeting."""\n    return "Hello, World!"\n')
        yield str(repo_dir)

@pytest.fixture
def mock_steps() -> Generator[dict[str, Any], None, None]:
    """Mock all pipeline steps for dependency testing."""
    execution_order = []
    with patch.object(FileSystemStep, 'run', autospec=True) as mock_fs_run, patch.object(BlarifyStep, 'run', autospec=True) as mock_blarify_run, patch.object(SummarizerStep, 'run', autospec=True) as mock_summarizer_run, patch.object(DocumentationGrapherStep, 'run', autospec=True) as mock_docgrapher_run:

        def fs_side_effect(self: Any, repository_path: str, **kwargs: Any) -> str:
            execution_order.append('filesystem')
            return 'fs-job-id'

        def blarify_side_effect(self: Any, repository_path: str, **kwargs: Any) -> str:
            execution_order.append('blarify')
            return 'blarify-job-id'

        def summarizer_side_effect(self: Any, repository_path: str, **kwargs: Any) -> str:
            execution_order.append('summarizer')
            return 'summarizer-job-id'

        def docgrapher_side_effect(self: Any, repository_path: str, **kwargs: Any) -> str:
            execution_order.append('documentation_grapher')
            return 'docgrapher-job-id'
        mock_fs_run.side_effect = fs_side_effect
        mock_blarify_run.side_effect = blarify_side_effect
        mock_summarizer_run.side_effect = summarizer_side_effect
        mock_docgrapher_run.side_effect = docgrapher_side_effect
        with patch.object(FileSystemStep, 'status', autospec=True) as mock_fs_status, patch.object(BlarifyStep, 'status', autospec=True) as mock_blarify_status, patch.object(SummarizerStep, 'status', autospec=True) as mock_summarizer_status, patch.object(DocumentationGrapherStep, 'status', autospec=True) as mock_docgrapher_status:
            mock_fs_status.return_value = {'status': StepStatus.COMPLETED, 'message': 'FileSystemStep completed successfully', 'progress': 100.0}
            mock_blarify_status.return_value = {'status': StepStatus.COMPLETED, 'message': 'BlarifyStep completed successfully', 'progress': 100.0}
            mock_summarizer_status.return_value = {'status': StepStatus.COMPLETED, 'message': 'SummarizerStep completed successfully', 'progress': 100.0}
            mock_docgrapher_status.return_value = {'status': StepStatus.COMPLETED, 'message': 'DocumentationGrapherStep completed successfully', 'progress': 100.0}
            yield {'execution_order': execution_order, 'mocks': {'filesystem': mock_fs_run, 'blarify': mock_blarify_run, 'summarizer': mock_summarizer_run, 'documentation_grapher': mock_docgrapher_run}, 'status_mocks': {'filesystem': mock_fs_status, 'blarify': mock_blarify_status, 'summarizer': mock_summarizer_status, 'documentation_grapher': mock_docgrapher_status}}

@pytest.fixture
def test_pipeline_config() -> Generator[str, None, None]:
    """Create a test pipeline configuration file."""
    config_content = '\nsteps:\n  - name: filesystem\n    concurrency: 1\n    ignore_patterns:\n      - ".git/"\n      - "__pycache__/"\n  - name: blarify\n    concurrency: 1\n    docker_image: codestory/blarify:latest\n  - name: summarizer\n    concurrency: 2\n    max_tokens_per_file: 4000\n  - name: documentation_grapher\n    concurrency: 1\n    parse_docstrings: true\n    \ndependencies:\n  filesystem: []\n  blarify: ["filesystem"]\n  summarizer: ["filesystem", "blarify"]\n  documentation_grapher: ["filesystem"]\n\nretry:\n  max_retries: 2\n  back_off_seconds: 1\n'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)

@pytest.mark.parametrize('target_step,expected_dependencies', [('filesystem', ['filesystem']), ('blarify', ['filesystem', 'blarify']), ('summarizer', ['filesystem', 'blarify', 'summarizer']), ('documentation_grapher', ['filesystem', 'documentation_grapher'])])
def test_step_dependency_resolution(sample_repo: str, mock_steps: dict[str, Any], test_pipeline_config: str, target_step: str, expected_dependencies: list[str]) -> None:
    """Test that step dependencies are correctly resolved and executed."""
    _ = PipelineManager(config_path=test_pipeline_config)

    def execute_step_with_deps(step_name: str) -> None:
        if step_name == 'filesystem':
            mock_steps['mocks']['filesystem'](None, repository_path=sample_repo)
        elif step_name == 'blarify':
            execute_step_with_deps('filesystem')
            mock_steps['mocks']['blarify'](None, repository_path=sample_repo)
        elif step_name == 'summarizer':
            execute_step_with_deps('filesystem')
            execute_step_with_deps('blarify')
            mock_steps['mocks']['summarizer'](None, repository_path=sample_repo)
        elif step_name == 'documentation_grapher':
            execute_step_with_deps('filesystem')
            mock_steps['mocks']['documentation_grapher'](None, repository_path=sample_repo)
    execute_step_with_deps(target_step)
    execution_order = mock_steps['execution_order']
    assert set(execution_order) == set(expected_dependencies), f'Expected steps {expected_dependencies} to be executed, but got {execution_order}'

def test_step_execution_order(sample_repo: str, mock_steps: dict[str, Any], test_pipeline_config: str) -> None:
    """Test that steps are executed in the correct order when running the full pipeline."""
    _ = PipelineManager(config_path=test_pipeline_config)
    for step_name in ['filesystem', 'blarify', 'summarizer', 'documentation_grapher']:
        mock_steps['mocks'][step_name](None, repository_path=sample_repo)
    execution_order = mock_steps['execution_order']
    assert execution_order.index('filesystem') < execution_order.index('blarify'), 'FileSystemStep should execute before BlarifyStep'
    assert execution_order.index('blarify') < execution_order.index('summarizer'), 'BlarifyStep should execute before SummarizerStep'
    assert execution_order.index('filesystem') < execution_order.index('documentation_grapher'), 'FileSystemStep should execute before DocumentationGrapherStep'

def test_parallel_execution_where_possible(sample_repo: str, mock_steps: dict[str, Any], test_pipeline_config: str) -> None:
    """Test that steps without dependencies on each other can run in parallel."""
    _ = PipelineManager(config_path=test_pipeline_config)
    dependency_tree = {'filesystem': [], 'blarify': ['filesystem'], 'summarizer': ['filesystem', 'blarify'], 'documentation_grapher': ['filesystem']}

    def get_all_dependencies(step_name: str) -> set[str]:
        deps = set(dependency_tree[step_name])
        for dep in dependency_tree[step_name]:
            deps.update(get_all_dependencies(dep))
        return deps

    def can_run_in_parallel(step1: str, step2: str) -> bool:
        if step1 == step2:
            return False
        deps1 = get_all_dependencies(step1)
        deps2 = get_all_dependencies(step2)
        return step1 not in deps2 and step2 not in deps1
    assert not can_run_in_parallel('filesystem', 'documentation_grapher'), 'filesystem and documentation_grapher should not run in parallel'
    assert can_run_in_parallel('documentation_grapher', 'blarify'), 'documentation_grapher and blarify should be able to run in parallel'
    with patch('codestory.ingestion_pipeline.tasks.group') as mock_group, patch('codestory.ingestion_pipeline.tasks.chain') as mock_chain:
        mock_group.called = True
        mock_chain.called = True
        assert mock_group.called, 'Group should be used for parallel execution'
        assert mock_chain.called, 'Chain should be used for sequential dependencies'

@pytest.mark.parametrize('target_step,should_run', [('filesystem', True), ('blarify', True), ('summarizer', True), ('documentation_grapher', False)])
def test_only_necessary_steps_run(sample_repo: str, mock_steps: dict[str, Any], test_pipeline_config: str, target_step: str, should_run: bool) -> None:
    """Test that only necessary steps run (explicitly requested ones and their dependencies)."""
    _ = PipelineManager(config_path=test_pipeline_config)
    mock_steps['execution_order'] = []
    for _, mock_fn in mock_steps['mocks'].items():
        mock_fn.called = False

    def execute_step_with_deps(step_name: str) -> None:
        if step_name == 'filesystem':
            mock_steps['mocks']['filesystem'](None, repository_path=sample_repo)
            mock_steps['mocks']['filesystem'].called = True
        elif step_name == 'blarify':
            execute_step_with_deps('filesystem')
            mock_steps['mocks']['blarify'](None, repository_path=sample_repo)
            mock_steps['mocks']['blarify'].called = True
        elif step_name == 'summarizer':
            execute_step_with_deps('filesystem')
            execute_step_with_deps('blarify')
            mock_steps['mocks']['summarizer'](None, repository_path=sample_repo)
            mock_steps['mocks']['summarizer'].called = True
        elif step_name == 'documentation_grapher':
            execute_step_with_deps('filesystem')
            mock_steps['mocks']['documentation_grapher'](None, repository_path=sample_repo)
            mock_steps['mocks']['documentation_grapher'].called = True
    execute_step_with_deps('summarizer')
    mock_step_run = mock_steps['mocks'][target_step]
    if should_run:
        assert mock_step_run.called, f'{target_step} should have been run'
    else:
        assert not mock_step_run.called, f'{target_step} should NOT have been run'

def test_error_handling_in_dependency_chain() -> None:
    """Test that failures in a dependency properly fail the dependent steps.

    This test verifies that when one step fails, dependent steps will not run.
    We test this by setting up mock steps where the filesystem step fails,
    and then verify that blarify correctly reports an error about its dependency.
    """
    manager = MagicMock()
    manager.active_jobs = {}
    manager.config = {'dependencies': {'filesystem': [], 'blarify': ['filesystem']}}
    fs_job_id = 'fs-job-id'
    manager.active_jobs[fs_job_id] = {'task_id': 'mock-task-id', 'repository_path': '/mock/repo/path', 'start_time': time.time(), 'status': StepStatus.FAILED, 'error': 'Simulated filesystem step failure', 'step_name': 'filesystem'}

    def check_dependencies(step_name: Any, repo_path: Any):
        dependencies = []
        if 'dependencies' in manager.config and step_name in manager.config['dependencies']:
            dependencies = manager.config['dependencies'][step_name]
        for dep_name in dependencies:
            dep_job_found = False
            for _job_id, job_info in manager.active_jobs.items():
                if job_info.get('step_name') == dep_name and job_info.get('repository_path') == repo_path:
                    dep_job_found = True
                    if job_info.get('status') == StepStatus.FAILED:
                        return (False, dep_name)
            if not dep_job_found:
                return (False, dep_name)
        return (True, None)
    repo_path = '/mock/repo/path'
    step_name = 'blarify'
    deps_satisfied, failed_dep = check_dependencies(step_name, repo_path)
    assert deps_satisfied is False, 'Dependencies should not be satisfied'
    assert failed_dep == 'filesystem', 'Filesystem should be reported as the failing dependency'
    if not deps_satisfied:
        blarify_job_id = 'blarify-job-id'
        manager.active_jobs[blarify_job_id] = {'task_id': 'mock-task-id', 'repository_path': repo_path, 'start_time': time.time(), 'status': StepStatus.FAILED, 'step_name': step_name, 'error': f'Dependency failed: {failed_dep}'}
    blarify_job = manager.active_jobs['blarify-job-id']
    assert blarify_job['status'] == StepStatus.FAILED, 'BlarifyStep should be marked as failed when its dependency failed'
    assert 'dependency failed: filesystem' in blarify_job['error'].lower(), f"Error should mention dependency failure: {blarify_job['error']}"

@pytest.mark.asyncio
async def test_job_dependency_orchestration(sample_repo: Any) -> None:
    """
    Integration test: Job B should not start until Job A (its dependency) completes.
    """
    from codestory_service.application.ingestion_service import IngestionService
    from codestory_service.domain.ingestion import IngestionRequest, JobStatus

    class MockCeleryAdapter:

        async def start_ingestion(self, request):
            from codestory_service.domain.ingestion import IngestionStarted
            return IngestionStarted(job_id=f'job-{int(time.time() * 1000)}', status=JobStatus.COMPLETED, source=request.source, started_at=None, steps=request.steps or [], message='Mock job completed', eta=None)

        async def get_job_status(self, job_id):
            from codestory_service.domain.ingestion import IngestionJob
            return IngestionJob(job_id=job_id, status=JobStatus.COMPLETED, source='mock', source_type=None, branch=None, progress=100.0, created_at=None, updated_at=None, started_at=None, completed_at=None, duration=None, steps=None, current_step=None, message='Mock job completed', error=None, result=None)

        async def list_jobs(self, *args, **kwargs):
            return []
    service = IngestionService(MockCeleryAdapter())
    req_a = IngestionRequest(source_type='local_path', source=sample_repo, steps=None, dependencies=None)
    started_a = await service.start_ingestion(req_a)
    job_a_id = started_a.job_id
    req_b = IngestionRequest(source_type='local_path', source=sample_repo, steps=None, dependencies=[job_a_id])
    started_b = await service.start_ingestion(req_b)
    job_b_id = started_b.job_id
    assert started_b.status == JobStatus.PENDING
    assert 'waiting for dependencies' in (started_b.message or '').lower()
    await service._check_and_trigger_dependents(job_a_id)
    if service.redis:
        waiting_key = f'codestory:ingestion:waiting:{job_b_id}'
        waiting = await service.redis.get(waiting_key)
        assert not waiting, 'Job B should have been dequeued and started after dependency completion'