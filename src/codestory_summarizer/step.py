"""Summarizer workflow step implementation.

This module implements the SummarizerStep class, which generates natural language
summaries for code elements using a language model and stores them in Neo4j.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Union

from celery import shared_task

from src.codestory.config.settings import get_settings
from src.codestory.graphdb.neo4j_connector import Neo4jConnector
from src.codestory.ingestion_pipeline.step import PipelineStep, StepStatus
from src.codestory.llm.client import create_client
from src.codestory.llm.models import ChatMessage, ChatRole

from .dependency_analyzer import DependencyAnalyzer
from .models import DependencyGraph, NodeData, NodeType, ProcessingStatus, SummaryData
from .parallel_executor import ParallelExecutor
from .prompts import get_summary_prompt
from .utils import ContentExtractor, ProgressTracker, get_progress_message

# Set up logging
logger = logging.getLogger(__name__)


class SummarizerStep(PipelineStep):
    """Workflow step that generates summaries for code elements.
    
    This step analyzes the code in a repository, generates natural language
    summaries using a language model, and stores them in the Neo4j database.
    """
    
    def __init__(self):
        """Initialize the summarizer step."""
        self.settings = get_settings()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.node_summaries: Dict[str, SummaryData] = {}
    
    def run(self, repository_path: str, **config: Any) -> str:
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
        # Validate repository path
        if not os.path.isdir(repository_path):
            raise ValueError(f"Repository path is not a valid directory: {repository_path}")
        
        # Generate job ID
        job_id = f"summarizer-{uuid.uuid4()}"
        
        # Extract configuration
        max_concurrency = config.get("max_concurrency", 5)
        max_tokens_per_file = config.get("max_tokens_per_file", 8000)
        
        # Start the Celery task
        task = run_summarizer.apply_async(
            kwargs={
                "repository_path": repository_path,
                "job_id": job_id,
                "max_concurrency": max_concurrency,
                "max_tokens_per_file": max_tokens_per_file,
                "config": config
            }
        )
        
        # Store job information
        self.active_jobs[job_id] = {
            "task_id": task.id,
            "repository_path": repository_path,
            "start_time": time.time(),
            "status": StepStatus.RUNNING,
            "config": config
        }
        
        logger.info(f"Started summarizer job {job_id} for repository: {repository_path}")
        
        return job_id
    
    def status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a job.
        
        Args:
            job_id: Identifier for the job
            
        Returns:
            Dict[str, Any]: Status information including:
                - status: StepStatus enum value
                - progress: Optional float (0-100) indicating completion percentage
                - message: Optional human-readable status message
                - error: Optional error details if status is FAILED
                
        Raises:
            ValueError: If the job ID is invalid or not found
        """
        if job_id not in self.active_jobs:
            # Check if this is a task ID
            from celery.result import AsyncResult
            try:
                result = AsyncResult(job_id)
                if result.state == "PENDING":
                    return {
                        "status": StepStatus.RUNNING,
                        "message": "Task is pending execution",
                    }
                elif result.state == "SUCCESS":
                    return {
                        "status": StepStatus.COMPLETED,
                        "message": "Task completed successfully",
                        "result": result.get()
                    }
                elif result.state == "FAILURE":
                    return {
                        "status": StepStatus.FAILED,
                        "message": "Task failed",
                        "error": str(result.result)
                    }
                else:
                    return {
                        "status": StepStatus.RUNNING,
                        "message": f"Task is in state: {result.state}",
                        "info": result.info
                    }
            except Exception:
                raise ValueError(f"Invalid job ID: {job_id}")
        
        job_info = self.active_jobs[job_id]
        task_id = job_info["task_id"]
        
        # Get task status
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        
        if result.state == "PENDING":
            return {
                "status": StepStatus.RUNNING,
                "message": "Task is pending execution",
            }
        elif result.state == "SUCCESS":
            return {
                "status": StepStatus.COMPLETED,
                "message": "Task completed successfully",
                "result": result.get()
            }
        elif result.state == "FAILURE":
            return {
                "status": StepStatus.FAILED,
                "message": "Task failed",
                "error": str(result.result)
            }
        else:
            # Task is still running
            status_info = {
                "status": StepStatus.RUNNING,
                "message": f"Task is in state: {result.state}",
            }
            
            # Add info from the task if available
            if isinstance(result.info, dict):
                status_info.update(result.info)
            
            return status_info
    
    def stop(self, job_id: str) -> Dict[str, Any]:
        """Stop a running job.
        
        Args:
            job_id: Identifier for the job
            
        Returns:
            Dict[str, Any]: Status information (same format as status method)
            
        Raises:
            ValueError: If the job ID is invalid or not found
            Exception: If the job cannot be stopped
        """
        if job_id not in self.active_jobs:
            raise ValueError(f"Invalid job ID: {job_id}")
        
        job_info = self.active_jobs[job_id]
        task_id = job_info["task_id"]
        
        # Revoke the task
        from celery.task.control import revoke
        revoke(task_id, terminate=True)
        
        # Update job status
        job_info["status"] = StepStatus.STOPPED
        job_info["end_time"] = time.time()
        
        return {
            "status": StepStatus.STOPPED,
            "message": f"Job {job_id} has been stopped",
            "job_id": job_id
        }
    
    def cancel(self, job_id: str) -> Dict[str, Any]:
        """Cancel a job.
        
        Unlike stop(), cancel attempts to immediately terminate the job
        without waiting for a clean shutdown.
        
        Args:
            job_id: Identifier for the job
            
        Returns:
            Dict[str, Any]: Status information (same format as status method)
            
        Raises:
            ValueError: If the job ID is invalid or not found
            Exception: If the job cannot be cancelled
        """
        # For Celery tasks, cancel is the same as stop
        result = self.stop(job_id)
        result["status"] = StepStatus.CANCELLED
        result["message"] = f"Job {job_id} has been cancelled"
        
        return result
    
    def ingestion_update(self, repository_path: str, **config: Any) -> str:
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
        # Add update flag to config to indicate this is an update
        config["update_mode"] = True
        
        # Run the step normally, with update mode enabled
        return self.run(repository_path, **config)


