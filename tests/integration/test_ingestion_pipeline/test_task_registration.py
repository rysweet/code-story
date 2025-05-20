"""Integration tests for Celery task registration.

These tests verify that tasks are properly registered with the Celery
application and can be discovered by the worker.
"""

import os
import pytest
import time
from unittest.mock import patch

from celery.result import AsyncResult

from codestory.ingestion_pipeline.celery_app import app as celery_app
from codestory.ingestion_pipeline.step import StepStatus, generate_job_id
from codestory_filesystem.step import FileSystemStep


@pytest.mark.integration
@pytest.mark.celery
def test_filesystem_task_registration():
    """Test that the filesystem task is properly registered with Celery."""
    # Get the list of registered tasks
    registered_tasks = celery_app.tasks.keys()
    
    # Check that the filesystem task is registered with the correct name
    task_name = "codestory_filesystem.step.process_filesystem"
    assert task_name in registered_tasks, f"Task {task_name} not registered with Celery. Registered tasks: {registered_tasks}"


@pytest.mark.integration
@pytest.mark.celery
def test_filesystem_task_routing():
    """Test that the filesystem task is routed to the correct queue."""
    # Get the routing configuration for the task
    task_name = "codestory_filesystem.step.process_filesystem"
    routes = celery_app.conf.task_routes or {}
    
    # Directly check if our pattern exists in the routes
    check_pattern = "codestory_*.step.*"
    assert check_pattern in routes, f"Expected route pattern '{check_pattern}' not found in routes: {routes}"
    
    # Check that the pattern routes to the ingestion queue
    route = routes.get(check_pattern)
    assert route is not None, f"Route for pattern '{check_pattern}' is None"
    assert route.get('queue') == 'ingestion', f"Pattern '{check_pattern}' should route to 'ingestion' queue, got: {route}"


@pytest.mark.integration
@pytest.mark.celery
def test_run_step_task_name_mapping():
    """Test that the run_step task uses the correct task name mapping."""
    # Import the task function
    from codestory.ingestion_pipeline.tasks import run_step
    
    # Check the task_name_map in the function source code
    import inspect
    source = inspect.getsource(run_step)
    
    # Check if the mapping contains the filesystem task with the new naming pattern
    assert "task_name_map" in source, "task_name_map not found in run_step function"
    assert "filesystem" in source and "codestory_filesystem.step.process_filesystem" in source, \
        "Filesystem task mapping not found in run_step function"


@pytest.mark.integration
@pytest.mark.celery
def test_step_class_task_delegation():
    """Test that the FileSystemStep.run method properly delegates to the Celery task."""
    # Check the FileSystemStep.run source code
    import inspect
    source = inspect.getsource(FileSystemStep.run)
    
    # Verify it uses the current_app.send_task with the correct task name
    assert "current_app.send_task" in source, "current_app.send_task not found in FileSystemStep.run method"
    assert "codestory_filesystem.step.process_filesystem" in source, \
        "Task name 'codestory_filesystem.step.process_filesystem' not found in FileSystemStep.run method"