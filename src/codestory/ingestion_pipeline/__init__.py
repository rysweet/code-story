"""Ingestion pipeline for processing codebases.

This module provides the pipeline for processing codebases and storing
the results in the graph database. The pipeline orchestrates a series
of workflow steps that can be configured and extended.
"""

from .manager import PipelineManager
from .step import PipelineStep, StepStatus

__all__ = ["PipelineManager", "PipelineStep", "StepStatus"]