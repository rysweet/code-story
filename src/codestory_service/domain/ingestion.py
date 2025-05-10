"""Domain models for ingestion pipeline interactions.

This module contains Pydantic models that represent the domain entities
for ingestion pipeline operations.
"""

import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator

from codestory.ingestion_pipeline.step import StepStatus


class JobStatus(str, Enum):
    """Enumeration of job statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
    CANCELLING = "cancelling"


class IngestionSourceType(str, Enum):
    """Enumeration of ingestion source types."""

    LOCAL_PATH = "local_path"
    GIT_URL = "git_url"
    GITHUB_URL = "github_url"
    GITHUB_REPO = "github_repo"


class IngestionRequest(BaseModel):
    """Model for ingestion request payload."""

    source_type: IngestionSourceType = Field(
        ...,
        description="Type of ingestion source",
    )
    source: str = Field(
        ...,
        description="Path or URL to the source code repository",
    )
    branch: Optional[str] = Field(
        None,
        description="Branch to ingest (for Git repositories)",
    )
    steps: Optional[List[str]] = Field(
        None,
        description="Specific steps to run (defaults to all configured steps)",
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional configuration for ingestion",
    )
    options: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional options for ingestion",
    )
    created_by: Optional[str] = Field(
        None,
        description="User or system that created the request",
    )
    description: Optional[str] = Field(
        None,
        description="Description of the ingestion job",
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Tags for categorizing the ingestion job",
    )

    @field_validator("source")
    def source_not_empty(cls, v: str) -> str:
        """Validate that source is not empty.

        Args:
            v: The source path or URL

        Returns:
            The validated source string

        Raises:
            ValueError: If the source is empty
        """
        if not v:
            raise ValueError("Source cannot be empty")
        return v

    @field_validator("source")
    def validate_source(cls, v: str, info) -> str:
        """Validate the source based on source_type.

        Args:
            v: The source path or URL
            info: ValidationInfo object containing data and context

        Returns:
            The validated source

        Raises:
            ValueError: If the source is invalid for the given source_type
        """
        # In Pydantic v2, we need to access the source_type from info.data
        source_type = info.data.get("source_type")

        if source_type == IngestionSourceType.LOCAL_PATH:
            # Local paths should exist
            import os

            if not os.path.exists(v):
                raise ValueError(f"Local path '{v}' does not exist")

        elif source_type in (
            IngestionSourceType.GIT_URL,
            IngestionSourceType.GITHUB_URL,
        ):
            # Git URLs should start with git:// or https://
            if not (
                v.startswith("git://")
                or v.startswith("https://")
                or v.startswith("http://")
                or v.startswith("ssh://")
            ):
                raise ValueError(
                    f"Git URL '{v}' should start with git://, https://, http://, or ssh://"
                )

        elif source_type == IngestionSourceType.GITHUB_REPO:
            # GitHub repo should be in format owner/repo
            if "/" not in v or v.count("/") > 1:
                raise ValueError(f"GitHub repo '{v}' should be in format 'owner/repo'")

        return v

    @model_validator(mode="after")
    def validate_model(self) -> "IngestionRequest":
        """Validate the model as a whole.

        Returns:
            The validated model

        Raises:
            ValueError: If the model is invalid
        """
        # If branch is specified, it should only be for Git sources
        if (
            self.branch is not None
            and self.source_type == IngestionSourceType.LOCAL_PATH
        ):
            raise ValueError("Branch can only be specified for Git repositories")

        return self


class IngestionStarted(BaseModel):
    """Response for a successful ingestion job start."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(JobStatus.RUNNING, description="Initial job status")
    source: str = Field(..., description="Source being ingested")
    started_at: datetime = Field(default_factory=datetime.now, description="Start time")
    steps: List[str] = Field(..., description="Steps to be executed")
    message: Optional[str] = Field(None, description="Status message")
    eta: Optional[int] = Field(None, description="Estimated time of start (unix timestamp)")

    class Config:
        """Model configuration."""

        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }


class StepProgress(BaseModel):
    """Model for step progress information."""

    name: str = Field(..., description="Step name")
    status: StepStatus = Field(..., description="Step status")
    progress: float = Field(..., description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if applicable")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration: Optional[float] = Field(None, description="Duration in seconds")


class IngestionJob(BaseModel):
    """Model for ingestion job details."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Overall job status")
    source: Optional[str] = Field(None, description="Source being ingested")
    source_type: Optional[IngestionSourceType] = Field(
        None, description="Type of ingestion source"
    )
    branch: Optional[str] = Field(None, description="Branch name if applicable")
    progress: float = Field(..., description="Overall progress percentage (0-100)")
    created_at: Optional[int] = Field(None, description="Creation timestamp")
    updated_at: Optional[int] = Field(None, description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    steps: Optional[Dict[str, StepProgress]] = Field(None, description="Progress by step")
    current_step: Optional[str] = Field(None, description="Current step name")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if applicable")
    result: Optional[Any] = Field(None, description="Job result data")

    @model_validator(mode="after")
    def calculate_derived_fields(self) -> "IngestionJob":
        """Calculate duration and overall progress from step data.

        Returns:
            The updated model with calculated fields
        """
        # Calculate duration if both start and completion times are available
        if self.started_at and self.completed_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()
        elif self.started_at and self.status in (
            JobStatus.RUNNING,
            JobStatus.PENDING,
        ):
            # Calculate elapsed time for running jobs
            self.duration = (datetime.now() - self.started_at).total_seconds()

        # Calculate overall progress as weighted average of step progress
        if self.steps and isinstance(self.steps, dict):
            # Only include steps that have started
            active_steps = {
                name: step
                for name, step in self.steps.items()
                if step.status != StepStatus.PENDING
            }

            if active_steps:
                # Simple average for now - could be weighted in the future
                self.progress = sum(
                    step.progress for step in active_steps.values()
                ) / len(active_steps)

            # If all steps are completed, ensure progress is 100%
            if all(step.status == StepStatus.COMPLETED for step in self.steps.values()):
                self.progress = 100.0

            # If any step has failed, set overall status to failed
            if any(step.status == StepStatus.FAILED for step in self.steps.values()):
                self.status = JobStatus.FAILED

                # Find the first error message
                for step in self.steps.values():
                    if step.status == StepStatus.FAILED and step.error:
                        self.error = f"Step '{step.name}' failed: {step.error}"
                        break

        return self


class JobProgressEvent(BaseModel):
    """WebSocket event for job progress updates."""

    job_id: str = Field(..., description="Job ID")
    step: str = Field(..., description="Current step name")
    status: StepStatus = Field(..., description="Step status")
    progress: float = Field(..., description="Progress percentage (0-100)")
    overall_progress: float = Field(..., description="Overall job progress")
    message: Optional[str] = Field(None, description="Status message")
    timestamp: float = Field(default_factory=time.time, description="Event timestamp")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    offset: int = Field(0, description="Number of items to skip", ge=0)
    limit: int = Field(
        10, description="Maximum number of items to return", ge=1, le=100
    )


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    offset: int = Field(..., description="Offset used in the query")
    limit: int = Field(..., description="Limit used in the query")
    has_more: bool = Field(False, description="Whether there are more items available")

    class Config:
        """Model configuration."""

        arbitrary_types_allowed = True


class PaginatedIngestionJobs(PaginatedResponse):
    """Paginated response for ingestion jobs."""

    items: List[IngestionJob] = Field(..., description="List of ingestion jobs")
