"""Utility functions for the ingestion pipeline.

This module provides helper functions for logging, metrics collection,
and other shared functionalities for the ingestion pipeline.
"""

import importlib
import logging
from pathlib import Path
from typing import Any

import yaml

# Use importlib.metadata instead of pkg_resources (which is deprecated)
try:
    from importlib.metadata import entry_points
except ImportError:
    # Fallback for Python < 3.8
    import pkg_resources

from prometheus_client import Counter, Gauge, Histogram

from .step import PipelineStep, StepStatus

# Set up logging
logger = logging.getLogger(__name__)


# Helper functions to get or create metrics (avoids duplicate registration)
def _get_or_create_counter(name, description, labels=None):
    try:
        # Always pass an empty list if labels is None
        if labels is None:
            labels = []
        return Counter(name, description, labels)
    except ValueError:
        # If already registered, get existing collector
        from prometheus_client import REGISTRY

        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and collector._name == name:
                return collector

        # Return a no-op counter if we can't find or create the real one
        class NoOpCounter:
            def labels(self, **kwargs):
                return self

            def inc(self, amount=1):
                pass

        return NoOpCounter()


def _get_or_create_histogram(name, description, labels=None, buckets=None):
    if buckets is None:
        buckets = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    try:
        # Always pass an empty list if labels is None
        if labels is None:
            labels = []
        return Histogram(name, description, labels, buckets=buckets)
    except ValueError:
        # If already registered, get existing collector
        from prometheus_client import REGISTRY

        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and collector._name == name:
                return collector

        # Return a no-op histogram if we can't find or create the real one
        class NoOpHistogram:
            def labels(self, **kwargs):
                return self

            def observe(self, amount):
                pass

        return NoOpHistogram()


def _get_or_create_gauge(name, description, labels=None):
    try:
        # Always pass an empty list if labels is None
        if labels is None:
            labels = []
        return Gauge(name, description, labels)
    except ValueError:
        # If already registered, get existing collector
        from prometheus_client import REGISTRY

        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and collector._name == name:
                return collector

        # Return a no-op gauge if we can't find or create the real one
        class NoOpGauge:
            def inc(self, amount=1):
                pass

            def dec(self, amount=1):
                pass

            def set(self, value):
                pass

            def labels(self, **kwargs):
                return self

        return NoOpGauge()


# Define metrics
INGESTION_JOB_COUNT = _get_or_create_counter(
    "codestory_ingestion_jobs_total", "Total number of ingestion jobs", ["status"]
)

INGESTION_STEP_COUNT = _get_or_create_counter(
    "codestory_ingestion_steps_total",
    "Total number of ingestion steps executed",
    ["step_name", "status"],
)

INGESTION_STEP_DURATION = _get_or_create_histogram(
    "codestory_ingestion_step_duration_seconds",
    "Duration of ingestion steps in seconds",
    ["step_name"],
)

INGESTION_ACTIVE_JOBS = _get_or_create_gauge(
    "codestory_ingestion_active_jobs", "Number of currently active ingestion jobs"
)


def load_pipeline_config(config_path: str | Path) -> dict[str, Any]:
    """Load and validate the pipeline configuration.

    Args:
        config_path: Path to the pipeline configuration YAML file

    Returns:
        Dict[str, Any]: Validated configuration dictionary

    Raises:
        FileNotFoundError: If the configuration file is not found
        ValueError: If the configuration file is invalid
    """
    # Convert string path to Path object if needed
    if isinstance(config_path, str):
        config_path = Path(config_path)

    # Check if the file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Pipeline configuration file not found: {config_path}")

    # Load the YAML file
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in pipeline configuration: {e}")

    # Validate the configuration
    if not isinstance(config, dict):
        raise ValueError("Pipeline configuration must be a dictionary")

    # Ensure there's a steps list
    if "steps" not in config:
        raise ValueError("Pipeline configuration must contain a 'steps' key")

    if not isinstance(config["steps"], list):
        raise ValueError("Pipeline configuration 'steps' must be a list")

    # Ensure each step has a name
    for i, step in enumerate(config["steps"]):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i} must be a dictionary")
        if "name" not in step:
            raise ValueError(f"Step {i} must have a 'name' key")

    # Add default values if missing
    if "retry" not in config:
        config["retry"] = {}
    if "max_retries" not in config["retry"]:
        config["retry"]["max_retries"] = 3
    if "back_off_seconds" not in config["retry"]:
        config["retry"]["back_off_seconds"] = 10

    return config


