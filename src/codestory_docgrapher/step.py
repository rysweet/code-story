"""Documentation grapher workflow step implementation.

This module implements the DocumentationGrapherStep class, which creates
a knowledge graph of documentation and links it to code entities.
"""

import logging
import os
import time
from typing import Any
from uuid import uuid4

from celery import shared_task

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus

from .document_finder import DocumentFinder
from .knowledge_graph import KnowledgeGraph
from .parsers import get_parser_for_file
from .utils.progress_tracker import ProgressTracker

# Set up logging
logger = logging.getLogger(__name__)


class DocumentationGrapherStep(PipelineStep):
    """Workflow step that creates a knowledge graph of documentation.

    This step searches for documentation files in a repository, extracts
    entities and relationships, and links them to code entities.
    """

    def __init__(self) -> Any:[misc]
        """Initialize the DocumentationGrapher step."""
        self.settings = get_settings()
        self.active_jobs: dict[str, dict[str, Any]] = {}

    def run(self, repository_path: str, **config: Any) -> str:
        """Run the DocumentationGrapher step.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters
                - ignore_patterns: List of patterns to ignore
                - use_llm: Whether to use LLM for advanced analysis

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If the repository path is invalid
        """
        # Validate repository path
        if not os.path.isdir(repository_path):
            raise ValueError(f"Repository path is not a valid directory: {repository_path}")

        # Generate job ID
        job_id = f"docgrapher-{uuid4()}"

        # Extract configuration
        ignore_patterns = config.get("ignore_patterns", [])
        use_llm = config.get("use_llm", True)

        # Start the Celery task using current_app.send_task with the fully qualified task name
        from celery import current_app

        # Use the fully qualified task name to avoid task routing issues
        task = current_app.send_task(
            "codestory_docgrapher.step.run_docgrapher",
            kwargs={
                "repository_path": repository_path,
                "job_id": job_id,
                "ignore_patterns": ignore_patterns,
                "use_llm": use_llm,
                "config": config,
            },
        )

        # Store job information
        self.active_jobs[job_id] = {
            "task_id": task.id,
            "repository_path": repository_path,
            "start_time": time.time(),
            "status": StepStatus.RUNNING,
            "config": config,
        }

        logger.info(f"Started DocumentationGrapher job {job_id} for repository: {repository_path}")

        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
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
                        "result": result.result,  # Fixed: Use result directly instead of 
                                                  # blocking get()
                    }
                elif result.state == "FAILURE":
                    return {
                        "status": StepStatus.FAILED,
                        "message": "Task failed",
                        "error": str(result.result),
                    }
                else:
                    return {
                        "status": StepStatus.RUNNING,
                        "message": f"Task is in state: {result.state}",
                        "info": result.info,
                    }
            except Exception:
                raise ValueError(f"Invalid job ID: {job_id}") from None

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
                "result": result.result,  # Fixed: Use result directly instead of blocking get()
            }
        elif result.state == "FAILURE":
            return {
                "status": StepStatus.FAILED,
                "message": "Task failed",
                "error": str(result.result),
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

    def stop(self, job_id: str) -> dict[str, Any]:
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
            "job_id": job_id,
        }

    def cancel(self, job_id: str) -> dict[str, Any]:
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
        result["status"] = StepStatus.CANCELLED
        result["message"] = f"Job {job_id} has been cancelled"

        return result

    def ingestion_update(self, repository_path: str, **config: Any) -> str:
        """Update the documentation graph for a repository.

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


@shared_task(bind=True, name="codestory_docgrapher.step.run_docgrapher")[misc]
def run_docgrapher([no-untyped-def]
    self,  # Celery task instance
    repository_path: str,
    job_id: str,
    ignore_patterns: list[str] | None = None,
    use_llm: bool = True,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the DocumentationGrapher workflow step as a Celery task.

    Args:
        self: Celery task instance
        repository_path: Path to the repository to process
        job_id: ID for the job
        ignore_patterns: List of patterns to ignore
        use_llm: Whether to use LLM for advanced analysis
        config: Additional configuration

    Returns:
        Dict with results
    """
    logger.info(f"Starting DocumentationGrapher task for repository: {repository_path}")

    start_time = time.time()
    ignore_patterns = ignore_patterns or []
    config = config or {}
    # Check if running in update mode
    config.get("update_mode", False)  # Used by subclasses

    # Create Neo4j connector
    settings = get_settings()
    connector = Neo4jConnector(
        uri=settings.neo4j.uri,
        username=settings.neo4j.username,
        password=settings.neo4j.password.get_secret_value(),
        database=settings.neo4j.database,
    )

    try:
        # Notify of progress
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 0.0,
                "message": "Finding documentation files...",
            },
        )

        # Find documentation files
        document_finder = DocumentFinder(connector, repository_path)
        doc_files = document_finder.find_documentation_files(ignore_patterns)

        # Create knowledge graph
        knowledge_graph = KnowledgeGraph(connector, repository_path)

        # Initialize progress tracker
        tracker = ProgressTracker(knowledge_graph.graph)
        tracker.set_total_documents(len(doc_files))

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 5.0,
                "message": f"Found {len(doc_files)} documentation files to process",
            },
        )

        # Process each documentation file
        for doc_file in doc_files:
            # Add document to graph
            knowledge_graph.add_document(doc_file)

            # Get parser for file
            parser = get_parser_for_file(doc_file)

            if parser:
                # Parse the file
                parsed_data = parser.parse(doc_file)

                # Add entities and relationships to graph
                knowledge_graph.add_entities(parsed_data.get("entities", []))
                knowledge_graph.add_relationships(parsed_data.get("relationships", []))

            # Mark document as processed
            tracker.document_processed()

            # Update progress
            if tracker.should_update():
                progress_message = tracker.update_progress()
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": tracker.get_progress(),
                        "message": progress_message,
                    },
                )

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 75.0,
                "message": "Linking documentation to code entities...",
            },
        )

        # Link documentation to code entities
        knowledge_graph.link_to_code_entities()

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 90.0,
                "message": "Storing documentation graph in Neo4j...",
            },
        )

        # Store graph in Neo4j
        knowledge_graph.store_in_neo4j()

        # Calculate final stats
        end_time = time.time()
        duration = end_time - start_time
        stats = knowledge_graph.get_graph_stats()

        # Create summary
        result = {
            "job_id": job_id,
            "repository_path": repository_path,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "documents_processed": stats["documents"],
            "entities_processed": stats["entities"],
            "relationships_processed": stats["relationships"],
            "progress": 100.0,  # Mark as completed
            "status": StepStatus.COMPLETED,
            "message": (
                f"Processed {stats['documents']} documents, "
                f"created {stats['entities']} entities and "
                f"{stats['relationships']} relationships in {duration:.2f} seconds"
            ),
            "stats": stats,
        }

        logger.info(f"DocumentationGrapher task completed: {result['message']}")

        return result
    except Exception as e:
        logger.exception(f"Error in DocumentationGrapher task: {e}")

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
            "message": f"DocumentationGrapher task failed: {e!s}",
        }
    finally:
        # Close connections
        connector.close()