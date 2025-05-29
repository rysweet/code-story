"""Celery tasks for the ingestion pipeline.

This module defines the Celery tasks that handle pipeline execution,
including step orchestration and status tracking.
"""

import logging
import time
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

from celery import chain
from celery.result import AsyncResult

from .celery_app import app
from .step import StepStatus
from .utils import record_job_metrics, record_step_metrics

# Set up logging
logger = logging.getLogger(__name__)


@app.task(name="codestory.ingestion_pipeline.tasks.run_step", bind=True)  # type: ignore[misc]
def run_step(
    self: Any,
    repository_path: str,
    step_name: str,
    step_config: dict[str, Any],
    job_id: str | None = None,
) -> dict[str, Any]:
    """Run a single pipeline step.

    Implements resource throttling using ResourceTokenManager.

    This task calls the appropriate plugin to execute a specific pipeline step.
    It uses a task_name_map to route to the fully qualified task name for each step,
    and applies parameter filtering to ensure each step receives only the parameters
    it can handle.

    Args:
        self: Celery task instance
        repository_path: Path to the repository to process
        step_name: Name of the step to run
        step_config: Configuration for the step
        job_id: Optional job ID to use

    Returns:
        Dict[str, Any]: Result information including:
            - step: Name of the step
            - status: StepStatus enum value
            - job_id: ID of the job
            - repository_path: Path to the repository
            - start_time: When the step started
            - end_time: When the step finished
            - duration: Duration in seconds
            - error: Optional error message if the step failed

    Notes:
        This method includes two important mechanisms:

        1. Task routing using fully qualified names:
           The task_name_map maps step names to fully qualified task names
           (e.g., "filesystem" -> "codestory_filesystem.step.process_filesystem")

        2. Parameter filtering:
           Each step may have different parameter requirements. To prevent
           "unexpected keyword argument" errors, this method filters the parameters
           based on the step type before passing them to the actual step task.
    """
    # Record start time
    start_time = time.time()
    logger.info(f"Starting step: {step_name} for repository: {repository_path}")

    # Record metric for step start
    record_step_metrics(step_name, StepStatus.RUNNING)

    # Initialize result
    result = {
        "step": step_name,
        "status": StepStatus.RUNNING,
        "job_id": job_id,
        "repository_path": repository_path,
        "start_time": start_time,
        "task_id": self.request.id,
    }

    import celery

    from codestory.config.settings import get_settings

    from .resource_manager import ResourceTokenManager

    settings = get_settings()
    redis_url = settings.redis.uri
    max_tokens = getattr(settings.ingestion, "resource_max_tokens", 4)

    token_manager = ResourceTokenManager(
        redis_url=redis_url,
        max_tokens=max_tokens,
    )

    acquired = token_manager.acquire_token()
    if not acquired:
        logger.error("Resource throttling: could not acquire resource token for step execution")
        result["status"] = StepStatus.FAILED
        result["error"] = "Resource throttling: could not acquire resource token (system busy)"
        end_time = time.time()
        result["end_time"] = end_time
        result["duration"] = end_time - start_time
        record_step_metrics(step_name, StepStatus.FAILED, end_time - start_time)
        return result

    # Extract retry/back-off config
    max_retries = int(step_config.get("max_retries", 3))
    back_off_seconds = int(step_config.get("back_off_seconds", 10))

    try:
        # This task doesn't directly run the step - instead it dispatches
        # to the appropriate plugin's task which is registered separately
        # Map step name to the fully qualified task name
        task_name_map = {
            "filesystem": "codestory_filesystem.step.process_filesystem",
            "blarify": "codestory_blarify.step.run_blarify",
            "summarizer": "codestory_summarizer.step.run_summarizer",
            "docgrapher": "codestory_docgrapher.step.run_docgrapher",
        }

        # Get the task name from the map or fallback to legacy format
        task_name = task_name_map.get(step_name, f"{step_name}.run")

        # Log what we're trying to do
        logger.debug(f"Dispatching to task: {task_name}")
        logger.debug(f"Available tasks: {[t for t in app.tasks if step_name in t]}")

        # Prepare configuration for the step task - with parameter filtering
        step_config_copy = step_config.copy()

        # Don't add repository_path to kwargs as it's already passed in the task signature
        # This avoids the "got multiple values for argument" error
        if "repository_path" in step_config_copy:
            # If it's already in the config, remove it to avoid conflicts
            logger.warning("Removing duplicate repository_path from step config to avoid conflicts")
            del step_config_copy["repository_path"]

        # Include job_id in kwargs if present
        if "job_id" not in step_config_copy and job_id:
            step_config_copy["job_id"] = job_id

        # Filter out step-specific parameters that are not common to all steps
        # This prevents "unexpected keyword argument" errors when passing step configs
        if step_name == "blarify":
            # Blarify step doesn't use concurrency parameter
            if "concurrency" in step_config_copy:
                logger.debug(
                    "Removing 'concurrency' from blarify step config to avoid parameter mismatch"
                )
                del step_config_copy["concurrency"]

        elif step_name == "summarizer" or step_name == "docgrapher":
            # These steps might have specific parameters that other steps don't accept
            safe_params = ["job_id", "ignore_patterns", "timeout", "incremental"]
            for param in list(step_config_copy.keys()):
                if param not in safe_params and param != step_name + "_specific":
                    logger.debug(
                        f"Removing '{param}' from {step_name} step config to avoid "
                        f"parameter mismatch"
                    )
                    del step_config_copy[param]

        logger.debug(
            f"Sending task {task_name} with args=[repository_path={repository_path}] "
            f"and kwargs={step_config_copy}"
        )

        try:
            # Pass repository_path as the first positional argument
            step_task = app.send_task(
                task_name,
                args=[repository_path],  # Pass repository_path as first arg
                kwargs=step_config_copy,
            )
            logger.debug(f"Task {task_name} sent successfully with ID: {step_task.id}")
        except Exception as e:
            logger.error(f"Error sending task {task_name}: {e}")
            # Retry on transient errors (example: network, resource busy)
            if hasattr(e, "errno") and e.errno in (11, 10060, 110):  # EAGAIN, ETIMEDOUT, ECONNREFUSED
                if self.request.retries < max_retries:
                    logger.warning(
                        f"Transient error in step {step_name}, retrying "
                        f"(attempt {self.request.retries + 1}/{max_retries}) in {back_off_seconds}s"
                    )
                    raise self.retry(
                        countdown=back_off_seconds,
                        max_retries=max_retries,
                        exc=e,
                    ) from e
            # Try to get more detailed error message
            raise Exception(f"Failed to send task {task_name}: {e}") from e

        # FIXED: Don't use .get() inside a task as this is a known anti-pattern
        # Instead, use the AsyncResult to check the task status without blocking
        async_result = AsyncResult(step_task.id, app=app)
        # Poll for completion with a timeout
        timeout = step_config.get("timeout", 1800)  # 30 minutes default timeout
        start_poll = time.time()
        step_result = None

        logger.info(f"Waiting for task {task_name} (id: {step_task.id}) with timeout {timeout}s")
        last_log_time = start_poll
        poll_counter = 0

        while time.time() - start_poll < timeout:
            poll_counter += 1
            current_time = time.time()

            # Collect resource usage
            cpu_percent = None
            memory_mb = None
            if psutil:
                try:
                    p = psutil.Process()
                    cpu_percent = p.cpu_percent(interval=0.0)
                    memory_mb = p.memory_info().rss / 1024 / 1024
                except Exception:
                    cpu_percent = None
                    memory_mb = None

            # Emit progress update every 10 seconds or every 20 polls
            if (current_time - last_log_time > 10 or poll_counter % 20 == 0):
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": None,  # Could estimate based on step state if desired
                        "message": f"Waiting for task {task_name} (elapsed: {current_time - start_poll:.1f}s)",
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb,
                        "step": step_name,
                        "retry_count": self.request.retries,
                    },
                )

            # Check for task revocation/cancellation
            if hasattr(self, "request") and getattr(self.request, "is_revoked", None):
                if self.request.is_revoked():
                    logger.warning(f"Step task {self.request.id} was revoked. Cancelling step execution.")
                    result["status"] = StepStatus.CANCELLED
                    result["error"] = "Step was cancelled by user"
                    end_time = time.time()
                    result["end_time"] = end_time
                    result["duration"] = end_time - start_time
                    result["retry_count"] = self.request.retries
                    record_step_metrics(step_name, StepStatus.CANCELLED, end_time - start_time)
                    logger.info(f"Step cancelled after {end_time - start_time:.2f} seconds")
                    return result

            # Log status every 30 seconds
            if current_time - last_log_time > 30 or poll_counter % 30 == 0:
                logger.info(
                    f"[{poll_counter}] Still waiting for task {task_name} (id: {step_task.id}) - "
                    f"elapsed: {current_time - start_poll:.1f}s"
                )
                last_log_time = current_time

                # Check if task exists
                task_state = None
                try:
                    task_state = async_result.state
                    logger.info(f"Task state: {task_state}")
                except Exception as e:
                    logger.error(f"Error getting task state: {e}")

            if async_result.ready():
                logger.info(f"Task {task_name} is ready after {time.time() - start_poll:.1f}s")
                if async_result.successful():
                    try:
                        step_result = async_result.result
                        logger.info(f"Task completed successfully: {type(step_result)}")
                        break
                    except Exception as e:
                        logger.error(f"Error getting result: {e}")
                        # Retry on transient error in result retrieval
                        if hasattr(e, "errno") and e.errno in (11, 10060, 110):
                            if self.request.retries < max_retries:
                                logger.warning(
                                    f"Transient error retrieving result for {step_name}, retrying "
                                    f"(attempt {self.request.retries + 1}/{max_retries}) in {back_off_seconds}s"
                                )
                                raise self.retry(
                                    countdown=back_off_seconds,
                                    max_retries=max_retries,
                                    exc=e,
                                ) from e
                        raise Exception(f"Error retrieving task result: {e}") from e
                else:
                    error_info = "Unknown error"
                    try:
                        error_info = async_result.result
                    except Exception as e:
                        error_info = f"Could not retrieve error info: {e}"
                    logger.error(f"Task failed: {error_info}")
                    # Retry on transient error in step execution
                    if hasattr(error_info, "errno") and error_info.errno in (11, 10060, 110):
                        if self.request.retries < max_retries:
                            logger.warning(
                                f"Transient error in step {step_name}, retrying "
                                f"(attempt {self.request.retries + 1}/{max_retries}) in {back_off_seconds}s"
                            )
                            raise self.retry(
                                countdown=back_off_seconds,
                                max_retries=max_retries,
                                exc=error_info,
                            )
                    raise Exception(f"Step task failed: {error_info}")
            time.sleep(1)  # Wait before checking again

        if step_result is None:
            logger.error(f"Task {task_name} (id: {step_task.id}) timed out after {timeout}s")
            # Retry on timeout if not exceeded max_retries
            if self.request.retries < max_retries:
                logger.warning(
                    f"Step {step_name} timed out, retrying "
                    f"(attempt {self.request.retries + 1}/{max_retries}) in {back_off_seconds}s"
                )
                raise self.retry(
                    countdown=back_off_seconds,
                    max_retries=max_retries,
                    exc=TimeoutError(f"Step task timed out after {timeout} seconds"),
                )
            raise Exception(f"Step task timed out after {timeout} seconds")

        # Update result with step's result
        if isinstance(step_result, dict):
            # If the step returns a dictionary, merge it with our result
            result.update(
                {
                    k: v
                    for k, v in step_result.items()
                    if k not in ["step", "repository_path", "start_time", "task_id"]
                }
            )
        else:
            # If the step just returns a job ID
            result["job_id"] = step_result

        # Mark as completed
        result["status"] = StepStatus.COMPLETED
        result["retry_count"] = self.request.retries
        result["last_error"] = None

    except Exception as e:
        # Log the error
        logger.exception(f"Error running step {step_name}: {e}")

        # Update result with error information
        result["status"] = StepStatus.FAILED
        result["error"] = str(e)
        result["retry_count"] = self.request.retries
        result["last_error"] = str(e)

    finally:
        # Always release the token if it was acquired
        try:
            token_manager.release_token()
        except Exception as e:
            logger.error(f"Error releasing resource token: {e}")

    # Record end time and duration
    end_time = time.time()
    duration = end_time - start_time
    result["end_time"] = end_time
    result["duration"] = duration

    # Record metrics
    record_step_metrics(step_name, StepStatus(result["status"]), duration)

    # Log completion
    logger.info(
        f"Completed step {step_name} with status {result['status']} in {duration:.2f} seconds"
    )

    return result


