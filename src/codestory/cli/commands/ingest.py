"""
Ingestion commands for the Code Story CLI.
"""

import os
import time
from typing import Dict, Any, Optional

import click

# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    import click as rich_click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from ..client import ServiceClient, ProgressClient


@click.group(help="Ingest a repository into Code Story.")
def ingest():
    """Command group for ingestion operations."""
    pass


@ingest.command(name="start", help="Start ingestion of a repository.")
@click.argument("repository_path", type=click.Path(exists=True))
@click.option("--no-progress", is_flag=True, help="Don't show progress updates.")
@click.pass_context
def start_ingestion(
    ctx: click.Context, repository_path: str, no_progress: bool = False
) -> None:
    """
    Start ingestion of a repository.

    REPOSITORY_PATH is the path to the repository to ingest.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # Get absolute path
    repository_path = os.path.abspath(repository_path)

    console.print(f"Starting ingestion of [cyan]{repository_path}[/]...")

    response = client.start_ingestion(repository_path)
    job_id = response.get("job_id")

    if not job_id:
        console.print("[bold red]Error:[/] Failed to start ingestion job.")
        return

    console.print(f"Ingestion job started with ID: [green]{job_id}[/]")

    if no_progress:
        return

    # Show progress updates
    _show_progress(ctx, job_id)


@ingest.command(name="status", help="Show status of an ingestion job.")
@click.argument("job_id")
@click.pass_context
def job_status(ctx: click.Context, job_id: str) -> None:
    """
    Show status of an ingestion job.

    JOB_ID is the ID of the ingestion job.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print(f"Getting status for job: [cyan]{job_id}[/]...")

    response = client.get_ingestion_status(job_id)

    _display_job_status(console, response)


@ingest.command(name="stop", help="Stop an ingestion job.")
@click.argument("job_id")
@click.pass_context
def stop_job(ctx: click.Context, job_id: str) -> None:
    """
    Stop an ingestion job.

    JOB_ID is the ID of the ingestion job to stop.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print(f"Stopping job: [cyan]{job_id}[/]...")

    response = client.stop_ingestion(job_id)

    if response.get("success"):
        console.print(f"Job [cyan]{job_id}[/] has been [yellow]stopped[/].")
    else:
        console.print(
            f"[bold red]Error:[/] Failed to stop job {job_id}. {response.get('message', '')}"
        )


@ingest.command(name="jobs", help="List all ingestion jobs.")
@click.pass_context
def list_jobs(ctx: click.Context) -> None:
    """
    List all ingestion jobs.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Getting list of ingestion jobs...")

    jobs = client.list_ingestion_jobs()

    if not jobs:
        console.print("No ingestion jobs found.")
        return

    table = Table(title="Ingestion Jobs")
    table.add_column("Job ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Repository", style="blue")
    table.add_column("Created", style="magenta")
    table.add_column("Progress", style="yellow")

    for job in jobs:
        status = job.get("status", "unknown")
        status_style = {
            "completed": "green",
            "failed": "red",
            "cancelled": "yellow",
            "running": "blue",
            "pending": "magenta",
        }.get(status.lower(), "white")

        table.add_row(
            job.get("job_id", ""),
            f"[{status_style}]{status}[/]",
            job.get("repository_path", ""),
            job.get("created_at", ""),
            f"{job.get('progress', 0):.1f}%",
        )

    console.print(table)


