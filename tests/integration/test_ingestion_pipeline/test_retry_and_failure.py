from typing import Any
'Integration test for retry and failure recovery in the ingestion pipeline.\n\nThis test simulates a transient failure in a pipeline step, verifies that the step is retried\naccording to the configured max_retries and back_off_seconds, and checks that the job status\nAPI reports the correct retry_count and last_error.\n'
import time
from unittest.mock import patch
import pytest
from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import StepStatus
pytestmark = [pytest.mark.integration]

def test_retry_and_failure_reporting(tmp_path: Any) -> None:
    """Test that a step is retried on transient error and retry info is reported."""

    class TransientError(Exception):
        pass
    retry_attempts = {'count': 0}

    def flaky_run(self, repository_path: Any, **kwargs):
        if retry_attempts['count'] < 2:
            retry_attempts['count'] += 1
            raise TransientError('Simulated transient error')
        return 'flaky-job-id'

    def flaky_status(self, job_id: Any) -> None:
        if retry_attempts['count'] < 2:
            return {'status': StepStatus.FAILED, 'progress': 0, 'error': 'Simulated transient error', 'retry_count': retry_attempts['count'], 'last_error': 'Simulated transient error'}
        else:
            return {'status': StepStatus.COMPLETED, 'progress': 100, 'retry_count': retry_attempts['count'], 'last_error': None}
    from codestory_filesystem.step import FileSystemStep
    with patch.object(FileSystemStep, 'run', flaky_run), patch.object(FileSystemStep, 'status', flaky_status):
        manager = PipelineManager()
        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()
        (repo_dir / 'README.md').write_text('# Test repo')
        manager.config['steps'] = [{'name': 'filesystem', 'max_retries': 2, 'back_off_seconds': 1}]
        job_id = manager.start_job(str(repo_dir))
        time.sleep(4)
        status = manager.status(job_id)
        steps = status.get('steps', {})
        fs_step = steps.get('filesystem')
        assert fs_step is not None, 'Step status should be present'
        assert fs_step['retry_count'] == 2, 'Retry count should match number of retries'
        assert fs_step['status'] == StepStatus.COMPLETED, 'Step should eventually complete'
        assert fs_step['last_error'] is None, 'Last error should be cleared on success'

def test_retry_exceeds_max(tmp_path: Any) -> None:
    """Test that a step fails after exceeding max_retries and last_error is reported."""

    class TransientError(Exception):
        pass
    retry_attempts = {'count': 0}

    def always_fail_run(self, repository_path: Any, **kwargs) -> None:
        retry_attempts['count'] += 1
        raise TransientError('Simulated persistent error')

    def always_fail_status(self, job_id: Any):
        return {'status': StepStatus.FAILED, 'progress': 0, 'error': 'Simulated persistent error', 'retry_count': retry_attempts['count'], 'last_error': 'Simulated persistent error'}
    from codestory_filesystem.step import FileSystemStep
    with patch.object(FileSystemStep, 'run', always_fail_run), patch.object(FileSystemStep, 'status', always_fail_status):
        manager = PipelineManager()
        repo_dir = tmp_path / 'repo'
        repo_dir.mkdir()
        (repo_dir / 'README.md').write_text('# Test repo')
        manager.config['steps'] = [{'name': 'filesystem', 'max_retries': 2, 'back_off_seconds': 1}]
        job_id = manager.start_job(str(repo_dir))
        time.sleep(4)
        status = manager.status(job_id)
        steps = status.get('steps', {})
        fs_step = steps.get('filesystem')
        assert fs_step is not None, 'Step status should be present'
        assert fs_step['retry_count'] == 3, 'Retry count should be max_retries + 1 (final failure)'
        assert fs_step['status'] == StepStatus.FAILED, 'Step should fail after max retries'
        assert fs_step['last_error'] == 'Simulated persistent error', 'Last error should be reported'