"""Utility functions for the ingestion pipeline.

This module provides helper functions for logging, metrics collection,
and other shared functionalities for the ingestion pipeline.
"""
import importlib
import logging
import sys
from pathlib import Path
from typing import Any
import yaml
if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points, EntryPoint
    USE_IMPORTLIB = True
elif sys.version_info >= (3, 8):
    from importlib.metadata import entry_points, EntryPoint
    USE_IMPORTLIB = True
else:
    try:
        import pkg_resources
        USE_IMPORTLIB = False
    except ImportError:
        USE_IMPORTLIB = True
        from importlib.metadata import entry_points, EntryPoint
from prometheus_client import Counter, Gauge, Histogram
from .step import PipelineStep, StepStatus
logger = logging.getLogger(__name__)

def _get_or_create_counter(name: str, description: str, counter_labels: list[str] | None=None) -> None:
    try:
        if counter_labels is None:
            counter_labels = []
        return Counter(name, description, counter_labels)  # type: ignore[return-value]
    except ValueError:
        from prometheus_client import REGISTRY
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, '_name') and collector._name == name:
                return collector  # type: ignore[return-value]

        class NoOpCounter:

            def labels(self, **kwargs: Any) -> 'NoOpCounter':
                return self

            def inc(self, amount: int=1) -> None:
                pass
        return NoOpCounter()  # type: ignore[return-value]

def _get_or_create_histogram(name: str, description: str, hist_labels: list[str] | None=None, buckets: tuple[float, ...] | None=None) -> None:
    if buckets is None:
        buckets = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    try:
        if hist_labels is None:
            hist_labels = []
        return Histogram(name, description, hist_labels, buckets=buckets)  # type: ignore[return-value]
    except ValueError:
        from prometheus_client import REGISTRY
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, '_name') and collector._name == name:
                return collector  # type: ignore[return-value]

        class NoOpHistogram:

            def labels(self, **kwargs: Any) -> 'NoOpHistogram':
                return self

            def observe(self, amount: float) -> None:
                pass
        return NoOpHistogram()  # type: ignore[return-value]

def _get_or_create_gauge(name: str, description: str, gauge_labels: list[str] | None=None) -> None:
    try:
        if gauge_labels is None:
            gauge_labels = []
        return Gauge(name, description, gauge_labels)  # type: ignore[return-value]
    except ValueError:
        from prometheus_client import REGISTRY
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, '_name') and collector._name == name:
                return collector  # type: ignore[return-value]

        class NoOpGauge:

            def inc(self, amount: int=1) -> None:
                pass

            def dec(self, amount: int=1) -> None:
                pass

            def set(self, value: float) -> None:
                pass

            def labels(self, **kwargs: Any) -> 'NoOpGauge':
                return self
        return NoOpGauge()  # type: ignore[return-value]
INGESTION_JOB_COUNT = _get_or_create_counter('codestory_ingestion_jobs_total', 'Total number of ingestion jobs', ['status'])
INGESTION_STEP_COUNT = _get_or_create_counter('codestory_ingestion_steps_total', 'Total number of ingestion steps executed', ['step_name', 'status'])
INGESTION_STEP_DURATION = _get_or_create_histogram('codestory_ingestion_step_duration_seconds', 'Duration of ingestion steps in seconds', ['step_name'])
INGESTION_ACTIVE_JOBS = _get_or_create_gauge('codestory_ingestion_active_jobs', 'Number of currently active ingestion jobs')

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
    if isinstance(config_path, str):
        config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f'Pipeline configuration file not found: {config_path}')
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f'Invalid YAML in pipeline configuration: {e}') from e
    if not isinstance(config, dict):
        raise ValueError('Pipeline configuration must be a dictionary')
    if 'steps' not in config:
        raise ValueError("Pipeline configuration must contain a 'steps' key")
    if not isinstance(config['steps'], list):
        raise ValueError("Pipeline configuration 'steps' must be a list")
    for i, step in enumerate(config['steps']):
        if not isinstance(step, dict):
            raise ValueError(f'Step {i} must be a dictionary')
        if 'name' not in step:
            raise ValueError(f"Step {i} must have a 'name' key")
    if 'retry' not in config:
        config['retry'] = {}
    if 'max_retries' not in config['retry']:
        config['retry']['max_retries'] = 3
    if 'back_off_seconds' not in config['retry']:
        config['retry']['back_off_seconds'] = 10
    for step in config['steps']:
        if 'max_retries' not in step:
            step['max_retries'] = config['retry']['max_retries']
        if 'back_off_seconds' not in step:
            step['back_off_seconds'] = config['retry']['back_off_seconds']
    return config

def discover_pipeline_steps() -> dict[str, type[PipelineStep]]:
    """Discover all registered pipeline step plugins.

    Uses entry points to find all registered pipeline steps.

    Returns:
        Dict[str, Type[PipelineStep]]: Dictionary mapping step names to step classes
    """
    steps: dict[str, type[PipelineStep]] = {}
    entry_point_group = 'codestory.pipeline.steps'
    try:
        if USE_IMPORTLIB:
            if sys.version_info >= (3, 10):
                eps = entry_points(group=entry_point_group)
                entry_points_list = list(eps)
            else:
                all_eps = entry_points()
                entry_points_list = []
                if hasattr(all_eps, 'select'):
                    entry_points_list = list(all_eps.select(group=entry_point_group))
                else:
                    entry_points_list = all_eps.get(entry_point_group, [])
            for entry_point in entry_points_list:
                step_name = entry_point.name
                step_class = entry_point.load()
                if not issubclass(step_class, PipelineStep):
                    logger.warning(f'Entry point {step_name} does not provide a PipelineStep subclass, skipping')
                    continue
                steps[step_name] = step_class
                logger.info(f'Discovered pipeline step: {step_name}')
        else:
            try:
                import pkg_resources
                for entry_point in pkg_resources.iter_entry_points(entry_point_group):
                    step_name = entry_point.name
                    step_class = entry_point.load()
                    if not issubclass(step_class, PipelineStep):
                        logger.warning(f'Entry point {step_name} does not provide a PipelineStep subclass, skipping')
                        continue
                    steps[step_name] = step_class
                    logger.info(f'Discovered pipeline step: {step_name}')
            except ImportError:
                logger.warning('pkg_resources not available and importlib.metadata failed')
    except Exception as e:
        logger.error(f'Error discovering pipeline steps: {e}')
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
    step_mapping = {'blarify': 'codestory_blarify.step', 'filesystem': 'codestory_filesystem.step', 'summarizer': 'codestory_summarizer.step', 'documentation_grapher': 'codestory_docgrapher.step'}
    if step_name not in step_mapping:
        return None
    try:
        module_name = step_mapping[step_name]
        module = importlib.import_module(module_name)
        for attr_name in dir(module):
            if attr_name.endswith('Step'):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, PipelineStep):
                    return attr
    except (ImportError, AttributeError) as e:
        logger.warning(f'Failed to manually find step {step_name}: {e}')
    return None

def record_step_metrics(step_name: str, status: StepStatus, duration: float | None=None) -> None:
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
    elif status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.STOPPED, StepStatus.CANCELLED):
        INGESTION_ACTIVE_JOBS.dec()