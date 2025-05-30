"""Summarizer workflow step implementation.

This module implements the SummarizerStep class, which generates natural language
summaries for code elements using a language model and stores them in Neo4j.
"""
import asyncio
import json
import logging
import os
import time
from typing import Any
from uuid import uuid4
from celery import shared_task
from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus
from codestory.llm.client import create_client
from codestory.llm.models import ChatMessage, ChatRole
from .dependency_analyzer import DependencyAnalyzer
from .models import NodeData, SummaryData
from .parallel_executor import ParallelExecutor
from .prompts import get_summary_prompt
from .utils import ContentExtractor, ProgressTracker
logger = logging.getLogger(__name__)

class SummarizerStep(PipelineStep):
    """Workflow step that generates summaries for code elements.

    This step analyzes the code in a repository, generates natural language
    summaries using a language model, and stores them in the Neo4j database.
    """

    def __init__(self: Any) -> None:
        """Initialize the summarizer step."""
        self.settings = get_settings()
        self.active_jobs: dict[str, dict[str, Any]] = {}
        self.node_summaries: dict[str, SummaryData] = {}

    def run(self: Any, repository_path: str, **config: Any) -> str:
        """Run the summarizer step.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters
                - max_concurrency: Maximum number of concurrent tasks
                - max_tokens_per_file: Maximum tokens per file for summarization

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If the repository path is invalid
        """
        if not os.path.isdir(repository_path):
            raise ValueError(f'Repository path is not a valid directory: {repository_path}')
        job_id = f'summarizer-{uuid4()}'
        max_concurrency = config.get('max_concurrency', 5)
        max_tokens_per_file = config.get('max_tokens_per_file', 8000)
        from celery import current_app
        task = current_app.send_task('codestory_summarizer.step.run_summarizer', kwargs={'repository_path': repository_path, 'job_id': job_id, 'max_concurrency': max_concurrency, 'max_tokens_per_file': max_tokens_per_file, 'config': config})
        self.active_jobs[job_id] = {'task_id': task.id, 'repository_path': repository_path, 'start_time': time.time(), 'status': StepStatus.RUNNING, 'config': config}
        logger.info(f'Started summarizer job {job_id} for repository: {repository_path}')
        return job_id

    def status(self: Any, job_id: str) -> dict[str, Any]:
        """Check the status of a job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information including:
                - status: StepStatus enum value
                - progress: Optional float (0-100) indicating completion percentage
                - message: Optional human-readable status message
                - error: Optional error details if status is FAILED

        Raises:
            ValueError: If the job ID is invalid or not found
        """
        if job_id not in self.active_jobs:
            from celery.result import AsyncResult
            try:
                result = AsyncResult(job_id)
                if result.state == 'PENDING':
                    return {'status': StepStatus.RUNNING, 'message': 'Task is pending execution'}
                elif result.state == 'SUCCESS':
                    return {'status': StepStatus.COMPLETED, 'message': 'Task completed successfully', 'result': result.result}
                elif result.state == 'FAILURE':
                    return {'status': StepStatus.FAILED, 'message': 'Task failed', 'error': str(result.result)}
                else:
                    return {'status': StepStatus.RUNNING, 'message': f'Task is in state: {result.state}', 'info': result.info}
            except Exception as e:
                raise ValueError(f'Invalid job ID: {job_id}') from e
        job_info = self.active_jobs[job_id]
        task_id = job_info['task_id']
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        if result.state == 'PENDING':
            return {'status': StepStatus.RUNNING, 'message': 'Task is pending execution'}
        elif result.state == 'SUCCESS':
            return {'status': StepStatus.COMPLETED, 'message': 'Task completed successfully', 'result': result.result}
        elif result.state == 'FAILURE':
            return {'status': StepStatus.FAILED, 'message': 'Task failed', 'error': str(result.result)}
        else:
            status_info = {'status': StepStatus.RUNNING, 'message': f'Task is in state: {result.state}'}
            if isinstance(result.info, dict):
                status_info.update(result.info)
            return status_info

    def stop(self: Any, job_id: str) -> dict[str, Any]:
        """Stop a running job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information (same format as status method)

        Raises:
            ValueError: If the job ID is invalid or not found
            Exception: If the job cannot be stopped
        """
        if job_id not in self.active_jobs:
            raise ValueError(f'Invalid job ID: {job_id}')
        job_info = self.active_jobs[job_id]
        task_id = job_info['task_id']
        from celery.task.control import revoke
        revoke(task_id, terminate=True)
        job_info['status'] = StepStatus.STOPPED
        job_info['end_time'] = time.time()
        return {'status': StepStatus.STOPPED, 'message': f'Job {job_id} has been stopped', 'job_id': job_id}

    def cancel(self: Any, job_id: str) -> dict[str, Any]:
        """Cancel a job.

        Unlike stop(), cancel attempts to immediately terminate the job
        without waiting for a clean shutdown.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information (same format as status method)

        Raises:
            ValueError: If the job ID is invalid or not found
            Exception: If the job cannot be cancelled
        """
        result = self.stop(job_id)
        result['status'] = StepStatus.CANCELLED
        result['message'] = f'Job {job_id} has been cancelled'
        return result

    def ingestion_update(self: Any, repository_path: str, **config: Any) -> str:
        """Update the graph with summaries for a repository.

        This is similar to run() but focuses on updating summaries
        for new or changed files.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If the step fails to run
        """
        config['update_mode'] = True
        return self.run(repository_path, **config)