@shared_task(bind=True, name="summarizer.run_summarizer")
def run_summarizer(
    self,
    repository_path: str,
    job_id: str,
    max_concurrency: int = 5,
    max_tokens_per_file: int = 8000,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Run the summarizer workflow step as a Celery task.
    
    Args:
        repository_path: Path to the repository to process
        job_id: ID for the job
        max_concurrency: Maximum number of concurrent tasks
        max_tokens_per_file: Maximum tokens per file for summarization
        config: Additional configuration
        
    Returns:
        Dict with results
    """
    logger.info(f"Starting summarizer task for repository: {repository_path}")
    
    start_time = time.time()
    config = config or {}
    update_mode = config.get("update_mode", False)
    
    # Create Neo4j connector
    settings = get_settings()
    connector = Neo4jConnector(
        uri=settings.neo4j.uri,
        username=settings.neo4j.username,
        password=settings.neo4j.password.get_secret_value(),
        database=settings.neo4j.database,
    )
    
    # Create LLM client
    llm_client = create_client()
    
    try:
        # Notify of progress
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 0.0,
                "message": "Building dependency graph...",
            }
        )
        
        # Build dependency graph
        analyzer = DependencyAnalyzer(connector)
        graph = analyzer.build_dependency_graph(repository_path)
        
        # Initialize content extractor
        extractor = ContentExtractor(connector, repository_path)
        
        # Initialize progress tracker
        tracker = ProgressTracker(graph)
        
        # Create directory to store summaries if it doesn't exist
        summary_dir = os.path.join(repository_path, ".summaries")
        os.makedirs(summary_dir, exist_ok=True)
        
        # Initialize summary store
        summary_store: Dict[str, SummaryData] = {}
        
        # Define node processor function
        def process_node(node_id: str, node_data: NodeData) -> bool:
            try:
                # Extract content
                content_info = extractor.extract_content(node_data)
                content = content_info.get("content", "")
                context = content_info.get("context", [])
                
                # Get child summaries for higher-level nodes
                child_summaries = []
                
                for dep_id in node_data.dependents:
                    if dep_id in summary_store:
                        child_summary = summary_store[dep_id].summary
                        node_type = summary_store[dep_id].node_type
                        
                        prefix = f"[{node_type}] "
                        if not child_summary.startswith(prefix):
                            child_summary = prefix + child_summary
                            
                        child_summaries.append(child_summary)
                
                # Generate prompt
                prompt = get_summary_prompt(
                    node=node_data,
                    content=content,
                    context=context,
                    child_summaries=child_summaries,
                    max_tokens=max_tokens_per_file
                )
                
                # Call LLM to generate summary
                messages = [
                    ChatMessage(role=ChatRole.SYSTEM, content="You are an expert code summarizer."),
                    ChatMessage(role=ChatRole.USER, content=prompt)
                ]
                
                response = llm_client.chat(
                    messages=messages,
                    max_tokens=500,
                    temperature=0.1
                )
                
                summary_text = response.choices[0].message.content
                
                # Create summary data
                summary = SummaryData(
                    node_id=node_id,
                    node_type=node_data.type,
                    summary=summary_text,
                    token_count=response.usage.prompt_tokens + response.usage.completion_tokens
                )
                
                # Store summary
                summary_store[node_id] = summary
                
                # Write summary to Neo4j
                store_summary(connector, node_id, summary_text, node_data.type.value)
                
                # Write summary to file for easy inspection
                summary_file = os.path.join(summary_dir, f"{node_id}.json")
                with open(summary_file, "w") as f:
                    json.dump(summary.model_dump(), f, indent=2)
                
                return True
            except Exception as e:
                logger.exception(f"Error processing node {node_id}: {e}")
                return False
        
        # Process nodes in parallel
        executor = ParallelExecutor(max_concurrency=max_concurrency)
        
        # Define completion callback for progress updates
        def on_node_completed(node_id: str, node_data: NodeData) -> None:
            if tracker.should_update():
                progress_message = tracker.update_progress()
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": tracker.get_progress(),
                        "message": progress_message,
                    }
                )
        
        # Run the async executor in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            graph = loop.run_until_complete(
                executor.process_graph(
                    graph=graph,
                    process_func=process_node,
                    on_completion=on_node_completed
                )
            )
        finally:
            loop.close()
        
        # Calculate final stats
        end_time = time.time()
        duration = end_time - start_time
        
        # Create summary
        result = {
            "job_id": job_id,
            "repository_path": repository_path,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "nodes_processed": graph.completed_count,
            "nodes_failed": graph.failed_count,
            "nodes_skipped": graph.skipped_count,
            "total_nodes": graph.total_count,
            "progress": 100.0,  # Mark as completed
            "status": StepStatus.COMPLETED,
            "message": f"Generated {graph.completed_count} summaries in {duration:.2f} seconds",
        }
        
        logger.info(f"Summarizer task completed: {result['message']}")
        
        return result
    except Exception as e:
        logger.exception(f"Error in summarizer task: {e}")
        
        # Return error result
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            "job_id": job_id,
            "repository_path": repository_path,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "status": StepStatus.FAILED,
            "error": str(e),
            "message": f"Summarizer task failed: {str(e)}",
        }
    finally:
        # Close connections
        connector.close()


def store_summary(
    connector: Neo4jConnector, 
    node_id: str, 
    summary: str,
    node_type: str
) -> None:
    """Store a summary in Neo4j.
    
    Args:
        connector: Neo4j connector
        node_id: ID of the node
        summary: Summary text
        node_type: Type of the node
    """
    # Create summary node
    summary_id = str(uuid.uuid4())
    
    # Create the Summary node
    summary_query = """
    CREATE (s:Summary {
        id: $summary_id,
        text: $summary,
        timestamp: $timestamp,
        source_type: $source_type
    })
    """
    
    connector.run_query(
        summary_query,
        parameters={
            "summary_id": summary_id,
            "summary": summary,
            "timestamp": time.time(),
            "source_type": node_type
        }
    )
    
    # Link the summary to the original node
    link_query = """
    MATCH (s:Summary {id: $summary_id})
    MATCH (n) WHERE ID(n) = $node_id
    CREATE (n)-[:HAS_SUMMARY]->(s)
    """
    
    connector.run_query(
        link_query,
        parameters={
            "summary_id": summary_id,
            "node_id": int(node_id)
        }
    )