def discover_pipeline_steps() -> dict[str, type[PipelineStep]]:
    """Discover all registered pipeline step plugins.

    Uses entry points to find all registered pipeline steps.

    Returns:
        Dict[str, Type[PipelineStep]]: Dictionary mapping step names to step classes
    """
    steps = {}
    entry_point_group = "codestory.pipeline.steps"

    try:
        # Use importlib.metadata if available, otherwise fall back to pkg_resources
        if "entry_points" in globals():
            # Python 3.8+ with importlib.metadata
            eps = entry_points(group=entry_point_group)
            try:
                # Python 3.10+ API
                entry_points_list = list(eps)
            except TypeError:
                # Python 3.8-3.9 API
                entry_points_list = eps.get(entry_point_group, [])

            for entry_point in entry_points_list:
                step_name = entry_point.name
                step_class = entry_point.load()

                # Validate that it's a PipelineStep subclass
                if not issubclass(step_class, PipelineStep):
                    logger.warning(
                        f"Entry point {step_name} does not provide a PipelineStep subclass, skipping"
                    )
                    continue

                steps[step_name] = step_class
                logger.info(f"Discovered pipeline step: {step_name}")
        else:
            # Python < 3.8 with pkg_resources
            for entry_point in pkg_resources.iter_entry_points(entry_point_group):
                step_name = entry_point.name
                step_class = entry_point.load()

                # Validate that it's a PipelineStep subclass
                if not issubclass(step_class, PipelineStep):
                    logger.warning(
                        f"Entry point {step_name} does not provide a PipelineStep subclass, skipping"
                    )
                    continue

                steps[step_name] = step_class
                logger.info(f"Discovered pipeline step: {step_name}")
    except Exception as e:
        logger.error(f"Error discovering pipeline steps: {e}")

    return steps


def find_step_manually(step_name: str) -> type[PipelineStep] | None:
    """Find a pipeline step class by name without entry points.

    This is a fallback for development and testing when entry points
    might not be properly registered.

    Args:
        step_name: Name of the step to find

    Returns:
        Optional[Type[PipelineStep]]: Step class if found, None otherwise
    """
    step_mapping = {
        "blarify": "codestory_blarify.step",
        "filesystem": "codestory_filesystem.step",
        "summarizer": "codestory_summarizer.step",
        "documentation_grapher": "codestory_docgrapher.step",
    }

    if step_name not in step_mapping:
        return None

    try:
        module_name = step_mapping[step_name]
        module = importlib.import_module(module_name)

        # Look for a class that ends with 'Step'
        for attr_name in dir(module):
            if attr_name.endswith("Step"):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, PipelineStep):
                    return attr
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to manually find step {step_name}: {e}")

    return None


def record_step_metrics(
    step_name: str, status: StepStatus, duration: float | None = None
) -> None:
    """Record metrics for a pipeline step.

    Args:
        step_name: Name of the step
        status: Status of the step
        duration: Duration of the step in seconds (optional)
    """
    INGESTION_STEP_COUNT.labels(step_name=step_name, status=status.value).inc()

    if duration is not None:
        INGESTION_STEP_DURATION.labels(step_name=step_name).observe(duration)


def record_job_metrics(status: StepStatus) -> None:
    """Record metrics for an ingestion job.

    Args:
        status: Status of the job
    """
    INGESTION_JOB_COUNT.labels(status=status.value).inc()

    if status == StepStatus.RUNNING:
        INGESTION_ACTIVE_JOBS.inc()
    elif status in (
        StepStatus.COMPLETED,
        StepStatus.FAILED,
        StepStatus.STOPPED,
        StepStatus.CANCELLED,
    ):
        INGESTION_ACTIVE_JOBS.dec()
