"""Blarify workflow step implementation.

This module implements the BlarifyStep class, which runs Blarify to parse code
and store AST and symbol bindings in Neo4j.
"""

import logging
import os
import time
import uuid
from typing import Any

import docker
from celery import current_app, shared_task
from celery.app.control import Control
from celery.result import AsyncResult
from docker.errors import DockerException

from codestory.config.settings import get_settings
from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus

# Set up logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_IMAGE = "blarapp/blarify:latest"
DEFAULT_TIMEOUT = 3600  # 1 hour
DEFAULT_CONTAINER_NAME_PREFIX = "codestory-blarify-"
WORK_DIR = "/workspace"


class BlarifyStep(PipelineStep):
    """Workflow step that runs Blarify to parse code and store AST in Neo4j.

    This step runs the Blarify tool in a Docker container to analyze the code
    structure and store the results directly in the Neo4j database.
    """

    def __init__(self, docker_image: str | None = None, timeout: int | None = None):
        """Initialize the Blarify step.

        Args:
            docker_image: Optional custom Docker image for Blarify
            timeout: Optional timeout in seconds for the Blarify process
        """
        self.settings = get_settings()
        self.image = docker_image or DEFAULT_IMAGE
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.active_jobs: dict[str, dict[str, Any]] = {}

        # Try to initialize Docker client
        try:
            self.docker_client = docker.from_env()
            # Test Docker connection
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.warning(
                f"Docker client initialization failed: {e}. Will use Celery task."
            )
            self.docker_client = None

    def run(self, repository_path: str, **config: Any) -> str:
        """Run the Blarify step.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters
                - ignore_patterns: List of patterns to ignore
                - docker_image: Override the default Docker image
                - timeout: Override the default timeout

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If the repository path is invalid
        """
        # Validate repository path
        if not os.path.isdir(repository_path):
            raise ValueError(
                f"Repository path is not a valid directory: {repository_path}"
            )

        # Generate job ID
        job_id = f"blarify-{uuid.uuid4()}"

        # Extract configuration
        ignore_patterns = config.get("ignore_patterns", [])
        docker_image = config.get("docker_image", self.image)
        timeout = config.get("timeout", self.timeout)

        # Start the Celery task

        # Get the registered task to support task_always_eager in test environments
        if "codestory_blarify.step.run_blarify" in current_app.tasks:
            # Direct task lookup works better with task_always_eager
            task = current_app.tasks["codestory_blarify.step.run_blarify"].apply_async(
                kwargs={
                    "repository_path": repository_path,
                    "job_id": job_id,
                    "ignore_patterns": ignore_patterns,
                    "docker_image": docker_image,
                    "timeout": timeout,
                    "config": config,
                }
            )
            logger.debug("Using apply_async with registered task")
        else:
            # Fallback to send_task if the task isn't registered
            # This avoids the task_always_eager warning but works in production
            task = current_app.send_task(
                "codestory_blarify.step.run_blarify",
                kwargs={
                    "repository_path": repository_path,
                    "job_id": job_id,
                    "ignore_patterns": ignore_patterns,
                    "docker_image": docker_image,
                    "timeout": timeout,
                    "config": config,
                },
            )
            logger.debug("Using send_task with fully qualified task name")

        # Store job information
        self.active_jobs[job_id] = {
            "task_id": task.id,
            "repository_path": repository_path,
            "start_time": time.time(),
            "status": StepStatus.RUNNING,
            "config": config,
        }

        logger.info(f"Started Blarify job {job_id} for repository: {repository_path}")

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
        # First check if we have internal status for this job
        if job_id in self.active_jobs:
            job_info = self.active_jobs[job_id]
            task_id = job_info["task_id"]

            # If our internal status is STOPPED or CANCELLED, prioritize that over Celery's status
            # This fixes a race condition where the job was stopped but Celery hasn't updated yet
            if job_info.get("status") in [StepStatus.STOPPED, StepStatus.CANCELLED]:
                logger.debug(
                    f"Job {job_id} has internal status {job_info['status']}, using that over Celery status"
                )
                return {
                    "status": job_info["status"],
                    "message": f"Job {job_id} is {job_info['status']}",
                    "job_id": job_id,
                }

            # Check Docker container status for running jobs in CI environment
            # This helps detect if Docker containers are actually still running
            if (
                os.environ.get("CI") == "true"
                and job_info.get("status") == StepStatus.RUNNING
                and self.docker_client
            ):
                container_name = f"{DEFAULT_CONTAINER_NAME_PREFIX}{job_id}"
                try:
                    containers = self.docker_client.containers.list(
                        filters={"name": container_name}
                    )
                    if not containers:
                        # Container is gone but job status wasn't updated
                        logger.info(
                            f"Container {container_name} is not running, updating job status to COMPLETED"
                        )
                        job_info["status"] = StepStatus.COMPLETED
                        job_info["end_time"] = time.time()
                        return {
                            "status": StepStatus.COMPLETED,
                            "message": f"Job {job_id} is completed (container is not running)",
                            "job_id": job_id,
                        }
                except Exception as e:
                    # If we can't check container status, log and continue
                    logger.warning(f"Error checking container status: {e}")

            # Fall through to Celery status check with task_id
            from celery.result import AsyncResult

            result = AsyncResult(task_id)

            # Check if it's REVOKED - this means the job was stopped
            if result.state == "REVOKED":
                logger.debug(f"Task {task_id} is REVOKED, returning STOPPED status")
                # Update our internal status too
                job_info["status"] = StepStatus.STOPPED
                return {
                    "status": StepStatus.STOPPED,
                    "message": f"Job {job_id} has been stopped",
                    "job_id": job_id,
                }

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

        # No internal tracking, check if this is a task ID

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
                    "result": result.result,  # Fixed: Use result directly instead of blocking get()
                }
            elif result.state == "FAILURE":
                return {
                    "status": StepStatus.FAILED,
                    "message": "Task failed",
                    "error": str(result.result),
                }
            elif result.state == "REVOKED":
                return {
                    "status": StepStatus.STOPPED,
                    "message": "Task has been stopped",
                }
            else:
                return {
                    "status": StepStatus.RUNNING,
                    "message": f"Task is in state: {result.state}",
                    "info": result.info,
                }
        except Exception:
            raise ValueError(f"Invalid job ID: {job_id}") from None

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

        # Use the control interface from the current app
        control = Control(current_app)
        control.revoke(task_id, terminate=True)

        # Try to stop the Docker container if running
        container_name = f"{DEFAULT_CONTAINER_NAME_PREFIX}{job_id}"
        container_stopped = False
        if self.docker_client:
            try:
                for container in self.docker_client.containers.list():
                    if container.name == container_name:
                        container.stop(timeout=10)
                        logger.info(f"Container {container_name} stopped")
                        container_stopped = True
                        break
            except DockerException as e:
                logger.warning(f"Failed to stop container {container_name}: {e}")

        # Update job status
        job_info["status"] = StepStatus.STOPPED
        job_info["end_time"] = time.time()

        # Update the task result if possible
        try:
            result = AsyncResult(task_id)
            if result.state in ["PENDING", "STARTED", "PROGRESS"]:
                # Force the task status to be recognized as stopped
                result.revoke(terminate=True)

                # Important: In some CI environments, task status isn't immediately updated
                # We need to force-update our internal tracking
                if hasattr(result, "_cache") and result._cache:
                    result._cache["status"] = "REVOKED"

                logger.info(f"Task {task_id} revoked and status updated")
        except Exception as e:
            logger.warning(f"Error updating task result: {e}")

        # Verify the container is really gone in CI environments
        if os.environ.get("CI") == "true" and self.docker_client and container_stopped:
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Check if any container with the target name still exists
                    containers = self.docker_client.containers.list(
                        all=True, filters={"name": container_name}
                    )
                    if not containers:
                        logger.info(
                            f"Verified container {container_name} is stopped/removed"
                        )
                        break

                    # Container still exists, wait and retry
                    logger.warning(
                        f"Container {container_name} still exists, retrying stop... (attempt {retry_count + 1})"
                    )
                    for container in containers:
                        try:
                            container.stop(timeout=5)
                            container.remove(force=True)
                            logger.info(f"Forcibly removed container {container.name}")
                        except Exception as e:
                            logger.warning(f"Error removing container: {e}")
                except Exception as e:
                    logger.warning(f"Error checking container status: {e}")
                finally:
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(2)  # Wait before retrying

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
        """Update the graph with Blarify for a repository.

        This runs Blarify in incremental mode, which only processes files
        that have changed since the last run.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If the step fails to run
        """
        # Add incremental flag to config to enable incremental mode
        config["incremental"] = True

        # Run the step normally, with incremental mode enabled
        return self.run(repository_path, **config)


