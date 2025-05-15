"""Filesystem workflow step for the ingestion pipeline.

This step scans the filesystem of the repository and creates a graph
of directories and files, which can be linked to AST nodes.
"""

import logging
import os
import time
from typing import Any

from celery import shared_task

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus, generate_job_id

# Set up logging
logger = logging.getLogger(__name__)


class FileSystemStep(PipelineStep):
    """Pipeline step that processes the filesystem structure of a repository.

    This step scans the filesystem of the repository and creates a graph
    of directories and files in Neo4j, which can be linked to AST nodes.
    """

    def __init__(self):
        """Initialize the filesystem step."""
        self.settings = get_settings()
        self.active_jobs: dict[str, dict[str, Any]] = {}

    def run(self, repository_path: str, **config: Any) -> str:
        """Run the filesystem step.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters
                - ignore_patterns: list of glob patterns to ignore
                - max_depth: Maximum directory depth to traverse
                - include_extensions: list of file extensions to include

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If the repository path is invalid
        """
        # Generate a job ID
        job_id = generate_job_id()

        print("*** STEP DEBUG: Running FileSystemStep.run ***")
        print(f"Generated job_id: {job_id}")
        print(f"Repository path: {repository_path}")
        print(f"Config: {config}")

        # Import Celery app for better debugging
        from codestory.ingestion_pipeline.celery_app import app as celery_app

        # Log worker and queue status
        print(f"Celery active queues: {celery_app.control.inspect().active_queues()}")
        print(f"Celery registered tasks: {celery_app.control.inspect().registered()}")

        # Call the Celery task with explicit queue
        task = process_filesystem.apply_async(
            args=[repository_path, job_id],
            kwargs=config,
            queue="ingestion",  # Explicitly set the queue here too
        )

        print(f"Celery task ID: {task.id}")
        print(f"Celery task status: {task.status}")

        # Try to get task info
        from celery.result import AsyncResult

        result = AsyncResult(task.id, app=celery_app)
        print(f"Celery AsyncResult state: {result.state}")
        print(f"Celery AsyncResult info: {result.info}")

        # Store job information
        self.active_jobs[job_id] = {
            "task_id": task.id,
            "repository_path": repository_path,
            "start_time": time.time(),
            "status": StepStatus.RUNNING,
            "config": config,
        }

        logger.info(f"Started filesystem step job {job_id} for {repository_path}")
        print("*** END STEP DEBUG ***")

        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        """Check the status of a job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        if job_id not in self.active_jobs:
            raise ValueError(f"Job ID not found: {job_id}")

        job_info = self.active_jobs[job_id]
        task_id = job_info["task_id"]

        print(
            f"*** STATUS DEBUG: checking status for job_id={job_id}, task_id={task_id} ***"
        )

        from celery.result import AsyncResult

        from codestory.ingestion_pipeline.celery_app import app

        # Get status from Celery
        result = AsyncResult(task_id, app=app)
        print(f"Celery result status: {result.status}")
        print(f"Celery result ready: {result.ready()}")
        print(f"Celery result info: {result.info}")

        status_info = {
            "status": StepStatus.RUNNING,
            "progress": None,
            "message": None,
            "error": None,
        }

        if result.ready():
            print(f"Task is ready. Successful: {result.successful()}")
            if result.successful():
                try:
                    task_result = result.result  # Fixed: Use result directly instead of blocking get()
                    print(f"Task result: {task_result}")
                    status_info.update(
                        {
                            "status": StepStatus.COMPLETED,
                            "message": f"Processed {task_result.get('file_count', 0)} files",
                            "progress": 100.0,
                            "result": task_result,
                        }
                    )
                except Exception as e:
                    print(f"Error getting result: {e}")
                    status_info.update(
                        {
                            "status": StepStatus.FAILED,
                            "error": f"Error retrieving result: {e!s}",
                        }
                    )
            else:
                print(f"Task failed. Result: {result.result}")
                status_info.update(
                    {
                        "status": StepStatus.FAILED,
                        "error": str(result.result),
                    }
                )
        else:
            # Still running
            print(f"Task still running. State: {result.state}")
            if isinstance(result.info, dict):
                # If the task reported progress
                print(f"Task reported progress: {result.info}")
                status_info.update(
                    {
                        "progress": result.info.get("progress"),
                        "message": result.info.get("message"),
                    }
                )

        # Update job info with latest status
        job_info.update(status_info)
        print(f"Final status info: {status_info}")
        print("*** END STATUS DEBUG ***")

        return job_info

    def stop(self, job_id: str) -> dict[str, Any]:
        """Stop a running job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        if job_id not in self.active_jobs:
            raise ValueError(f"Job ID not found: {job_id}")

        job_info = self.active_jobs[job_id]
        task_id = job_info["task_id"]

        from codestory.ingestion_pipeline.celery_app import app

        # Stop the task
        app.control.revoke(task_id, terminate=True)

        # Update job info
        job_info.update(
            {
                "status": StepStatus.STOPPED,
                "message": f"Job {job_id} has been stopped",
            }
        )

        return job_info

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel a job.

        Args:
            job_id: Identifier for the job

        Returns:
            dict[str, Any]: Status information

        Raises:
            ValueError: If the job ID is not found
        """
        # For Celery tasks, cancel is effectively the same as stop
        result = self.stop(job_id)
        result["status"] = StepStatus.CANCELLED
        result["message"] = f"Job {job_id} has been cancelled"

        return result

    def ingestion_update(self, repository_path: str, **config: Any) -> str:
        """Update the graph with the results of this step only.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters

        Returns:
            str: Job ID that can be used to check the status
        """
        # For this step, ingestion_update is the same as run
        return self.run(repository_path, **config)


@shared_task(
    name="filesystem.run", bind=True, queue="ingestion"  # Explicitly set the queue
)
def process_filesystem(
    self,
    repository_path: str,
    job_id: str,
    ignore_patterns: list[str] | None = None,
    max_depth: int | None = None,
    include_extensions: list[str] | None = None,
    **config: Any,
) -> dict[str, Any]:
    """Process the filesystem of a repository.

    Args:
        self: The Celery task instance
        repository_path: Path to the repository to process
        job_id: Identifier for the job
        ignore_patterns: list of glob patterns to ignore
        max_depth: Maximum directory depth to traverse
        include_extensions: list of file extensions to include
        **config: Additional configuration parameters

    Returns:
        dict[str, Any]: Result information
    """
    start_time = time.time()
    print("*** CELERY DEBUG: Starting task process_filesystem (DEBUGGING) ***")
    print(f"Repository path: {repository_path}")
    print(f"Job ID: {job_id}")
    print(f"Ignore patterns: {ignore_patterns}")
    print(f"Other config: {config}")

    # Log additional info about the task
    task_id = self.request.id if hasattr(self, "request") else "Unknown"
    print(f"Celery task ID: {task_id}")

    logger.info(f"Processing filesystem for {repository_path}")

    # Default ignore patterns if not provided
    if ignore_patterns is None:
        ignore_patterns = [
            "node_modules/",
            ".git/",
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "venv/",
            ".venv/",
            ".idea/",
            ".vscode/",
        ]

    # Set up Neo4j connection
    try:
        settings = get_settings()
        neo4j = Neo4jConnector(
            uri=settings.neo4j.uri,
            username=settings.neo4j.username,
            password=settings.neo4j.password.get_secret_value(),
            database=settings.neo4j.database,
        )
    except Exception as e:
        logger.exception(f"Error connecting to Neo4j: {e}")
        return {
            "status": StepStatus.FAILED,
            "error": f"Neo4j connection error: {e!s}",
            "job_id": job_id,
        }

    # Process the filesystem
    try:
        file_count = 0
        dir_count = 0

        # Create repository node
        repo_name = os.path.basename(repository_path)
        repo_node = neo4j.create_node(
            label="Repository",
            properties={
                "name": repo_name,
                "path": repository_path,
            },
        )

        # Process the repository
        print(f"Starting to walk repository: {repository_path}")
        print(f"Repository exists? {os.path.exists(repository_path)}")
        print(f"Repository is directory? {os.path.isdir(repository_path)}")
        print(f"Repository contents: {os.listdir(repository_path)}")

        for current_dir, dirs, files in os.walk(repository_path):
            rel_path = os.path.relpath(current_dir, repository_path)
            print(f"Walking directory: {current_dir} (relative: {rel_path})")
            print(f"  Contains directories: {dirs}")
            print(f"  Contains files: {files}")

            # Check depth limit
            if max_depth is not None:
                rel_path = os.path.relpath(current_dir, repository_path)
                if rel_path != "." and rel_path.count(os.sep) >= max_depth:
                    print(f"  Skipping directory due to depth limit: {rel_path}")
                    dirs.clear()  # Don't descend further
                    continue

            # Filter directories based on ignore patterns
            dirs_to_remove = []
            for d in dirs:
                if any(
                    d.startswith(pat.rstrip("/")) or d == pat.rstrip("/")
                    for pat in ignore_patterns
                    if pat.endswith("/")
                ):
                    print(f"  Ignoring directory {d} due to pattern match")
                    dirs_to_remove.append(d)

            for d in dirs_to_remove:
                dirs.remove(d)

            # Create directory node
            rel_dir_path = os.path.relpath(current_dir, repository_path)
            if rel_dir_path == ".":
                # This is the repository root
                dir_node = repo_node
            else:
                print(f"  Creating directory node: {rel_dir_path}")
                try:
                    dir_node = neo4j.create_node(
                        label="Directory",
                        properties={
                            "name": os.path.basename(current_dir),
                            "path": rel_dir_path,
                        },
                    )
                    print(f"  Directory node created successfully: {dir_node}")
                except Exception as e:
                    print(f"  Error creating directory node: {e}")
                    raise

                # Link to parent directory
                parent_path = os.path.dirname(rel_dir_path)
                if parent_path == "":
                    # Parent is the repo
                    neo4j.create_relationship(
                        start_node=repo_node,
                        end_node=dir_node,
                        rel_type="CONTAINS",
                    )
                else:
                    # Find parent directory node
                    parent_node = neo4j.find_node(
                        label="Directory",
                        properties={"path": parent_path},
                    )
                    if parent_node:
                        neo4j.create_relationship(
                            start_node=parent_node,
                            end_node=dir_node,
                            rel_type="CONTAINS",
                        )

                dir_count += 1

            # Process files
            for file in files:
                # Skip files matching ignore patterns
                if any(
                    file == pat or file.endswith(pat.lstrip("*"))
                    for pat in ignore_patterns
                    if not pat.endswith("/")
                ):
                    continue

                # Check if extension is included
                if include_extensions and not any(
                    file.endswith(ext) for ext in include_extensions
                ):
                    continue

                # Create file node
                file_path = os.path.join(rel_dir_path, file)
                if rel_dir_path == ".":
                    file_path = file

                print(f"  Creating file node: {file_path}")
                try:
                    file_node = neo4j.create_node(
                        label="File",
                        properties={
                            "name": file,
                            "path": file_path,
                            "extension": os.path.splitext(file)[1].lstrip(".") or None,
                            "size": os.path.getsize(os.path.join(current_dir, file)),
                            "modified": os.path.getmtime(
                                os.path.join(current_dir, file)
                            ),
                        },
                    )
                    print(f"  File node created successfully: {file_node}")
                except Exception as e:
                    print(f"  Error creating file node: {e}")
                    raise

                # Link to directory
                neo4j.create_relationship(
                    start_node=dir_node,
                    end_node=file_node,
                    rel_type="CONTAINS",
                )

                file_count += 1

                # Report progress (every 100 files)
                if file_count % 100 == 0:
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "progress": None,  # Can't know total
                            "message": f"Processed {file_count} files, {dir_count} directories",
                        },
                    )

        # Record end time
        end_time = time.time()
        duration = end_time - start_time

        # Create a processing record
        neo4j.create_node(
            label="ProcessingRecord",
            properties={
                "step": "filesystem",
                "job_id": job_id,
                "repository": repo_name,
                "timestamp": time.time(),
                "duration": duration,
                "file_count": file_count,
                "dir_count": dir_count,
            },
        )

        logger.info(
            f"Completed filesystem processing for {repository_path}: "
            f"{file_count} files, {dir_count} directories in {duration:.2f} seconds"
        )

        return {
            "status": StepStatus.COMPLETED,
            "job_id": job_id,
            "duration": duration,
            "file_count": file_count,
            "dir_count": dir_count,
        }

    except Exception as e:
        logger.exception(f"Error processing filesystem: {e}")
        return {
            "status": StepStatus.FAILED,
            "error": str(e),
            "job_id": job_id,
        }
    finally:
        # Close Neo4j connection
        neo4j.close()
