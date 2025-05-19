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
                - job_id: Optional job ID to use (will be generated if not provided)

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If the repository path is invalid
        """
        # Generate a job ID if not provided
        job_id = config.pop('job_id', None) or generate_job_id()

        print("*** STEP DEBUG: Running FileSystemStep.run ***")
        print(f"Generated job_id: {job_id}")
        print(f"Repository path: {repository_path}")
        print(f"Config: {config}")

        # Import Celery app for better debugging
        from codestory.ingestion_pipeline.celery_app import app as celery_app

        # Log worker and queue status
        print(f"Celery active queues: {celery_app.control.inspect().active_queues()}")
        print(f"Celery registered tasks: {celery_app.control.inspect().registered()}")

        # Make sure job_id is in kwargs, not args
        kwargs = config.copy()
        kwargs['job_id'] = job_id
        
        # Call the Celery task with explicit queue and the repository_path as first arg
        task = process_filesystem.apply_async(
            args=[repository_path],  # Just pass repository_path as first arg
            kwargs=kwargs,           # Pass other parameters including job_id as kwargs
            queue="ingestion",       # Explicitly set the queue here too
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
    # Register the task with a clear, consistent name
    name="filesystem.run", bind=True, queue="ingestion"  # Explicitly set the queue
)
def process_filesystem(
    self,
    repository_path: str,  # Required positional parameter
    ignore_patterns: list[str] | None = None,
    max_depth: int | None = None,
    include_extensions: list[str] | None = None,
    job_id: str = None,  # Optional - will be generated if not provided
    **config: Any,
) -> dict[str, Any]:
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
    print("*** CELERY DEBUG: Starting task process_filesystem (DEBUGGING) ***")
    print(f"Task ID: {self.request.id}")
    print(f"Args: repository_path={repository_path}")
    print(f"Kwargs: {config}")
    
    # Validate repository_path - it's now a required parameter
    if not repository_path:
        raise ValueError("repository_path is required")
        
    if job_id is None:
        # Generate a job ID if not provided
        job_id = f"task-{self.request.id}" if hasattr(self, "request") else f"task-{time.time()}"
    
    # Enhanced debug logging
    task_id = self.request.id if hasattr(self, "request") else "Unknown"
    
    print(f"======= FILESYSTEM STEP DEBUG ======")
    print(f"Task ID: {task_id}")
    print(f"Repository path: {repository_path}")
    print(f"Repository exists: {os.path.exists(repository_path)}")
    print(f"Repository is directory: {os.path.isdir(repository_path)}")
    try:
        print(f"Repository contents: {os.listdir(repository_path)[:10]}... (first 10 entries)")
    except Exception as e:
        print(f"Error listing repository: {e}")
    print(f"Job ID: {job_id}")
    print(f"Ignore patterns: {ignore_patterns}")
    print(f"Max depth: {max_depth}")
    print(f"Include extensions: {include_extensions}")
    print(f"Other config: {config}")
    print(f"====================================")

    logger.info(f"Starting filesystem processing for {repository_path} (task_id: {task_id}, job_id: {job_id})")
    logger.info(f"Max depth: {max_depth}, Patterns: {ignore_patterns}")

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

    # Try multiple Neo4j connection configurations
    neo4j = None
    errors = []
    
    # Get settings for the default configuration
    settings = get_settings()
    logger.info(f"Current Neo4j settings from config: uri={settings.neo4j.uri}, database={settings.neo4j.database}")
    
    # Different ways to connect to Neo4j
    connection_params = [
        # Default from settings
        {
            "uri": settings.neo4j.uri,
            "username": settings.neo4j.username,
            "password": settings.neo4j.password.get_secret_value(),
            "database": settings.neo4j.database,
        },
        # Container hostname connection
        {
            "uri": "bolt://neo4j:7687",
            "username": "neo4j",
            "password": "password",
            "database": "neo4j",
        },
        # Localhost connection (for main instance)
        {
            "uri": "bolt://localhost:7689",  # Port from docker-compose.yml
            "username": "neo4j",
            "password": "password",
            "database": "neo4j",
        },
        # Localhost test connection
        {
            "uri": "bolt://localhost:7688",  # Port from docker-compose.test.yml
            "username": "neo4j",
            "password": "password",
            "database": "testdb",
        }
    ]
    
    # Try each connection configuration until one works
    for i, params in enumerate(connection_params):
        try:
            logger.info(f"Trying Neo4j connection {i+1}/{len(connection_params)}: {params['uri']}")
            neo4j = Neo4jConnector(**params)
            
            # Test the connection with a simple query
            test_result = neo4j.execute_query("MATCH (n) RETURN count(n) as count LIMIT 1")
            logger.info(f"Neo4j connection successful: {test_result}")
            
            # If we get here, the connection is working
            break
        except Exception as e:
            logger.warning(f"Neo4j connection {i+1} failed: {e}")
            errors.append(f"Connection {i+1} ({params['uri']}): {e}")
            if neo4j:
                try:
                    neo4j.close()
                except:
                    pass
            neo4j = None
    
    # Check if a working connection was found
    if not neo4j:
        error_details = "\n".join(errors)
        logger.error(f"All Neo4j connection attempts failed:\n{error_details}")
        return {
            "status": StepStatus.FAILED,
            "error": f"Neo4j connection error: No working connection found.\n{error_details}",
            "job_id": job_id,
        }

    # Process the filesystem
    try:
        file_count = 0
        dir_count = 0
        
        # Log depth setting but don't limit it
        logger.info(f"Using repository traversal depth: {max_depth} (unlimited if None)")

        # Debug info for neo4j
        with open("/tmp/neo4j_debug.log", "w") as f:
            f.write(f"Repository path: {repository_path}\n")
            f.write(f"Neo4j URI: {settings.neo4j.uri}\n")
            f.write(f"Neo4j database: {settings.neo4j.database}\n")
            f.write(f"Max depth: {max_depth}\n")
            f.write(f"Connection test...\n")
            
            try:
                # Simple test query
                test_query = "MATCH (n) RETURN count(n) as count"
                test_result = neo4j.execute_query(test_query)
                f.write(f"Test query result: {test_result}\n")
            except Exception as e:
                f.write(f"Test query failed: {str(e)}\n")

        # Create repository node with MERGE to handle existing nodes
        repo_name = os.path.basename(repository_path)
        repo_properties = {
            "name": repo_name,
            "path": repository_path,
        }
        
        # Use direct query with MERGE to avoid constraint violations
        repo_query = """
        MERGE (r:Repository {path: $props.path})
        SET r.name = $props.name
        RETURN r
        """
        repo_result = neo4j.execute_query(
            repo_query, params={"props": repo_properties}, write=True
        )
        repo_node = repo_result[0]["r"] if repo_result else None
        
        logger.info(f"Repository node created or updated: {repo_node}")

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
                    # Use MERGE for directory nodes to handle existing nodes
                    dir_properties = {
                        "name": os.path.basename(current_dir),
                        "path": rel_dir_path,
                    }
                    dir_query = """
                    MERGE (d:Directory {path: $props.path})
                    SET d.name = $props.name
                    RETURN d
                    """
                    dir_result = neo4j.execute_query(
                        dir_query, params={"props": dir_properties}, write=True
                    )
                    dir_node = dir_result[0]["d"] if dir_result else None
                    print(f"  Directory node created or updated: {dir_node}")
                except Exception as e:
                    print(f"  Error creating directory node: {e}")
                    raise

                # Link to parent directory using MERGE for relationship
                parent_path = os.path.dirname(rel_dir_path)
                if parent_path == "":
                    # Parent is the repo
                    rel_query = """
                    MATCH (r:Repository {path: $repo_path})
                    MATCH (d:Directory {path: $dir_path})
                    MERGE (r)-[rel:CONTAINS]->(d)
                    RETURN rel
                    """
                    neo4j.execute_query(
                        rel_query,
                        params={
                            "repo_path": repository_path,
                            "dir_path": rel_dir_path
                        },
                        write=True
                    )
                else:
                    # Parent is another directory 
                    rel_query = """
                    MATCH (p:Directory {path: $parent_path})
                    MATCH (d:Directory {path: $dir_path})
                    MERGE (p)-[rel:CONTAINS]->(d)
                    RETURN rel
                    """
                    neo4j.execute_query(
                        rel_query,
                        params={
                            "parent_path": parent_path,
                            "dir_path": rel_dir_path
                        },
                        write=True
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
                    # Use MERGE for file nodes to handle existing nodes
                    file_properties = {
                        "name": file,
                        "path": file_path,
                        "extension": os.path.splitext(file)[1].lstrip(".") or None,
                        "size": os.path.getsize(os.path.join(current_dir, file)),
                        "modified": os.path.getmtime(
                            os.path.join(current_dir, file)
                        ),
                    }
                    file_query = """
                    MERGE (f:File {path: $props.path})
                    SET f.name = $props.name,
                        f.extension = $props.extension,
                        f.size = $props.size,
                        f.modified = $props.modified
                    RETURN f
                    """
                    file_result = neo4j.execute_query(
                        file_query, params={"props": file_properties}, write=True
                    )
                    file_node = file_result[0]["f"] if file_result else None
                    print(f"  File node created or updated: {file_node}")
                except Exception as e:
                    print(f"  Error creating file node: {e}")
                    raise

                # Link to directory using MERGE for relationship
                if rel_dir_path == ".":
                    # Parent is the repo
                    rel_query = """
                    MATCH (r:Repository {path: $repo_path})
                    MATCH (f:File {path: $file_path})
                    MERGE (r)-[rel:CONTAINS]->(f)
                    RETURN rel
                    """
                    neo4j.execute_query(
                        rel_query,
                        params={
                            "repo_path": repository_path,
                            "file_path": file_path
                        },
                        write=True
                    )
                else:
                    # Parent is a directory
                    rel_query = """
                    MATCH (d:Directory {path: $dir_path})
                    MATCH (f:File {path: $file_path})
                    MERGE (d)-[rel:CONTAINS]->(f)
                    RETURN rel
                    """
                    neo4j.execute_query(
                        rel_query,
                        params={
                            "dir_path": rel_dir_path,
                            "file_path": file_path
                        },
                        write=True
                    )

                file_count += 1

                # Report progress more frequently (every 10 files)
                if file_count % 10 == 0:
                    logger.info(f"Progress: {file_count} files, {dir_count} directories")
                    try:
                        self.update_state(
                            state="PROGRESS",
                            meta={
                                "progress": None,  # Can't know total
                                "message": f"Processed {file_count} files, {dir_count} directories",
                                "file_count": file_count,
                                "dir_count": dir_count,
                            },
                        )
                    except Exception as e:
                        logger.error(f"Error updating progress state: {e}")
                        
                # Add progress tracking for directories too
                if dir_count % 10 == 0 and dir_count > 0:
                    logger.info(f"Directory progress: {dir_count} directories processed")

        # Record end time
        end_time = time.time()
        duration = end_time - start_time

        # Create a processing record with MERGE
        record_query = """
        MERGE (p:ProcessingRecord {step: $props.step, job_id: $props.job_id})
        SET p.repository = $props.repository,
            p.timestamp = $props.timestamp,
            p.duration = $props.duration,
            p.file_count = $props.file_count,
            p.dir_count = $props.dir_count
        RETURN p
        """
        neo4j.execute_query(
            record_query,
            params={
                "props": {
                    "step": "filesystem",
                    "job_id": job_id,
                    "repository": repo_name,
                    "timestamp": time.time(),
                    "duration": duration,
                    "file_count": file_count,
                    "dir_count": dir_count,
                }
            },
            write=True
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