@shared_task(bind=True, name="codestory_blarify.step.run_blarify")
def run_blarify(
    self,  # Celery task instance
    repository_path: str,
    job_id: str,
    ignore_patterns: list[str] | None = None,
    docker_image: str | None = None,
    timeout: int | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the Blarify workflow step as a Celery task.

    Args:
        self: Celery task instance
        repository_path: Path to the repository to process
        job_id: ID for the job
        ignore_patterns: List of patterns to ignore
        docker_image: Docker image to use
        timeout: Timeout in seconds
        config: Additional configuration

    Returns:
        Dict with results
    """
    logger.info(f"Starting Blarify task for repository: {repository_path}")

    start_time = time.time()
    ignore_patterns = ignore_patterns or []
    docker_image = docker_image or DEFAULT_IMAGE
    timeout = timeout or DEFAULT_TIMEOUT
    config = config or {}
    incremental = config.get("incremental", False)

    # Get Neo4j connection settings
    settings = get_settings()
    neo4j_uri = settings.neo4j.uri
    neo4j_username = settings.neo4j.username
    neo4j_password = settings.neo4j.password.get_secret_value()
    neo4j_database = settings.neo4j.database

    # Format Neo4j connection string for Blarify
    # Check if host has 'bolt://' prefix and remove it
    host = neo4j_uri.replace("bolt://", "")

    # Handle container networking - if this is a Docker service name, also provide localhost option
    if ":" not in host and not host.startswith(("localhost", "127.0.0.1")):
        # This is likely a Docker service name like 'neo4j', try localhost with mapped port
        neo4j_port = "7689"  # Default mapped port in docker-compose.yml
        alt_host = f"host.docker.internal:{neo4j_port}"
        logger.info(f"Using Docker DNS with host.docker.internal: {alt_host}")
        neo4j_connection = (
            f"neo4j://{neo4j_username}:{neo4j_password}@{alt_host}/{neo4j_database}"
        )
    else:
        # Use the configured host directly
        neo4j_connection = (
            f"neo4j://{neo4j_username}:{neo4j_password}@{host}/{neo4j_database}"
        )

    try:
        # Try to use Docker directly
        client = docker.from_env()

        # Make sure the repository path exists
        if not os.path.isdir(repository_path):
            raise ValueError(
                f"Repository path is not a valid directory: {repository_path}"
            )

        # Check if we're running inside Docker and modify paths accordingly
        container_repository_path = repository_path
        if os.environ.get("CODESTORY_IN_CONTAINER", "false").lower() == "true":
            # We're inside a container, map host path to container path if needed
            if repository_path.startswith("/repositories/"):
                # Already container path, use as is
                pass
            else:
                # Try to map host path to container path
                for host_path, container_path in os.environ.get(
                    "CODESTORY_MOUNT_MAPPINGS", ""
                ).split(";"):
                    if (
                        host_path
                        and container_path
                        and repository_path.startswith(host_path)
                    ):
                        container_repository_path = repository_path.replace(
                            host_path, container_path, 1
                        )
                        logger.info(
                            f"Mapped repository path from {repository_path} to {container_repository_path}"
                        )
                        break

        # Container name for easier identification
        container_name = f"{DEFAULT_CONTAINER_NAME_PREFIX}{job_id}"

        # Check if the repository path is already mounted in any running container
        try:
            running_containers = client.containers.list()
            for container in running_containers:
                if (
                    container.name == "codestory-worker"
                    or container.name == "codestory-service"
                ):
                    logger.info(f"Found existing container: {container.name}")
                    # Check if the repository is mounted in this container
                    container_info = container.attrs
                    for mount in container_info.get("Mounts", []):
                        if (
                            mount["Type"] == "bind"
                            and mount["Source"] == repository_path
                        ):
                            # Repository is already mounted, use the container path
                            container_repository_path = mount["Destination"]
                            logger.info(
                                f"Found existing mount: {repository_path} -> {container_repository_path}"
                            )
                            break
        except Exception as e:
            logger.warning(f"Error checking existing containers: {e}")

        # Update status
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 10.0,
                "message": "Pulling Blarify Docker image...",
            },
        )

        # Pull the Docker image
        try:
            client.images.pull(docker_image)
            logger.info(f"Pulled Docker image: {docker_image}")
        except DockerException as e:
            logger.warning(
                f"Failed to pull Docker image: {e}. Assuming it exists locally."
            )

        # Update status
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 20.0,
                "message": "Starting Blarify container...",
            },
        )

        # Prepare command arguments
        blarify_cmd = ["blarify", "parse", WORK_DIR]

        # Add ignore patterns
        for pattern in ignore_patterns:
            blarify_cmd.extend(["--ignore", pattern])

        # Add incremental flag if needed
        if incremental:
            blarify_cmd.append("--incremental")

        # Add output destination (Neo4j)
        blarify_cmd.extend(["--output", neo4j_connection])

        # Prepare volume mapping
        volumes = {repository_path: {"bind": WORK_DIR, "mode": "ro"}}
        logger.info(f"Using volume mapping: {repository_path} -> {WORK_DIR}")

        # Run the container
        container = client.containers.run(
            image=docker_image,
            name=container_name,
            command=blarify_cmd,
            volumes=volumes,
            detach=True,
            remove=True,
        )

        logger.info(f"Started Blarify container: {container.id}")

        # Monitor container progress with improved timeout handling
        last_log_time = time.time()
        log_interval = 5  # seconds

        # Initialize progress at 20%
        progress = 20.0
        last_activity_time = time.time()
        max_inactivity = (
            300  # Maximum inactivity before considering timeout (5 minutes)
        )

        # Stream logs and track progress
        for log_line in container.logs(stream=True, follow=True):
            try:
                log_line = log_line.decode("utf-8").strip()

                # Reset inactivity timer on any log output
                last_activity_time = time.time()

                # Extract progress information if available
                if "Progress:" in log_line:
                    try:
                        progress_str = (
                            log_line.split("Progress:")[1].strip().split("%")[0]
                        )
                        parsed_progress = float(progress_str)
                        # Scale progress from 20% to 90%
                        progress = 20.0 + (parsed_progress * 0.7)
                    except (ValueError, IndexError):
                        # If parsing fails, increment progress slightly
                        progress = min(progress + 0.5, 90.0)
                elif "Error:" in log_line:
                    logger.error(f"Blarify error: {log_line}")

                # Update progress at regular intervals
                current_time = time.time()
                if current_time - last_log_time > log_interval:
                    last_log_time = current_time
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "progress": progress,
                            "message": f"Processing repository with Blarify... ({progress:.1f}%)",
                        },
                    )
                    logger.debug(f"Blarify progress: {progress:.1f}%")

                # Check for inactivity timeout
                if current_time - last_activity_time > max_inactivity:
                    logger.error(
                        f"Blarify process timed out due to inactivity after {max_inactivity} seconds"
                    )
                    # Attempt to stop the container gracefully
                    try:
                        container.stop(timeout=10)
                        logger.info(
                            f"Stopped container {container.id} due to inactivity timeout"
                        )
                    except Exception as e:
                        logger.warning(f"Error stopping container: {e}")

                    raise TimeoutError(
                        f"Blarify process timed out due to inactivity after {max_inactivity} seconds"
                    )
            except Exception as e:
                logger.warning(f"Error processing log line: {e}")
                # Don't break the loop for parsing errors
                if not isinstance(e, (ValueError, IndexError)):
                    # Break if it's a more serious error like a timeout
                    break

        # Wait for container to finish
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", -1)

        if exit_code != 0:
            error_msg = f"Blarify container exited with code {exit_code}"
            logger.error(error_msg)

            # Try to get error from logs
            try:
                logs = container.logs(tail=100).decode("utf-8")
                error_details = "\n".join(logs.splitlines()[-10:])
                error_msg += f"\nLast log lines:\n{error_details}"
            except Exception:
                pass

            raise RuntimeError(error_msg)

        # Verify results in Neo4j
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 95.0,
                "message": "Verifying results in Neo4j...",
            },
        )

        # Connect to Neo4j and verify data
        try:
            # Try localhost first if in Docker container
            if ":" not in host and not host.startswith(("localhost", "127.0.0.1")):
                try:
                    # Try with localhost
                    localhost_uri = "bolt://localhost:7689"
                    connector = Neo4jConnector(
                        uri=localhost_uri,
                        username=settings.neo4j.username,
                        password=settings.neo4j.password.get_secret_value(),
                        database=settings.neo4j.database,
                    )
                    logger.info(
                        f"Connected to Neo4j using localhost override: {localhost_uri}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to connect to Neo4j using localhost: {e}, falling back to original URI"
                    )
                    connector = Neo4jConnector(
                        uri=settings.neo4j.uri,
                        username=settings.neo4j.username,
                        password=settings.neo4j.password.get_secret_value(),
                        database=settings.neo4j.database,
                    )
            else:
                # Use the original URI
                connector = Neo4jConnector(
                    uri=settings.neo4j.uri,
                    username=settings.neo4j.username,
                    password=settings.neo4j.password.get_secret_value(),
                    database=settings.neo4j.database,
                )

            # Check for AST nodes
            ast_count = connector.execute_query(
                "MATCH (n:AST) RETURN count(n) as count"
            )[0].get("count", 0)

        except Exception as e:
            logger.warning(f"Error connecting to Neo4j for verification: {e}")
            ast_count = 0  # Unable to verify, assume 0

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
            "nodes_processed": ast_count,
            "progress": 100.0,  # Mark as completed
            "status": StepStatus.COMPLETED,
            "message": (
                f"Blarify processed repository and created {ast_count} AST nodes "
                f"in {duration:.2f} seconds"
            ),
        }

        logger.info(f"Blarify task completed: {result['message']}")

        return result
    except (docker.errors.DockerException, TimeoutError) as e:
        logger.error(f"Docker error: {e}")
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
            "error": f"Docker error: {e!s}",
            "message": f"Blarify task failed: {e!s}",
        }
    except Exception as e:
        logger.exception(f"Error in Blarify task: {e}")

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
            "message": f"Blarify task failed: {e!s}",
        }
