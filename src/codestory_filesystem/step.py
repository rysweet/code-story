"""Filesystem workflow step for the ingestion pipeline.

This step scans the filesystem of the repository and creates a graph
of directories and files, which can be linked to AST nodes.
"""
import logging
import os
import pathlib
import time
import traceback
from typing import Any

import pathspec  # type: ignore[import-not-found]
from celery import shared_task

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus, generate_job_id

logger = logging.getLogger(__name__)
DEBUG_ENABLED = True
BUILTIN_IGNORE_PATTERNS = ['.git/', '__pycache__/', '*.pyc', '*.pyo', '*.log', '*.tmp', 'node_modules/', 'build/', 'dist/', '.venv/', '.idea/', '.vscode/']

def get_combined_ignore_spec(repository_path: str, extra_patterns: list[str] | None=None) -> pathspec.PathSpec:
    """Returns a PathSpec combining built-in ignore patterns, .gitignore (if present), and any extra patterns.
    
    Built-in patterns are always first, then .gitignore, then extra_patterns.
    """
    repo_root = pathlib.Path(repository_path)
    gitignore_path = repo_root / '.gitignore'
    pathspec_patterns = list(BUILTIN_IGNORE_PATTERNS)
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            gitignore_patterns = [line.strip() for line in f if line.strip() and (not line.startswith('#'))]
            pathspec_patterns.extend(gitignore_patterns)
    if extra_patterns:
        pathspec_patterns.extend(extra_patterns)
    if '.git/' not in pathspec_patterns:
        pathspec_patterns.append('.git/')
    return pathspec.PathSpec.from_lines('gitwildmatch', pathspec_patterns)

def log_debug(message: str, job_id: str | None=None) -> None:
    """Log a debug message with consistent formatting.

    Args:
        message: The message to log
        job_id: Optional job ID for context
    """
    if DEBUG_ENABLED:
        job_context = f'[job_id={job_id}] ' if job_id else ''
        formatted_message = f'FILESYSTEM_STEP: {job_context}{message}'
        logger.debug(formatted_message)
        print(formatted_message)

def log_info(message: str, job_id: str | None=None) -> None:
    """Log an info message with consistent formatting.

    Args:
        message: The message to log
        job_id: Optional job ID for context
    """
    job_context = f'[job_id={job_id}] ' if job_id else ''
    formatted_message = f'FILESYSTEM_STEP: {job_context}{message}'
    logger.info(formatted_message)
    if DEBUG_ENABLED:
        print(formatted_message)

def log_error(message: str, error: Exception | None=None, job_id: str | None=None) -> None:
    """Log an error message with consistent formatting and optional exception details.

    Args:
        message: The error message
        error: Optional exception that caused the error
        job_id: Optional job ID for context
    """
    job_context = f'[job_id={job_id}] ' if job_id else ''
    formatted_message = f'FILESYSTEM_STEP ERROR: {job_context}{message}'
    if error:
        formatted_message += f': {error!s}'
        logger.error(formatted_message, exc_info=error)
    else:
        logger.error(formatted_message)
    print(formatted_message)
    if error and DEBUG_ENABLED:
        stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        print(f'FILESYSTEM_STEP STACK TRACE: {job_context}\n{stack_trace}')

def log_progress(progress: dict[str, Any], job_id: str | None=None) -> None:
    """Log progress information with consistent formatting.

    Args:
        progress: Dictionary containing progress information
        job_id: Optional job ID for context
    """
    job_context = f'[job_id={job_id}] ' if job_id else ''
    formatted_message = f'FILESYSTEM_STEP PROGRESS: {job_context}{progress}'
    logger.info(formatted_message)
    if DEBUG_ENABLED:
        print(formatted_message)

