"""Step interface definition for ingestion pipeline plugins.

This module defines the base interface that all ingestion pipeline steps must implement.
"""
import abc
import uuid
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """Status values for pipeline steps."""
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    STOPPED = 'STOPPED'
    CANCELLED = 'CANCELLED'

class PipelineStep(abc.ABC):
    """Base interface for all ingestion pipeline workflow steps.

    All workflow steps in the ingestion pipeline must implement this interface.
    Each step is responsible for a specific part of the ingestion process,
    such as parsing code, analyzing files, or generating summaries.
    """

    @abc.abstractmethod
    def run(self: Any, repository_path: str, **config: Any) -> str:
        """Run the workflow step.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters for the step

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If the step fails to run
        """
        pass

    @abc.abstractmethod
    def status(self: Any, job_id: str) -> dict[str, Any]:
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
        pass

    @abc.abstractmethod
    def stop(self: Any, job_id: str) -> dict[str, Any]:
        """Stop a running job.

        Args:
            job_id: Identifier for the job

        Returns:
            Dict[str, Any]: Status information (same format as status method)

        Raises:
            ValueError: If the job ID is invalid or not found
            Exception: If the job cannot be stopped
        """
        pass

    @abc.abstractmethod
    def cancel(self: Any, job_id: str) -> dict[str, Any]:
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
        pass

    @abc.abstractmethod
    def ingestion_update(self: Any, repository_path: str, **config: Any) -> str:
        """Update the graph with the results of this step only.

        This method allows running just this step without triggering
        the entire pipeline, useful for incremental updates.

        Args:
            repository_path: Path to the repository to process
            **config: Additional configuration parameters for the step

        Returns:
            str: Job ID that can be used to check the status

        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If the step fails to run
            NotImplementedError: If the step does not support incremental updates
        """
        pass

def generate_job_id() -> str:
    """Generate a unique job ID for tracking pipeline steps.

    Returns:
        str: A unique identifier in the format 'step-{uuid}'
    """
    return f'job-{uuid.uuid4()}'