@shared_task(bind=True, name='codestory_summarizer.step.run_summarizer')
def run_summarizer(self: Any, repository_path: str, job_id: str, max_concurrency: int=5, max_tokens_per_file: int=8000, config: dict[str, Any] | None=None) -> dict[str, Any]:
    """Run the summarizer workflow step as a Celery task.

    Args:
        self: The Celery task instance
        repository_path: Path to the repository to process
        job_id: ID for the job
        max_concurrency: Maximum number of concurrent tasks
        max_tokens_per_file: Maximum tokens per file for summarization
        config: Additional configuration

    Returns:
        dict[str, Any]: Results of the summarization process
    """
    logger.info(f'Starting summarizer task for repository: {repository_path}')
    start_time = time.time()
    config = config or {}
    settings = get_settings()
    connector = Neo4jConnector(uri=settings.neo4j.uri, username=settings.neo4j.username, password=settings.neo4j.password.get_secret_value(), database=settings.neo4j.database)
    llm_client = create_client()
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0.0, 'message': 'Building dependency graph...'})
        analyzer = DependencyAnalyzer(connector)
        graph = analyzer.build_dependency_graph(repository_path)
        extractor = ContentExtractor(connector, repository_path)
        tracker = ProgressTracker(graph)
        summary_dir = os.path.join(repository_path, '.summaries')
        os.makedirs(summary_dir, exist_ok=True)
        summary_store: dict[str, SummaryData] = {}

        def process_node(node_id: str, node_data: NodeData) -> bool:
            try:
                content_info = extractor.extract_content(node_data)
                content = content_info.get('content', '')
                context = content_info.get('context', [])
                child_summaries: list[Any] = []
                for dep_id in node_data.dependents:
                    if dep_id in summary_store:
                        child_summary = summary_store[dep_id].summary
                        node_type = summary_store[dep_id].node_type
                        prefix = f'[{node_type}] '
                        if not child_summary.startswith(prefix):
                            child_summary = prefix + child_summary
                        child_summaries.append(child_summary)
                content_str = content if isinstance(content, str) else str(content)
                context_list = context if isinstance(context, list) else [str(context)]
                prompt = get_summary_prompt(node=node_data, content=content_str, context=context_list, child_summaries=child_summaries, max_tokens=max_tokens_per_file)
                messages = [ChatMessage(role=ChatRole.SYSTEM, content='You are an expert code summarizer.'), ChatMessage(role=ChatRole.USER, content=prompt)]
                response = llm_client.chat(messages=messages, max_tokens=500, temperature=0.1)
                have_choices = response.choices and len(response.choices) > 0
                summary_text = response.choices[0].message.content if have_choices else ''
                token_count = 0
                if response.usage:
                    prompt_tokens = response.usage.prompt_tokens or 0
                    completion_tokens = response.usage.completion_tokens or 0
                    token_count = prompt_tokens + completion_tokens
                safe_summary_text = summary_text if summary_text is not None else ''
                summary = SummaryData(node_id=node_id, node_type=node_data.type, summary=safe_summary_text, token_count=token_count)
                summary_store[node_id] = summary
                safe_summary = safe_summary_text if safe_summary_text else ''
                store_summary(connector, node_id, safe_summary, node_data.type.value)
                summary_file = os.path.join(summary_dir, f'{node_id}.json')
                with open(summary_file, 'w') as f:
                    json.dump(summary.model_dump(), f, indent=2)
                return True
            except Exception as e:
                logger.exception(f'Error processing node {node_id}: {e}')
                return False
        executor = ParallelExecutor(max_concurrency=max_concurrency)

        def on_node_completed(node_id: str, node_data: NodeData) -> None:
            if tracker.should_update():
                progress_message = tracker.update_progress()
                self.update_state(state='PROGRESS', meta={'progress': tracker.get_progress(), 'message': progress_message})
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            graph = loop.run_until_complete(executor.process_graph(graph=graph, process_func=process_node, on_completion=on_node_completed))
        finally:
            loop.close()
        end_time = time.time()
        duration = end_time - start_time
        result = {'job_id': job_id, 'repository_path': repository_path, 'start_time': start_time, 'end_time': end_time, 'duration': duration, 'nodes_processed': graph.completed_count, 'nodes_failed': graph.failed_count, 'nodes_skipped': graph.skipped_count, 'total_nodes': graph.total_count, 'progress': 100.0, 'status': StepStatus.COMPLETED, 'message': f'Generated {graph.completed_count} summaries in {duration:.2f} seconds'}
        logger.info(f"Summarizer task completed: {result['message']}")
        return result
    except Exception as e:
        logger.exception(f'Error in summarizer task: {e}')
        end_time = time.time()
        duration = end_time - start_time
        return {'job_id': job_id, 'repository_path': repository_path, 'start_time': start_time, 'end_time': end_time, 'duration': duration, 'status': StepStatus.FAILED, 'error': str(e), 'message': f'Summarizer task failed: {e!s}'}
    finally:
        connector.close()

def store_summary(connector: Neo4jConnector, node_id: str, summary: str, node_type: str) -> None:
    """Store a summary in Neo4j.

    Args:
        connector: Neo4j connector
        node_id: ID of the node
        summary: Summary text
        node_type: Type of the node
    """
    summary_id = str(uuid4())
    summary_query = '\n    CREATE (s:Summary {\n        id: $summary_id,\n        text: $summary,\n        timestamp: $timestamp,\n        source_type: $source_type\n    })\n    '
    connector.execute_query(summary_query, params={'summary_id': summary_id, 'summary': summary, 'timestamp': time.time(), 'source_type': node_type})
    link_query = '\n    MATCH (s:Summary {id: $summary_id})\n    MATCH (n) WHERE ID(n) = $node_id\n    CREATE (n)-[:HAS_SUMMARY]->(s)\n    '
    connector.execute_query(link_query, params={'summary_id': summary_id, 'node_id': int(node_id)})