import threading
import time
import uuid
from typing import Any

from codestory.graphdb.neo4j_connector import Neo4jConnector
from codestory.ingestion_pipeline.step import PipelineStep, StepStatus


class TestPipelineManager:
    """A test implementation of PipelineManager that runs steps directly without Celery."""

    def __init__(self, neo4j_connector: Neo4jConnector):
        self.neo4j_connector = neo4j_connector
        self.job_id = str(uuid.uuid4())
        self.steps_status = {}
        self.steps_results = {}
        self.steps_errors = {}
        self.dependency_graph = {}
        self._step_instances = {}
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._job_complete = threading.Event()

    def register_step(self, step: PipelineStep, dependencies: list[PipelineStep] | None = None) -> None:
        """Register a step with the pipeline manager.

        Args:
            step: The step to register
            dependencies: Optional list of steps that this step depends on
        """
        with self._lock:
            step_name = self._get_step_name(step)
            self.steps_status[step_name] = "pending"
            self.dependency_graph[step_name] = [self._get_step_name(d) for d in dependencies] if dependencies else []
            self._step_instances[step_name] = step

    def start_job(self, parameters: dict[str, Any]) -> str:
        """Start a new job with the given parameters.
        
        Args:
            parameters: Job parameters
            
        Returns:
            job_id: The ID of the new job
        """
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("A job is already running")
            
            self.job_parameters = parameters
            self.steps_status = dict.fromkeys(self.dependency_graph, "pending")
            self.steps_results = {}
            self.steps_errors = {}
            self._job_complete.clear()
            self._stop_event.clear()
            
            self._thread = threading.Thread(target=self._run_pipeline)
            self._thread.daemon = True
            self._thread.start()
            
            return self.job_id

    def _run_pipeline(self) -> None:
        """Run the pipeline steps in dependency order."""
        try:
            remaining_steps = set(self.dependency_graph.keys())
            completed_steps: set[str] = set()

            while remaining_steps and not self._stop_event.is_set():
                # Find steps that can be run (all dependencies satisfied)
                runnable_steps = [
                    step for step in remaining_steps
                    if set(self.dependency_graph[step]).issubset(completed_steps)
                ]

                if not runnable_steps:
                    # We have steps but none can run - dependency cycle or missing dependencies
                    with self._lock:
                        for step in remaining_steps:
                            self.steps_status[step] = "failed"
                            self.steps_errors[step] = "Dependency cycle or missing dependencies"
                    break

                # Run each step that's ready
                for step_name in runnable_steps:
                    with self._lock:
                        self.steps_status[step_name] = "running"

                    try:
                        # Find the actual step instance by name
                        step_instance = self._get_step_instance(step_name)
                        if not step_instance:
                            raise ValueError(f"Step {step_name} not found")

                        # Execute the step - call the actual run method
                        print(f"Running step {step_name} using parameters: {self.job_parameters}")
                        job_id = step_instance.run(
                            repository_path=self.job_parameters["repo_path"],
                            **self.job_parameters
                        )

                        # Wait for the step to complete
                        max_wait = 60  # seconds
                        for _ in range(max_wait):
                            status = step_instance.status(job_id)
                            if status["status"] in [StepStatus.COMPLETED, StepStatus.FAILED]:
                                break
                            time.sleep(1)

                        # Check final status
                        if status["status"] == StepStatus.COMPLETED:
                            with self._lock:
                                self.steps_status[step_name] = "completed"
                                self.steps_results[step_name] = status.get("result", {})
                                completed_steps.add(step_name)
                                remaining_steps.remove(step_name)
                        else:
                            raise RuntimeError(f"Step {step_name} failed: {status.get('error', 'Unknown error')}")

                    except Exception as e:
                        print(f"Error running step {step_name}: {e}")
                        with self._lock:
                            self.steps_status[step_name] = "failed"
                            self.steps_errors[step_name] = str(e)
                            remaining_steps.remove(step_name)

                            # Mark all dependent steps as failed
                            self._propagate_failure(step_name, remaining_steps, str(e))

                # Avoid tight loop
                time.sleep(0.1)
                
            # All steps completed or stopped
            self._job_complete.set()
            
        except Exception as e:
            # Global exception in pipeline execution
            with self._lock:
                for step in self.dependency_graph:
                    if step not in completed_steps:
                        self.steps_status[step] = "failed"
                        self.steps_errors[step] = f"Pipeline error: {e!s}"
            self._job_complete.set()

    def _propagate_failure(self, failed_step: str, remaining_steps: set[str], error: str) -> None:
        """Mark all steps that depend on the failed step as failed."""
        dependent_steps = [
            step for step in remaining_steps
            if failed_step in self.dependency_graph[step]
        ]

        for step in dependent_steps:
            self.steps_status[step] = "failed"
            self.steps_errors[step] = f"Dependency '{failed_step}' failed: {error}"
            remaining_steps.remove(step)

            # Recursively propagate failure
            self._propagate_failure(step, remaining_steps,
                                   f"Dependency chain failure from '{failed_step}'")

    def _get_step_name(self, step: PipelineStep) -> str:
        """Get a consistent name for a step instance."""
        # Use class name as the step name
        return step.__class__.__name__

    def _get_step_instance(self, step_name: str) -> PipelineStep | None:
        """Find the step instance by name from the registered steps."""
        with self._lock:
            # First check if we already have an instance
            if step_name in self._step_instances:
                return self._step_instances[step_name]

            # Otherwise create a new instance from the registered step classes
            for step_cls in self._registered_steps:
                if step_cls.__name__ == step_name:
                    instance = step_cls()
                    self._step_instances[step_name] = instance
                    return instance

        return None

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of a job.
        
        Args:
            job_id: The job ID to check
            
        Returns:
            status: Job status dictionary
        """
        if job_id != self.job_id:
            return {"status": "not_found"}
        
        with self._lock:
            all_completed = all(
                status == "completed" for status in self.steps_status.values()
            )
            any_failed = any(
                status == "failed" for status in self.steps_status.values()
            )
            
            if any_failed:
                job_status = "failed"
            elif all_completed:
                job_status = "completed"
            else:
                job_status = "running"
                
            return {
                "job_id": self.job_id,
                "status": job_status,
                "steps": {
                    step: {
                        "status": self.steps_status.get(step, "unknown"),
                        "result": self.steps_results.get(step),
                        "error": self.steps_errors.get(step)
                    }
                    for step in self.dependency_graph
                }
            }

    def wait_for_job(self, job_id: str, timeout: float | None = None) -> bool:
        """Wait for a job to complete.
        
        Args:
            job_id: The job ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if the job completed, False if it timed out
        """
        if job_id != self.job_id:
            return False
        
        return self._job_complete.wait(timeout)

    def stop_job(self, job_id: str) -> bool:
        """Stop a running job.
        
        Args:
            job_id: The job ID to stop
            
        Returns:
            bool: True if the job was stopped, False otherwise
        """
        if job_id != self.job_id:
            return False
        
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        return True

    @property
    def _registered_steps(self) -> list[type[PipelineStep]]:
        """Return all registered step classes.

        This should be implemented by subclasses to return all step classes
        relevant to the test.
        """
        raise NotImplementedError(
            "Subclasses must implement _registered_steps to return relevant step classes"
        )