@app.task(name="codestory.ingestion_pipeline.tasks.orchestrate_pipeline", bind=True)  # type: ignore[misc]
def orchestrate_pipeline(
    self: Any, repository_path: str, step_configs: list[dict[str, Any]], job_id: str
) -> dict[str, Any]:
    """Orchestrate the execution of the entire pipeline.

    This task creates a chain of steps to be executed in order,
    tracks their progress, and returns the overall result.

    Args:
        self: Celery task instance
        repository_path: Path to the repository to process
        step_configs: List of step configurations with name and parameters
        job_id: ID for the overall pipeline job

    Returns:
        Dict[str, Any]: Result information including:
            - job_id: ID of the overall job
            - status: StepStatus enum value
            - repository_path: Path to the repository
            - steps: List of step results
            - start_time: When the pipeline started
            - end_time: When the pipeline finished
            - duration: Duration in seconds
            - error: Optional error message if the pipeline failed
    """
    # Record start time
    start_time = time.time()
    logger.info(f"Starting pipeline for repository: {repository_path} (job_id: {job_id})")

    # Record metric for job start
    record_job_metrics(StepStatus.RUNNING)

    # Initialize result
    result = {
        "job_id": job_id,
        "status": StepStatus.RUNNING,
        "repository_path": repository_path,
        "steps": [],
        "start_time": start_time,
    }

    try:
        # Create a chain of step tasks
        workflow: list[Any] = []

        # Add each step to the workflow
        for step_config in step_configs:
            step_name = step_config.pop("name")
            # When creating signatures, we need to be careful about argument passing
            # to avoid 'got multiple values for argument' errors
            # Create a copy of step_config and explicitly set the job_id
            step_config_copy = step_config.copy()
            # Make sure job_id is included in every step
            step_config_copy["job_id"] = job_id

            workflow.append(
                run_step.s(
                    step_name=step_name,
                    step_config=step_config_copy,
                    job_id=job_id,  # Pass job_id explicitly as kwarg
                    # Do not include repository_path here, will be passed as arg
                )
            )

        # Run the workflow as a chain (sequential execution)
        # Prepare arguments for the chain
        try:
            logger.info(f"Sending args=[{repository_path}] to chain with {len(workflow)} steps")

            # The first argument to the chain is the repository_path
            # This will be passed to the first task in the chain
            chain_result = chain(*workflow).apply_async(args=[repository_path])

            logger.info(f"Chain started with ID: {chain_result.id}")
        except Exception as e:
            logger.error(f"Error starting chain: {e}")
            # Try to get more detailed error message
            from celery.exceptions import CeleryError

            if isinstance(e, CeleryError):
                logger.error(f"Celery error details: {e.args}")
            raise

        # FIXED: Don't use .get() inside a task as this is a known anti-pattern
        # Instead, use polling to check for completion
        async_result = AsyncResult(chain_result.id, app=app)
        timeout = 1800  # 30 minutes default timeout for the entire pipeline
        start_poll = time.time()
        all_results = None

        logger.info(f"Waiting for chain (id: {chain_result.id}) with timeout {timeout}s")
        last_log_time = start_poll
        poll_counter = 0

        import celery
        while time.time() - start_poll < timeout:
            poll_counter += 1
            current_time = time.time()

            # Check for task revocation/cancellation
            if hasattr(self, "request") and getattr(self.request, "is_revoked", None):
                if self.request.is_revoked():
                    logger.warning(f"Pipeline task {self.request.id} was revoked. Cancelling pipeline execution.")
                    result["status"] = StepStatus.CANCELLED
                    result["error"] = "Pipeline was cancelled by user"
                    end_time = time.time()
                    result["end_time"] = end_time
                    result["duration"] = end_time - start_time
                    record_job_metrics(StepStatus.CANCELLED)
                    logger.info(f"Pipeline cancelled after {end_time - start_time:.2f} seconds")
                    return result

            # Log status every 30 seconds or each 15 polls
            if current_time - last_log_time > 30 or poll_counter % 15 == 0:
                logger.info(
                    f"[{poll_counter}] Still waiting for chain (id: {chain_result.id}) - "
                    f"elapsed: {current_time - start_poll:.1f}s"
                )
                last_log_time = current_time

                # Collect resource usage
                cpu_percent = None
                memory_mb = None
                if psutil:
                    try:
                        p = psutil.Process()
                        cpu_percent = p.cpu_percent(interval=0.0)
                        memory_mb = p.memory_info().rss / 1024 / 1024
                    except Exception:
                        cpu_percent = None
                        memory_mb = None

                # Emit progress update
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": None,  # Could estimate based on steps completed
                        "message": f"Waiting for pipeline chain (elapsed: {current_time - start_poll:.1f}s)",
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb,
                        "step": "pipeline",
                    },
                )

                # Check current state
                try:
                    chain_state = async_result.state
                    logger.info(f"Chain state: {chain_state}")
                except Exception as e:
                    logger.error(f"Error getting chain state: {e}")

            if async_result.ready():
                logger.info(f"Chain is ready after {time.time() - start_poll:.1f}s")
                if async_result.successful():
                    try:
                        all_results = async_result.result
                        logger.info(f"Chain completed successfully: {type(all_results)}")
                        break
                    except Exception as e:
                        logger.error(f"Error getting chain result: {e}")
                        raise Exception(f"Error retrieving chain result: {e}") from e
                else:
                    error_info = "Unknown error"
                    try:
                        error_info = async_result.result
                    except Exception as e:
                        error_info = f"Could not retrieve error info: {e}"
                    logger.error(f"Chain failed: {error_info}")
                    raise Exception(f"Chain execution failed: {error_info}")

            time.sleep(2)  # Check less frequently for longer-running pipeline

        if all_results is None:
            logger.error(f"Chain (id: {chain_result.id}) timed out after {timeout}s")
            raise Exception(f"Pipeline timed out after {timeout} seconds")

        # If there's only one step, wrap it in a list
        if not isinstance(all_results, list):
            all_results = [all_results]

        # Update the result with step results
        result["steps"] = all_results

        # Check if any step failed
        failed_steps = [s for s in all_results if s.get("status") == StepStatus.FAILED]
        if failed_steps:
            # Mark the job as failed if any step failed
            result["status"] = StepStatus.FAILED
            result[
                "error"
            ] = f"{len(failed_steps)} steps failed: {', '.join(s['step'] for s in failed_steps)}"
        else:
            # Mark as completed if all steps succeeded
            result["status"] = StepStatus.COMPLETED

    except Exception as e:
        # Log the error
        logger.exception(f"Error orchestrating pipeline: {e}")

        # Update result with error information
        result["status"] = StepStatus.FAILED
        result["error"] = str(e)

    # Record end time and duration
    end_time = time.time()
    duration = end_time - start_time
    result["end_time"] = end_time
    result["duration"] = duration

    # Record metrics
    record_job_metrics(StepStatus(result["status"]))

    # Log completion
    logger.info(f"Completed pipeline with status {result['status']} in {duration:.2f} seconds")

    return result


