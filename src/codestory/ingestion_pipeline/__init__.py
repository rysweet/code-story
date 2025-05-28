"""Ingestion pipeline for processing codebases.

This module provides the pipeline for processing codebases and storing
the results in the graph database. The pipeline orchestrates a series
of workflow steps that can be configured and extended.
"""

from typing import Any

from .manager import PipelineManager
from .step import PipelineStep, StepStatus

__all__ = ["PipelineManager", "PipelineStep", "StepStatus"]


def main() -> Any:
    """Entry point for running the module.

    This allows running with 'python -m codestory.ingestion_pipeline'
    """
    from .run_worker import main as run_worker_main

    run_worker_main()


# Make the module directly executable
if __name__ == "__main__":
    main()
