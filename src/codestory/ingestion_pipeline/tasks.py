"""Celery tasks for the ingestion pipeline.

This module defines the Celery tasks that handle pipeline execution,
including step orchestration and status tracking.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from celery import chain, group
from celery.result import AsyncResult

from .celery_app import app
from .step import StepStatus
from .utils import record_job_metrics, record_step_metrics

# Set up logging
logger = logging.getLogger(__name__)


@app.task(name="codestory.ingestion_pipeline.tasks.run_step", bind=True)
def run_step(
    self, 
    repository_path: str, 
    step_name: str, 
    step_config: Dict[str, Any],
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Run a single pipeline step.
    
    This task calls the appropriate plugin to execute a specific pipeline step.
    
    Args:
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
    
    try:
        # This task doesn't directly run the step - instead it dispatches
        # to the appropriate plugin's task which is registered separately
        task_name = f"codestory.pipeline.steps.{step_name}.run"
        logger.debug(f"Dispatching to task: {task_name}")
        
        # Call the step's task
        step_task = app.send_task(
            task_name,
            args=[repository_path],
            kwargs=step_config,
        )
        
        # Wait for the step to complete
        step_result = step_task.get()
        
        # Update result with step's result
        if isinstance(step_result, dict):
            # If the step returns a dictionary, merge it with our result
            result.update({
                k: v for k, v in step_result.items() 
                if k not in ["step", "repository_path", "start_time", "task_id"]
            })
        else:
            # If the step just returns a job ID
            result["job_id"] = step_result
            
        # Mark as completed
        result["status"] = StepStatus.COMPLETED
        
    except Exception as e:
        # Log the error
        logger.exception(f"Error running step {step_name}: {e}")
        
        # Update result with error information
        result["status"] = StepStatus.FAILED
        result["error"] = str(e)
    
    # Record end time and duration
    end_time = time.time()
    duration = end_time - start_time
    result["end_time"] = end_time
    result["duration"] = duration
    
    # Record metrics
    record_step_metrics(step_name, StepStatus(result["status"]), duration)
    
    # Log completion
    logger.info(
        f"Completed step {step_name} with status {result['status']} "
        f"in {duration:.2f} seconds"
    )
    
    return result


@app.task(name="codestory.ingestion_pipeline.tasks.orchestrate_pipeline", bind=True)
def orchestrate_pipeline(
    self, 
    repository_path: str, 
    step_configs: List[Dict[str, Any]], 
    job_id: str
) -> Dict[str, Any]:
    """Orchestrate the execution of the entire pipeline.
    
    This task creates a chain of steps to be executed in order,
    tracks their progress, and returns the overall result.
    
    Args:
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
        workflow = []
        
        # Add each step to the workflow
        for step_config in step_configs:
            step_name = step_config.pop("name")
            workflow.append(
                run_step.s(
                    repository_path=repository_path,
                    step_name=step_name,
                    step_config=step_config,
                )
            )
        
        # Run the workflow as a chain (sequential execution)
        chain_result = chain(*workflow).apply_async()
        
        # Wait for the entire chain to complete
        all_results = chain_result.get()
        
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
            result["error"] = f"{len(failed_steps)} steps failed: {', '.join(s['step'] for s in failed_steps)}"
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
    logger.info(
        f"Completed pipeline with status {result['status']} "
        f"in {duration:.2f} seconds"
    )
    
    return result


@app.task(name="codestory.ingestion_pipeline.tasks.get_job_status", bind=True)
def get_job_status(self, task_id: str) -> Dict[str, Any]:
    """Get the status of a running job.
    
    Args:
        task_id: Celery task ID to check
        
    Returns:
        Dict[str, Any]: Status information
    """
    try:
        result = AsyncResult(task_id, app=app)
        
        if result.ready():
            if result.successful():
                return {
                    "status": StepStatus.COMPLETED,
                    "result": result.get(),
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
            "error": f"Error checking status: {str(e)}",
        }


@app.task(name="codestory.ingestion_pipeline.tasks.stop_job", bind=True)
def stop_job(self, task_id: str) -> Dict[str, Any]:
    """Stop a running job.
    
    Args:
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
            "error": f"Error stopping job: {str(e)}",
        }