@app.task(name="codestory.ingestion_pipeline.tasks.get_job_status", bind=True)  # type: ignore[misc]
def get_job_status(self: Any, task_id: str) -> dict[str, Any]:
    """Get the status of a running job.

    Args:
        self: Celery task instance
        task_id: Celery task ID to check

    Returns:
        Dict[str, Any]: Status information
    """
    try:
        result = AsyncResult(task_id, app=app)

        if result.ready():
            if result.successful():
                # FIXED: Don't use .get() inside a task
                # Instead, access the result directly through result.result
                return {
                    "status": StepStatus.COMPLETED,
                    "result": result.result,
                }
            else:
                return {
                    "status": StepStatus.FAILED,
                    "error": str(result.result),
                }
        else:
            return {
                "status": StepStatus.RUNNING,
                "info": result.info,
            }
    except Exception as e:
        logger.exception(f"Error checking job status: {e}")
        return {
            "status": StepStatus.FAILED,
            "error": f"Error checking status: {e!s}",
        }


@app.task(name="codestory.ingestion_pipeline.tasks.stop_job", bind=True)  # type: ignore[misc]
def stop_job(self: Any, task_id: str) -> dict[str, Any]:
    """Stop a running job.

    Args:
        self: Celery task instance
        task_id: Celery task ID to stop

    Returns:
        Dict[str, Any]: Status information
    """
    try:
        result = AsyncResult(task_id, app=app)

        if not result.ready():
            # Revoke the task (terminate=True means it will be killed if running)
            app.control.revoke(task_id, terminate=True)
            return {
                "status": StepStatus.STOPPED,
                "message": f"Job {task_id} has been stopped",
            }
        else:
            if result.successful():
                return {
                    "status": StepStatus.COMPLETED,
                    "message": f"Job {task_id} already completed",
                }
            else:
                return {
                    "status": StepStatus.FAILED,
                    "message": f"Job {task_id} already failed",
                    "error": str(result.result),
                }
    except Exception as e:
        logger.exception(f"Error stopping job: {e}")
        return {
            "status": StepStatus.FAILED,
            "error": f"Error stopping job: {e!s}",
        }