class FileSystemStep(PipelineStep):
    """Pipeline step that processes the filesystem structure of a repository.

    This step scans the filesystem of the repository and creates a graph
    of directories and files in Neo4j, which can be linked to AST nodes.
    """

    def __init__(self: Any) -> None:
        """Initialize the filesystem step."""
        self.settings = get_settings()
        self.active_jobs: dict[str, dict[str, Any]] = {}

    def run(self: Any, repository_path: str, **config: Any) -> str:
        """Run the filesystem step.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters
                - ignore_patterns: list of glob patterns to ignore
                - max_depth: Maximum directory depth to traverse
                - include_extensions: list of file extensions to include
                - job_id: Optional job ID to use (will be generated if not provided)

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If the repository path is invalid
        """
        job_id = config.pop('job_id', None) or generate_job_id()
        log_info(f'Starting filesystem step with repository path: {repository_path}', job_id)
        log_debug(f'Configuration parameters: {config}', job_id)
        if not repository_path:
            error_msg = 'Repository path is required'
            log_error(error_msg, job_id=job_id)
            raise ValueError(error_msg)
        if not os.path.exists(repository_path):
            error_msg = f'Repository path does not exist: {repository_path}'
            log_error(error_msg, job_id=job_id)
            raise ValueError(error_msg)
        if not os.path.isdir(repository_path):
            error_msg = f'Repository path is not a directory: {repository_path}'
            log_error(error_msg, job_id=job_id)
            raise ValueError(error_msg)
        try:
            from codestory.ingestion_pipeline.celery_app import app as celery_app
            active_queues = celery_app.control.inspect().active_queues()
            registered_tasks = celery_app.control.inspect().registered()
            log_debug(f'Celery active queues: {active_queues}', job_id)
            log_debug(f'Celery registered tasks: {registered_tasks}', job_id)
            kwargs = config.copy()
            kwargs['job_id'] = job_id
            log_debug(f'Submitting task with args=[{repository_path}], kwargs={kwargs}', job_id)
            from celery import current_app
            task = current_app.send_task('codestory_filesystem.step.process_filesystem', args=[repository_path], kwargs=kwargs, queue='ingestion')
            log_debug(f'Celery task submitted with ID: {task.id}', job_id)
            log_debug(f'Celery task initial status: {task.status}', job_id)
            from celery.result import AsyncResult
            result = AsyncResult(task.id, app=celery_app)
            log_debug(f'Celery AsyncResult state: {result.state}', job_id)
            log_debug(f'Celery AsyncResult info: {result.info}', job_id)
            self.active_jobs[job_id] = {'task_id': task.id, 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
            log_info(f'Successfully initiated filesystem step job {job_id} for repository {repository_path}', job_id)
            return job_id
        except Exception as e:
            error_msg = 'Failed to initiate filesystem step'
            log_error(error_msg, error=e, job_id=job_id)
            raise

    def status(self: Any, job_id: str) -> dict[str, Any]:
        """Check the status of a job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        log_debug(f'Checking status for job_id={job_id}', job_id)
        if job_id not in self.active_jobs:
            error_msg = f'Job ID not found: {job_id}'
            log_error(error_msg, job_id=job_id)
            raise ValueError(error_msg)
        job_info = self.active_jobs[job_id]
        task_id = job_info['task_id']
        log_debug(f'Found job info with task_id={task_id}', job_id)
        try:
            from celery.result import AsyncResult

            from codestory.ingestion_pipeline.celery_app import app
            result = AsyncResult(task_id, app=app)
            log_debug(f'Celery AsyncResult status: {result.status}, ready: {result.ready()}', job_id)
            if isinstance(result.info, dict):
                log_debug(f'Celery AsyncResult info: {result.info}', job_id)
            status_info: dict[str, Any] = {'status': StepStatus.RUNNING, 'progress': None, 'message': None, 'error': None}
            if result.ready():
                log_debug(f'Task is ready. Successful: {result.successful()}', job_id)
                if result.successful():
                    try:
                        task_result = result.result
                        log_debug(f'Task completed with result: {task_result}', job_id)
                        file_count = task_result.get('file_count', 0)
                        dir_count = task_result.get('dir_count', 0)
                        duration = task_result.get('duration', 0)
                        status_msg = f'Processed {file_count} files and {dir_count} directories in {duration:.2f} seconds'
                        log_info(status_msg, job_id)
                        status_info.update({'status': StepStatus.COMPLETED, 'message': status_msg, 'progress': 100.0, 'result': task_result})
                    except Exception as e:
                        error_msg = 'Error retrieving task result'
                        log_error(error_msg, error=e, job_id=job_id)
                        status_info.update({'status': StepStatus.FAILED, 'error': f'Error retrieving result: {e!s}'})
                else:
                    error_msg = f'Task failed with result: {result.result}'
                    log_error(error_msg, job_id=job_id)
                    status_info.update({'status': StepStatus.FAILED, 'error': str(result.result)})
            else:
                log_debug(f'Task still running. State: {result.state}', job_id)
                if isinstance(result.info, dict):
                    progress_info = result.info
                    log_progress(progress_info, job_id)
                    status_info.update({'progress': progress_info.get('progress'), 'message': progress_info.get('message')})
                    if progress_info.get('progress') is not None:
                        log_info(f"Progress: {progress_info.get('progress'):.1f}%", job_id)
            job_info.update(status_info)
            log_debug(f"Updated job info with status: {status_info['status']}", job_id)
            return job_info  # type: ignore[no-any-return]
        except Exception as e:
            error_msg = 'Error checking job status'
            log_error(error_msg, error=e, job_id=job_id)
            job_info.update({'status': StepStatus.FAILED, 'error': f'Status check failed: {e!s}'})
            return job_info  # type: ignore[no-any-return]

    def stop(self: Any, job_id: str) -> dict[str, Any]:
        """Stop a running job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        log_info(f'Attempting to stop job {job_id}', job_id)
        if job_id not in self.active_jobs:
            error_msg = f'Job ID not found: {job_id}'
            log_error(error_msg, job_id=job_id)
            raise ValueError(error_msg)
        job_info = self.active_jobs[job_id]
        task_id = job_info['task_id']
        log_debug(f'Found job with task_id={task_id}', job_id)
        try:
            from codestory.ingestion_pipeline.celery_app import app
            log_debug(f'Revoking Celery task {task_id}', job_id)
            app.control.revoke(task_id, terminate=True)
            job_info.update({'status': StepStatus.STOPPED, 'message': f'Job {job_id} has been stopped'})
            log_info(f'Successfully stopped job {job_id}', job_id)
            return job_info  # type: ignore[no-any-return]
        except Exception as e:
            error_msg = f'Error stopping job {job_id}'
            log_error(error_msg, error=e, job_id=job_id)
            job_info.update({'status': StepStatus.STOPPED, 'message': f'Job {job_id} marked as stopped, but encountered error: {e!s}', 'error': str(e)})
            return job_info  # type: ignore[no-any-return]

    def cancel(self: Any, job_id: str) -> dict[str, Any]:
        """Cancel a job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        log_info(f'Attempting to cancel job {job_id}', job_id)
        try:
            result = self.stop(job_id)
            result['status'] = StepStatus.CANCELLED
            result['message'] = f'Job {job_id} has been cancelled'
            log_info(f'Successfully cancelled job {job_id}', job_id)
            return result  # type: ignore[no-any-return]
        except Exception as e:
            if job_id in self.active_jobs:
                job_info = self.active_jobs[job_id]
                job_info.update({'status': StepStatus.CANCELLED, 'message': f'Job {job_id} marked as cancelled, but encountered error: {e!s}', 'error': str(e)})
                log_error(f'Marked job {job_id} as cancelled with errors', error=e, job_id=job_id)
                return job_info  # type: ignore[no-any-return]
            else:
                log_error(f'Failed to cancel job {job_id}', error=e, job_id=job_id)
                raise

    def ingestion_update(self: Any, repository_path: str, **config: Any) -> str:
        """Update the graph with the results of this step only.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters

        Returns:
            str: Job ID that can be used to check the status
        """
        log_info(f'Initiating incremental update for repository: {repository_path}')
        job_id = self.run(repository_path, **config)
        log_info(f'Incremental update initiated with job ID: {job_id}')
        return job_id  # type: ignore[no-any-return]

@shared_task(name='codestory_filesystem.step.process_filesystem', bind=True, queue='ingestion')  # type: ignore[misc]
def process_filesystem(self: Any, repository_path: str, ignore_patterns: list[str] | None=None, max_depth: int | None=None, include_extensions: list[str] | None=None, job_id: str | None=None, **config: Any) -> dict[str, Any]:
    """Process the filesystem of a repository.

    Args:
        self: The Celery task instance
        repository_path: Path to the repository to process
        ignore_patterns: list of glob patterns to ignore
        max_depth: Maximum directory depth to traverse
        include_extensions: list of file extensions to include
        job_id: Identifier for the job
        **config: Additional configuration parameters

    Returns:
        dict[str, Any]: Result information
    """
    start_time = time.time()
    if job_id is None:
        job_id = f'task-{self.request.id}' if hasattr(self, 'request') else f'task-{time.time()}'
    task_id = self.request.id if hasattr(self, 'request') else 'Unknown'
    log_info(f'Starting filesystem processing task for repository: {repository_path}', job_id)
    log_debug(f'Task ID: {task_id}', job_id)
    log_debug(f'Configuration: ignore_patterns={ignore_patterns}, max_depth={max_depth}, include_extensions={include_extensions}', job_id)
    if not repository_path:
        error_msg = 'Repository path is required'
        log_error(error_msg, job_id=job_id)
        raise ValueError(error_msg)
    if not os.path.exists(repository_path):
        error_msg = f'Repository path does not exist: {repository_path}'
        log_error(error_msg, job_id=job_id)
        self.update_state(state='FAILURE', meta={'error': error_msg})
        raise ValueError(error_msg)
    if not os.path.isdir(repository_path):
        error_msg = f'Repository path is not a directory: {repository_path}'
        log_error(error_msg, job_id=job_id)
        self.update_state(state='FAILURE', meta={'error': error_msg})
        raise ValueError(error_msg)
    log_debug(f'Repository exists: {os.path.exists(repository_path)}', job_id)
    log_debug(f'Repository is directory: {os.path.isdir(repository_path)}', job_id)
    try:
        repo_contents = os.listdir(repository_path)[:10]
        log_debug(f'Repository sample contents (first 10): {repo_contents}', job_id)
    except Exception as e:
        log_error('Error listing repository contents', error=e, job_id=job_id)
    repo_root = pathlib.Path(repository_path)
    gitignore_path = repo_root / '.gitignore'
    pathspec_patterns = list(BUILTIN_IGNORE_PATTERNS)
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            gitignore_patterns = [line.strip() for line in f if line.strip() and (not line.startswith('#'))]
            pathspec_patterns.extend(gitignore_patterns)
    if ignore_patterns:
        pathspec_patterns.extend(ignore_patterns)
    if '.git/' not in pathspec_patterns:
        pathspec_patterns.append('.git/')
    spec = pathspec.PathSpec.from_lines('gitwildmatch', pathspec_patterns)
    log_info(f'Using pathspec ignore patterns: {pathspec_patterns}', job_id)
    neo4j = None
    errors: list[Any] = []
    settings = get_settings()
    log_info('Attempting to connect to Neo4j database', job_id)
    log_debug(f'Neo4j settings from config: uri={settings.neo4j.uri}, database={settings.neo4j.database}', job_id)
    connection_params: list[dict[str, str]] = [
        {'uri': settings.neo4j.uri, 'username': settings.neo4j.username, 'password': settings.neo4j.password.get_secret_value() if settings.neo4j.password is not None else "", 'database': settings.neo4j.database},
        {'uri': 'bolt://neo4j:7687', 'username': 'neo4j', 'password': 'password', 'database': 'neo4j'},
        {'uri': 'bolt://localhost:7689', 'username': 'neo4j', 'password': 'password', 'database': 'neo4j'},
        {'uri': 'bolt://localhost:7688', 'username': 'neo4j', 'password': 'password', 'database': 'testdb'}
    ]
    for i, params in enumerate(connection_params):
        connection_uri = params['uri']
        try:
            log_debug(f'Trying Neo4j connection #{i + 1}/{len(connection_params)}: {connection_uri}', job_id)
            neo4j = Neo4jConnector(**params)  # type: ignore[arg-type]
            log_debug('Testing Neo4j connection with simple query', job_id)
            test_result = neo4j.execute_query('MATCH (n) RETURN count(n) as count LIMIT 1')
            log_info(f'Neo4j connection successful to {connection_uri}', job_id)
            log_debug(f'Connection test result: {test_result}', job_id)
            break
        except Exception as e:
            log_error(f'Neo4j connection #{i + 1} to {connection_uri} failed', error=e, job_id=job_id)
            errors.append(f'Connection {i + 1} ({connection_uri}): {e}')
            if neo4j:
                try:
                    neo4j.close()
                except Exception as close_error:
                    log_debug(f'Error closing failed Neo4j connection: {close_error}', job_id)
            neo4j = None
    if not neo4j:
        error_details = '\n'.join(errors)
        error_msg = 'All Neo4j connection attempts failed. Cannot proceed without database connection.'
        log_error(error_msg, job_id=job_id)
        log_debug(f'Detailed connection errors:\n{error_details}', job_id)
        self.update_state(state='FAILURE', meta={'error': error_msg, 'job_id': job_id, 'details': error_details})
        return {'status': StepStatus.FAILED, 'error': f'Neo4j connection error: No working connection found.\n{error_details}', 'job_id': job_id}
    try:
        file_count = 0
        dir_count = 0
        log_info(f'Starting repository traversal with max_depth: {max_depth} (unlimited if None)', job_id)
        debug_log_path = '/tmp/neo4j_debug.log'
        log_debug(f'Writing debug information to {debug_log_path}', job_id)
        with open(debug_log_path, 'w') as f:
            f.write(f'Repository path: {repository_path}\n')
            f.write(f'Neo4j URI: {settings.neo4j.uri}\n')
            f.write(f'Neo4j database: {settings.neo4j.database}\n')
            f.write(f'Max depth: {max_depth}\n')
            f.write(f'Job ID: {job_id}\n')
            f.write(f'Ignore patterns: {ignore_patterns}\n')
            f.write(f'Include extensions: {include_extensions}\n\n')
            try:
                test_query = 'MATCH (n) RETURN count(n) as count'
                test_result = neo4j.execute_query(test_query)
                f.write(f'Neo4j connection test result: {test_result}\n')
            except Exception as e:
                f.write(f'Neo4j test query failed: {e!s}\n')
        repo_name = os.path.basename(repository_path)
        repo_properties = {'name': repo_name, 'path': repository_path}
        log_info(f'Creating or updating repository node: {repo_name}', job_id)
        repo_query = '\n        MERGE (r:Repository {path: $props.path})\n        SET r.name = $props.name\n        RETURN r\n        '
        try:
            repo_result = neo4j.execute_query(repo_query, params={'props': repo_properties}, write=True)
            repo_node = repo_result[0]['r'] if repo_result else None
            log_debug(f'Repository node created or updated: {repo_node}', job_id)
            if not repo_node:
                log_error('Failed to create repository node - query returned no results', job_id=job_id)
        except Exception as e:
            log_error('Error creating repository node', error=e, job_id=job_id)
            raise
        log_info(f'Starting filesystem traversal for repository: {repository_path}', job_id)
        log_debug(f'Repository validation: exists={os.path.exists(repository_path)}, is_dir={os.path.isdir(repository_path)}', job_id)
        try:
            contents = os.listdir(repository_path)
            log_debug(f'Top-level repository contents: {contents[:10]}...', job_id)
        except Exception as e:
            log_error('Error listing repository contents', error=e, job_id=job_id)
        dir_timing_stats = {'dir_node_creation': 0.0, 'dir_linking': 0.0, 'dir_total': 0.0}
        log_info(f'Starting directory traversal. Ignore patterns: {ignore_patterns}', job_id)
        total_dirs_estimate = sum((len(dirs) for _, dirs, _ in os.walk(repository_path, topdown=True)))
        log_info(f'Estimated total directories: {total_dirs_estimate}', job_id)
        for current_dir, dirs, files in os.walk(repository_path):
            dir_start_time = time.time()
            rel_path = os.path.relpath(current_dir, repository_path)
            rel_path_posix = pathlib.Path(rel_path).as_posix() if rel_path != '.' else ''
            dirs_to_remove = []
            for d in list(dirs):
                dir_rel = os.path.normpath(os.path.join(rel_path_posix, d)).replace('\\', '/')
                if spec.match_file(dir_rel + '/'):
                    log_debug(f'Ignoring directory {dir_rel} (matched .gitignore/pathspec)', job_id)
                    dirs_to_remove.append(d)
            for d in dirs_to_remove:
                dirs.remove(d)
            if dirs_to_remove:
                log_info(f'Filtered {len(dirs_to_remove)} directories in {rel_path} due to .gitignore/pathspec', job_id)
            rel_dir_path = os.path.relpath(current_dir, repository_path)
            if rel_dir_path == '.':
                dir_node = repo_node
                log_info('Using repository node as root directory node', job_id)
            else:
                log_info(f'Creating directory node: {rel_dir_path}', job_id)
                try:
                    dir_node_start = time.time()
                    dir_properties = {'name': os.path.basename(current_dir), 'path': rel_dir_path}
                    dir_query = '\n                    MERGE (d:Directory {path: $props.path})\n                    SET d.name = $props.name\n                    RETURN d\n                    '
                    dir_result = neo4j.execute_query(dir_query, params={'props': dir_properties}, write=True)
                    dir_node = dir_result[0]['d'] if dir_result else None
                    dir_node_end = time.time()
                    dir_node_time = dir_node_end - dir_node_start
                    dir_timing_stats['dir_node_creation'] += dir_node_time
                    if not dir_node:
                        log_error(f'Failed to create directory node for {rel_dir_path}', job_id=job_id)
                    else:
                        log_debug(f'Directory node created in {dir_node_time:.3f}s: {rel_dir_path}', job_id)
                    dir_linking_start = time.time()
                    parent_path = os.path.dirname(rel_dir_path)
                    if parent_path == '':
                        log_debug(f'Linking directory {rel_dir_path} to repository', job_id)
                        rel_query = '\n                        MATCH (r:Repository {path: $repo_path})\n                        MATCH (d:Directory {path: $dir_path})\n                        MERGE (r)-[rel:CONTAINS]->(d)\n                        RETURN rel\n                        '
                        neo4j.execute_query(rel_query, params={'repo_path': repository_path, 'dir_path': rel_dir_path}, write=True)
                    else:
                        log_debug(f'Linking directory {rel_dir_path} to parent directory {parent_path}', job_id)
                        rel_query = '\n                        MATCH (p:Directory {path: $parent_path})\n                        MATCH (d:Directory {path: $dir_path})\n                        MERGE (p)-[rel:CONTAINS]->(d)\n                        RETURN rel\n                        '
                        neo4j.execute_query(rel_query, params={'parent_path': parent_path, 'dir_path': rel_dir_path}, write=True)
                    dir_linking_end = time.time()
                    dir_linking_time = dir_linking_end - dir_linking_start
                    dir_timing_stats['dir_linking'] += dir_linking_time
                    log_debug(f'Directory relationship created in {dir_linking_time:.3f}s: {rel_dir_path}', job_id)
                    dir_count += 1
                    if total_dirs_estimate > 0:
                        progress_percent = min(100, dir_count / total_dirs_estimate * 100)
                    else:
                        progress_percent = 0
                    if dir_count > 0:
                        avg_dir_node_time = dir_timing_stats['dir_node_creation'] / dir_count
                        avg_dir_linking_time = dir_timing_stats['dir_linking'] / dir_count
                    else:
                        avg_dir_node_time = 0
                        avg_dir_linking_time = 0
                    dir_progress_msg = f'Created directory {dir_count}/{total_dirs_estimate} ({progress_percent:.1f}%): {rel_dir_path} Avg times - node: {avg_dir_node_time:.3f}s, linking: {avg_dir_linking_time:.3f}s'
                    log_info(dir_progress_msg, job_id)
                    try:
                        self.update_state(state='PROGRESS', meta={'progress': progress_percent, 'message': dir_progress_msg, 'directory': rel_dir_path, 'dir_count': dir_count, 'total_dirs_estimate': total_dirs_estimate, 'timing': {'avg_dir_creation': avg_dir_node_time, 'avg_dir_linking': avg_dir_linking_time}})
                    except Exception as e:
                        log_error('Error updating directory progress state', error=e, job_id=job_id)
                except Exception as e:
                    log_error(f'Error creating directory node for {rel_dir_path}', error=e, job_id=job_id)
                    raise
            dir_processing_end = time.time()
            dir_timing_stats['dir_total'] += dir_processing_end - dir_start_time
            start_dir_time = time.time()
            log_info(f'Processing {len(files)} files in directory {rel_dir_path}', job_id)
            files_processed = 0
            files_skipped = 0
            file_timing_stats = {'file_metadata': 0.0, 'file_node_creation': 0.0, 'linking': 0.0, 'total': 0.0}
            for file_idx, file in enumerate(files):
                start_file_time = time.time()
                file_rel = os.path.normpath(os.path.join(rel_path_posix, file)).replace('\\', '/')
                if spec.match_file(file_rel):
                    files_skipped += 1
                    continue
                if include_extensions and (not any(file.endswith(ext) for ext in include_extensions)):
                    files_skipped += 1
                    continue
                file_path = os.path.join(rel_dir_path, file)
                if rel_dir_path == '.':
                    file_path = file
                log_debug(f'[{file_idx + 1}/{len(files)}] Processing file: {file_path}', job_id)
                try:
                    metadata_start = time.time()
                    abs_file_path = os.path.join(current_dir, file)
                    file_size = os.path.getsize(abs_file_path)
                    file_modified = os.path.getmtime(abs_file_path)
                    file_extension = os.path.splitext(file)[1].lstrip('.') or None
                    metadata_end = time.time()
                    file_timing_stats['file_metadata'] += metadata_end - metadata_start
                    node_start = time.time()
                    file_properties = {'name': file, 'path': file_path, 'extension': file_extension, 'size': file_size, 'modified': file_modified}
                    file_query = '\n                    MERGE (f:File {path: $props.path})\n                    SET f.name = $props.name,\n                        f.extension = $props.extension,\n                        f.size = $props.size,\n                        f.modified = $props.modified\n                    RETURN f\n                    '
                    file_result = neo4j.execute_query(file_query, params={'props': file_properties}, write=True)
                    file_node = file_result[0]['f'] if file_result else None
                    node_end = time.time()
                    node_time = node_end - node_start
                    file_timing_stats['file_node_creation'] += node_time
                    if not file_node:
                        log_error(f'Failed to create file node for {file_path}', job_id=job_id)
                    else:
                        log_debug(f'File node created in {node_time:.3f}s: {file_path}', job_id)
                    linking_start = time.time()
                    if rel_dir_path == '.':
                        log_debug(f'Linking file {file_path} to repository', job_id)
                        rel_query = '\n                        MATCH (r:Repository {path: $repo_path})\n                        MATCH (f:File {path: $file_path})\n                        MERGE (r)-[rel:CONTAINS]->(f)\n                        RETURN rel\n                        '
                        neo4j.execute_query(rel_query, params={'repo_path': repository_path, 'file_path': file_path}, write=True)
                    else:
                        log_debug(f'Linking file {file_path} to directory {rel_dir_path}', job_id)
                        rel_query = '\n                        MATCH (d:Directory {path: $dir_path})\n                        MATCH (f:File {path: $file_path})\n                        MERGE (d)-[rel:CONTAINS]->(f)\n                        RETURN rel\n                        '
                        neo4j.execute_query(rel_query, params={'dir_path': rel_dir_path, 'file_path': file_path}, write=True)
                    linking_end = time.time()
                    linking_time = linking_end - linking_start
                    file_timing_stats['linking'] += linking_time
                    log_debug(f'File relationship created in {linking_time:.3f}s: {file_path}', job_id)
                    file_count += 1
                    files_processed += 1
                    file_end_time = time.time()
                    file_total_time = file_end_time - start_file_time
                    file_timing_stats['total'] += file_total_time
                    if files_processed > 0:
                        avg_time_per_file = file_timing_stats['total'] / files_processed
                        avg_node_time = file_timing_stats['file_node_creation'] / files_processed
                        avg_linking_time = file_timing_stats['linking'] / files_processed
                    else:
                        avg_time_per_file = 0
                        avg_node_time = 0
                        avg_linking_time = 0
                    if file_count % 10 == 0:
                        progress_msg = f'Processed {file_count}/{file_count + files_skipped} files, {dir_count} directories. Avg time per file: {avg_time_per_file:.3f}s (node: {avg_node_time:.3f}s, linking: {avg_linking_time:.3f}s)'
                        log_info(progress_msg, job_id)
                        try:
                            self.update_state(state='PROGRESS', meta={'progress': None, 'message': progress_msg, 'file_count': file_count, 'dir_count': dir_count, 'timing': {'avg_per_file': avg_time_per_file, 'avg_node_creation': avg_node_time, 'avg_linking': avg_linking_time}})
                        except Exception as e:
                            log_error('Error updating progress state', error=e, job_id=job_id)
                except Exception as e:
                    log_error(f'Error creating file node for {file_path}', error=e, job_id=job_id)
                    continue
            dir_end_time = time.time()
            dir_total_time = dir_end_time - start_dir_time
            dir_summary = f'Directory {rel_dir_path} completed in {dir_total_time:.2f}s: {files_processed} files processed, {files_skipped} files skipped'
            log_info(dir_summary, job_id)
            if files_processed > 0 or files_skipped > 0:
                log_debug(f'Directory {rel_dir_path} processed: {files_processed} files created, {files_skipped} files skipped', job_id)
        end_time = time.time()
        duration = end_time - start_time
        overall_timing_stats = {'total_duration': duration, 'directory_operations': {'total': dir_timing_stats.get('dir_total', 0), 'node_creation': dir_timing_stats.get('dir_node_creation', 0), 'linking': dir_timing_stats.get('dir_linking', 0), 'avg_per_directory': dir_timing_stats.get('dir_total', 0) / max(1, dir_count) if dir_count else 0}, 'file_operations': {'total': file_timing_stats.get('total', 0) if 'file_timing_stats' in locals() else 0, 'metadata': file_timing_stats.get('file_metadata', 0) if 'file_timing_stats' in locals() else 0, 'node_creation': file_timing_stats.get('file_node_creation', 0) if 'file_timing_stats' in locals() else 0, 'linking': file_timing_stats.get('linking', 0) if 'file_timing_stats' in locals() else 0, 'avg_per_file': file_timing_stats.get('total', 0) / max(1, file_count) if 'file_timing_stats' in locals() and file_count else 0}, 'neo4j_operations': {'node_creation': dir_timing_stats.get('dir_node_creation', 0) + (file_timing_stats.get('file_node_creation', 0) if 'file_timing_stats' in locals() else 0), 'relationship_creation': dir_timing_stats.get('dir_linking', 0) + (file_timing_stats.get('linking', 0) if 'file_timing_stats' in locals() else 0), 'avg_operation_time': (dir_timing_stats.get('dir_node_creation', 0) + dir_timing_stats.get('dir_linking', 0) + (file_timing_stats.get('file_node_creation', 0) if 'file_timing_stats' in locals() else 0) + (file_timing_stats.get('linking', 0) if 'file_timing_stats' in locals() else 0)) / max(1, dir_count * 2 + file_count * 2)}}
        from typing import cast
        overall_timing_stats_dict = cast('dict[str, Any]', overall_timing_stats)
        detailed_timing = f"Detailed Timing Stats:\nTotal Duration: {duration:.2f}s\nDirectory Operations ({dir_count} dirs):\n  - Total: {overall_timing_stats_dict['directory_operations']['total']:.2f}s\n  - Node creation: {overall_timing_stats_dict['directory_operations']['node_creation']:.2f}s\n  - Linking: {overall_timing_stats_dict['directory_operations']['linking']:.2f}s\n  - Avg per directory: {overall_timing_stats_dict['directory_operations']['avg_per_directory']:.3f}s\nFile Operations ({file_count} files):\n  - Total: {overall_timing_stats_dict['file_operations']['total']:.2f}s\n  - Metadata: {overall_timing_stats_dict['file_operations']['metadata']:.2f}s\n  - Node creation: {overall_timing_stats_dict['file_operations']['node_creation']:.2f}s\n  - Linking: {overall_timing_stats_dict['file_operations']['linking']:.2f}s\n  - Avg per file: {overall_timing_stats_dict['file_operations']['avg_per_file']:.3f}s\nNeo4j Operations:\n  - Node creation total: {overall_timing_stats_dict['neo4j_operations']['node_creation']:.2f}s\n  - Relationship creation total: {overall_timing_stats_dict['neo4j_operations']['relationship_creation']:.2f}s\n  - Avg operation time: {overall_timing_stats_dict['neo4j_operations']['avg_operation_time']:.3f}s\n"
        log_info(f'Performance Analysis:\n{detailed_timing}', job_id)
        try:
            log_info('Creating processing record for completed job', job_id)
            record_query = '\n            MERGE (p:ProcessingRecord {step: $props.step, job_id: $props.job_id})\n            SET p.repository = $props.repository,\n                p.timestamp = $props.timestamp,\n                p.duration = $props.duration,\n                p.file_count = $props.file_count,\n                p.dir_count = $props.dir_count,\n                p.performance = $props.performance\n            RETURN p\n            '
            # Explicitly cast overall_timing_stats to dict for mypy
            from typing import cast
            overall_timing_stats_dict = cast('dict[str, Any]', overall_timing_stats)
            record_props = {'step': 'filesystem', 'job_id': job_id, 'repository': repo_name, 'timestamp': time.time(), 'duration': duration, 'file_count': file_count, 'dir_count': dir_count, 'performance': {'avg_file_time': overall_timing_stats_dict['file_operations']['avg_per_file'], 'avg_dir_time': overall_timing_stats_dict['directory_operations']['avg_per_directory'], 'avg_neo4j_op_time': overall_timing_stats_dict['neo4j_operations']['avg_operation_time']}}
            neo4j.execute_query(record_query, params={'props': record_props}, write=True)
            log_debug('Successfully created processing record with performance data', job_id)
        except Exception as e:
            log_error('Error creating processing record', error=e, job_id=job_id)
        completion_msg = f"Completed filesystem processing for {repository_path}:\n- {file_count} files, {dir_count} directories in {duration:.2f} seconds\n- Average Neo4j operation time: {overall_timing_stats_dict['neo4j_operations']['avg_operation_time']:.3f}s\n- Average file processing time: {overall_timing_stats_dict['file_operations']['avg_per_file']:.3f}s\n- Average directory processing time: {overall_timing_stats_dict['directory_operations']['avg_per_directory']:.3f}s"
        log_info(completion_msg, job_id)
        try:
            self.update_state(state='SUCCESS', meta={'status': StepStatus.COMPLETED, 'job_id': job_id, 'duration': duration, 'file_count': file_count, 'dir_count': dir_count, 'message': completion_msg, 'timing_stats': overall_timing_stats_dict})
        except Exception as e:
            log_error('Error updating final task state', error=e, job_id=job_id)
        return {'status': StepStatus.COMPLETED, 'job_id': job_id, 'duration': duration, 'file_count': file_count, 'dir_count': dir_count, 'message': completion_msg, 'timing_stats': overall_timing_stats_dict}
    except Exception as e:
        error_msg = f'Error processing filesystem for repository {repository_path}'
        log_error(error_msg, error=e, job_id=job_id)
        try:
            self.update_state(state='FAILURE', meta={'status': StepStatus.FAILED, 'error': str(e), 'job_id': job_id})
        except Exception as state_error:
            log_error('Error updating failure state', error=state_error, job_id=job_id)
        return {'status': StepStatus.FAILED, 'error': str(e), 'job_id': job_id, 'traceback': traceback.format_exc()}
    finally:
        if neo4j:
            try:
                log_debug('Closing Neo4j connection', job_id)
                neo4j.close()
            except Exception as close_error:
                log_error('Error closing Neo4j connection', error=close_error, job_id=job_id)