def _show_progress(ctx: click.Context, job_id: str) -> None:
    """
    Show live progress updates for an ingestion job.

    Args:
        ctx: Click context
        job_id: Ingestion job ID
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # Create progress display
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[bold green]{task.fields[status]}"),
    )

    overall_task = progress.add_task(
        "[bold]Overall Progress", total=100, status="Initializing..."
    )
    step_tasks = {}

    # Function to update progress
    def update_progress(data: Dict[str, Any]) -> None:
        nonlocal step_tasks

        # Handle different response formats (service API vs Celery/Redis format)
        # Format conversion for Redis PubSub messages
        if "job_id" in data and "step" in data:
            from codestory.ingestion_pipeline.step import StepStatus
            # This is a JobProgressEvent from Redis
            overall_status = data.get("status", StepStatus.RUNNING).lower()
            overall_progress = data.get("overall_progress", 0)
            
            # Convert to steps format
            if "steps" not in data:
                data["steps"] = [{
                    "name": data.get("step", "Processing"),
                    "status": overall_status,
                    "progress": data.get("progress", 0),
                    "message": data.get("message", "")
                }]
        else:
            # Regular job status format
            overall_status = data.get("status", "running").lower()
            overall_progress = data.get("progress", 0)

        # Update overall progress
        progress.update(
            overall_task, completed=overall_progress, status=overall_status.capitalize()
        )

        # Update step progress
        steps = data.get("steps", [])
        
        # If no steps but we have current_step info, create a step entry
        if not steps and "current_step" in data:
            steps = [{
                "name": data.get("current_step", "Processing"),
                "status": overall_status,
                "progress": overall_progress,
                "message": data.get("message", "")
            }]

        for step in steps:
            step_name = step.get("name", "unknown")
            step_status = step.get("status", "pending").lower()
            step_progress = step.get("progress", 0)

            if step_name not in step_tasks:
                step_tasks[step_name] = progress.add_task(
                    f"[cyan]{step_name}[/]", total=100, status=step_status.capitalize()
                )

            progress.update(
                step_tasks[step_name],
                completed=step_progress,
                status=step_status.capitalize(),
            )

        # Check if finished
        if overall_status.lower() in ("completed", "failed", "cancelled"):
            # Let the live display render one more time
            time.sleep(0.5)

            # Signal progress client to stop
            return False

        return True

    # Create progress client
    progress_client = ProgressClient(
        job_id=job_id,
        callback=update_progress,
        console=console,
        settings=ctx.obj["settings"],
        # Explicitly get Redis URL from settings if available
        redis_url=ctx.obj["settings"].redis.uri if hasattr(ctx.obj["settings"], "redis") else None,
    )

    # Start tracking progress
    with Live(progress, refresh_per_second=4):
        progress_client.start()

        # Wait for completion or error
        while True:
            try:
                # Check if process has been interrupted
                if progress_client._stop_event.is_set():
                    break

                time.sleep(0.5)
            except KeyboardInterrupt:
                console.print("[yellow]Stopping progress updates...[/]")
                break

    # Stop tracking progress
    progress_client.stop()

    # Display final status
    response = client.get_ingestion_status(job_id)
    console.print()
    _display_job_status(console, response)


def _display_job_status(console: Console, status: Dict[str, Any]) -> None:
    """
    Display detailed status for an ingestion job.

    Args:
        console: Rich console
        status: Job status data
    """
    # Create status table
    table = Table(title=f"Job Status: {status.get('job_id', 'Unknown')}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    # Add main job info
    table.add_row("Repository", status.get("repository_path", "Unknown"))
    table.add_row("Created", status.get("created_at", "Unknown"))
    table.add_row("Updated", status.get("updated_at", "Unknown"))

    # Format status with appropriate color
    job_status = status.get("status", "unknown")
    status_style = {
        "completed": "green",
        "failed": "red",
        "cancelled": "yellow",
        "running": "blue",
        "pending": "magenta",
    }.get(job_status.lower(), "white")

    table.add_row("Status", f"[{status_style}]{job_status}[/]")
    table.add_row("Progress", f"{status.get('progress', 0):.1f}%")

    # Add error if present
    if "error" in status and status["error"]:
        table.add_row("Error", f"[red]{status['error']}[/]")

    console.print(table)

    # Create step status table
    steps = status.get("steps", [])

    if steps:
        step_table = Table(title="Step Status")
        step_table.add_column("Step", style="cyan")
        step_table.add_column("Status", style="green")
        step_table.add_column("Progress", style="yellow")
        step_table.add_column("Message", style="magenta")

        for step in steps:
            step_status = step.get("status", "unknown")
            status_style = {
                "completed": "green",
                "failed": "red",
                "cancelled": "yellow",
                "running": "blue",
                "pending": "magenta",
            }.get(step_status.lower(), "white")

            step_table.add_row(
                step.get("name", "Unknown"),
                f"[{status_style}]{step_status}[/]",
                f"{step.get('progress', 0):.1f}%",
                step.get("message", ""),
            )

        console.print(step_table)
