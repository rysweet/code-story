"""Ingestion commands for the Code Story CLI."""

import contextlib
import os
import subprocess
import time
from typing import Any, Optional, Union

import click

# Import rich_click if available, otherwise create a stub
with contextlib.suppress(ImportError):
    pass
from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from rich.table import Table

from ..client import ProgressClient, ServiceClient
from ..require_service_available import require_service_available


@click.group(help="Ingest a repository into Code Story.")
def ingest() -> Any:
    """Command group for ingestion operations."""
    pass


def run_command(command, capture_output=True, shell=True) -> None:  # type: ignore[no-untyped-def]
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            command, capture_output=capture_output, text=True, shell=shell, check=True
        )
        return result.stdout if capture_output else None  # type: ignore[return-value]
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error output: {e.stderr}")
        return None


def is_docker_running() -> Any:
    """Check if Docker is running and containers exist."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=codestory-service",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit
        )
        return "codestory-service" in result.stdout
    except Exception:
        return False


def is_repo_mounted(repo_path, console=None) -> None:  # type: ignore[no-untyped-def]
    """Check if repository is already mounted correctly for ingestion.

    This checks both the actual mount and whether the path is accessible
    inside the container at the expected location.
    """
    # Get the repository name from the path
    repo_path = os.path.abspath(repo_path)
    repo_name = os.path.basename(repo_path)
    container_path = f"/repositories/{repo_name}"

    try:
        # First try the Docker service container
        services_to_check = ["codestory-service", "codestory-worker"]

        for service in services_to_check:
            # Check if service is running
            service_check = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={service}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if service not in service_check.stdout:
                if console:
                    console.print(f"Container {service} is not running")
                continue

            # Check if directory exists and has content in the container
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    service,
                    "bash",
                    "-c",
                    f"test -d {container_path} && ls -la {container_path} | wc -l | "
                    f"grep -v '^[[:space:]]*2[[:space:]]*$'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            # If the directory exists and has more than just . and .. entries, it's mounted
            path_exists_with_content = result.returncode == 0

            # Additional check - make sure a specific file from the repo is visible
            test_files = ["README.md", "pyproject.toml", ".git/config"]
            for test_file in test_files:
                local_test_file = os.path.join(repo_path, test_file)
                if os.path.exists(local_test_file):
                    file_check = subprocess.run(
                        [
                            "docker",
                            "exec",
                            service,
                            "test",
                            "-f",
                            f"{container_path}/{test_file}",
                            "&&",
                            "echo",
                            "exists",
                        ],
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if "exists" in file_check.stdout:
                        if console:
                            console.print(
                                f"[green]Repository confirmed mounted in {service} container[/]"
                            )
                        return True  # type: ignore[return-value]

            if path_exists_with_content:
                if console:
                    console.print(
                        f"[green]Repository directory exists with content in {service}[/]"
                    )
                return True  # type: ignore[return-value]

            # If we get here with the first service but mount not found, try the next

        # If we reach here, repository is not mounted in any container
        # Log some diagnostic information
        for service in services_to_check:
            try:
                # Check if service is running first
                service_check = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        f"name={service}",
                        "--format",
                        "{{.Names}}",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if service in service_check.stdout:
                    # Try to inspect what's actually in /repositories
                    inspect_result = subprocess.run(
                        ["docker", "exec", service, "ls", "-la", "/repositories"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if console:
                        console.print(
                            f"{service} container /repositories directory contents:\n"
                            f"{inspect_result.stdout}"
                        )

                    # Also check if the directory exists but is empty
                    dir_check = subprocess.run(
                        [
                            "docker",
                            "exec",
                            service,
                            "test",
                            "-d",
                            container_path,
                            "&&",
                            "echo",
                            "exists",
                        ],
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if "exists" in dir_check.stdout:
                        if console:
                            console.print(
                                f"Directory {container_path} exists in {service} but "
                                f"appears to be empty."
                            )
            except Exception as e:
                if console:
                    console.print(f"Error checking {service} container: {e}")

        return False  # type: ignore[return-value]
    except Exception as e:
        if console:
            console.print(f"Error checking if repository is mounted in containers: {e}")
        return False  # type: ignore[return-value]


def create_override_file(repo_path, console=None) -> None:  # type: ignore[no-untyped-def]
    """Create a docker-compose.override.yml file with the repository mount."""
    repo_path = os.path.abspath(repo_path)
    repo_name = os.path.basename(repo_path)
    container_path = f"/repositories/{repo_name}"

    override_content = f"""services:
  service:
    volumes:
      - {repo_path}:{container_path}:ro
  worker:
    volumes:
      - {repo_path}:{container_path}:ro
"""

    # Write the override file
    override_file_path = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        ),
        "docker-compose.override.yml",
    )
    try:
        with open(override_file_path, "w") as f:
            f.write(override_content)
        if console:
            console.print(
                f"[green]Created docker-compose.override.yml with mount configuration "
                f"for {repo_path}[/]"
            )
        return True  # type: ignore[return-value]
    except Exception as e:
        if console:
            console.print(f"[red]Error creating override file: {e}[/]")
        return False  # type: ignore[return-value]


def create_repo_config(repo_path, console=None) -> None:  # type: ignore[no-untyped-def]
    """Create repository configuration file."""
    config_dir = os.path.join(repo_path, ".codestory")
    os.makedirs(config_dir, exist_ok=True)

    config_file = os.path.join(config_dir, "repository.toml")
    repo_name = os.path.basename(repo_path)

    with open(config_file, "w") as f:
        f.write(
            f"""# CodeStory repository configuration
# Created by automatic repository mounting

[repository]
name = "{repo_name}"
local_path = "{repo_path}"
container_path = "/repositories/{repo_name}"
mounted = true
mount_time = "{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}"
auto_mounted = true
"""
        )

    if console:
        console.print(f"[green]Created repository config at {config_file}[/]")
    return True  # type: ignore[return-value]


def wait_for_service(console=None, max_attempts=30) -> None:  # type: ignore[no-untyped-def]
    """Wait for the service to be ready."""
    if console:
        console.print("Waiting for service to be ready...")
    attempts = 0

    while attempts < max_attempts:
        try:
            health_status = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    "codestory-service",
                ],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()

            if console:
                console.print(
                    f"Service status: {health_status} (attempt {attempts + 1}/{max_attempts})"
                )

            if health_status == "healthy":
                if console:
                    console.print("[green]Service is ready![/]")
                return True  # type: ignore[return-value]

            time.sleep(5)
            attempts += 1
        except Exception as e:
            if console:
                console.print(f"Error checking service status: {e}")
            time.sleep(5)
            attempts += 1

    if console:
        console.print("[yellow]Service did not become ready in time[/]")
    return False  # type: ignore[return-value]


def setup_repository_mount(repo_path, console=None, force_remount=False) -> None:  # type: ignore[no-untyped-def]
    """Set up repository mount using Docker bind mounts without restarting containers."""
    repo_path = os.path.abspath(repo_path)

    # Check if path exists
    if not os.path.isdir(repo_path):
        if console:
            console.print(f"[red]Error: Directory {repo_path} does not exist[/]")
        return False  # type: ignore[return-value]

    # Get repo name for specific mounting
    repo_name = os.path.basename(repo_path)
    container_path = f"/repositories/{repo_name}"

    # Check if Docker is running
    if not is_docker_running():
        if console:
            console.print("[yellow]Starting Docker containers with repository mount...[/]")
        # Create docker-compose.override.yml with repository mount
        create_override_file(repo_path, console)
        # Start containers with repository mount
        run_command("docker-compose up -d", capture_output=False)

        # Wait for service to be ready
        wait_for_service(console)
        return True  # type: ignore[return-value]

    # Check if repository is already mounted if not forcing a remount
    if not force_remount and is_repo_mounted(repo_path, console):  # type: ignore[func-returns-value]
        if console:
            console.print(
                f"[green]Repository {repo_path} is already mounted correctly at {container_path}[/]"
            )
        return True  # type: ignore[return-value]

    # Repository needs to be mounted without restarting containers
    if console:
        console.print(
            f"[yellow]Dynamically mounting repository {repo_path} to {container_path}...[/]"
        )

    # Create docker-compose.override.yml file with the new mount
    create_override_file(repo_path, console)

    # Restart only the required services with the new configuration
    if console:
        console.print("[yellow]Recreating containers with the new mount configuration...[/]")
    run_command("docker-compose up -d service worker", capture_output=False)

    # Wait for services to be ready
    wait_for_service(console)

    # Create repository config
    create_repo_config(repo_path, console)

    # Verify repository is actually mounted correctly
    verification = is_repo_mounted(repo_path, console)  # type: ignore[func-returns-value]
    if verification:
        if console:
            console.print(
                f"[green]Successfully verified repository is mounted correctly at "
                f"{container_path}[/]"
            )
    else:
        if console:
            console.print(
                "[yellow]Warning: Repository may not be mounted correctly. Continuing anyway.[/]"
            )

            # Try to inspect what's in /repositories for debugging
            inspect_result = subprocess.run(
                ["docker", "exec", "codestory-service", "ls", "-la", "/repositories"],
                capture_output=True,
                text=True,
                check=False,
            )
            console.print(
                f"[dim]Container /repositories directory contents:\n{inspect_result.stdout}[/]"
            )

    return True  # type: ignore[return-value]


@ingest.command(name="start", help="Start ingestion of a repository.")
@click.argument("repository_path", type=click.Path(exists=True))
@click.option("--no-progress", is_flag=True, help="Don't show progress updates.")
@click.option("--container", is_flag=True, help="Force container path mapping.")
@click.option(
    "--path-prefix",
    default="/repositories",
    help="Container path prefix where repositories are mounted.",
)
@click.option(
    "--auto-mount",
    is_flag=True,
    default=True,
    help="Automatically mount repository and restart containers if needed.",
)
@click.option("--no-auto-mount", is_flag=True, help="Disable automatic repository mounting.")
@click.option(
    "--force-remount",
    is_flag=True,
    help="Force remount even if repository appears to be mounted.",
)
@click.option("--debug", is_flag=True, help="Show additional debug information.")
@click.pass_context
@click.option(
    "--priority",
    type=click.Choice(["high", "default", "low"], case_sensitive=False),
    default="default",
    show_default=True,
    help="Task priority: high, default, or low. Routes to the appropriate Celery queue.",
)
@click.option(
    "--dependency",
    "dependencies",
    multiple=True,
    help="Specify a job ID or step name this job depends on. Can be used multiple times.",
)
@click.option(
    "--eta",
    type=str,
    default=None,
    help="Optional: schedule job to run at this datetime (ISO 8601 or Unix timestamp).",
)
@click.option(
    "--countdown",
    type=int,
    default=None,
    help="Optional: delay job execution by this many seconds from now.",
)
def start_ingestion(
    ctx: click.Context,
    repository_path: str,
    no_progress: bool = False,
    container: bool = False,
    path_prefix: str = "/repositories",
    auto_mount: bool = True,
    no_auto_mount: bool = False,
    force_remount: bool = False,
    debug: bool = False,
    priority: str = "default",
    dependencies: tuple[str, ...] = (),
    eta: Optional[Union[str, int]] = None,
    countdown: Optional[int] = None,
) -> None:
    """
    Start ingestion of a repository.

    Optionally specify dependencies using --dependency JOB_ID or --dependency STEP_NAME.
    The job will not start until all dependencies are complete.

    REPOSITORY_PATH is the path to the repository to ingest.

    When using Docker deployment, this command will automatically:
    1. Detect if you're connected to a containerized service
    2. Mount the repository into the containers if needed
    3. Restart the containers with proper volume mounts
    4. Map local paths to container paths for proper access

    Examples:
      Local path:     /Users/name/projects/my-repo
      Container path: /repositories/my-repo
    """
    require_service_available()

    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    # Get absolute local path
    local_path = os.path.abspath(repository_path)
    console.print(f"Starting ingestion of [cyan]{local_path}[/]...")

    # Override auto_mount if no_auto_mount is specified
    if no_auto_mount:
        auto_mount = False

    # Get the repository name from the path (last part)
    repo_name = os.path.basename(local_path)

    # Create container path
    container_path = os.path.join(path_prefix, repo_name)

    # Detect if we're likely running against a container
    is_container = container or "localhost" in client.base_url or "127.0.0.1" in client.base_url

    # Debug information if requested
    if debug:
        console.print("[dim]Debug information:[/]")
        console.print(f"[dim]  Repository path: {local_path}[/]")
        console.print(f"[dim]  Repository name: {repo_name}[/]")
        console.print(f"[dim]  Container path: {container_path}[/]")
        console.print(f"[dim]  Is container environment: {is_container}[/]")

        # Check if containers are running
        docker_ps = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        console.print(f"[dim]  Docker containers: {docker_ps.stdout}[/]")

        # Check if directory exists
        console.print(f"[dim]  Repository exists: {os.path.isdir(local_path)}[/]")

        # Check if directory is mounted
        is_mounted = is_repo_mounted(local_path)  # type: ignore[func-returns-value]
        console.print(f"[dim]  Repository is mounted: {is_mounted}[/]")

        # Check contents of /repositories in container
        try:
            repo_ls = subprocess.run(
                ["docker", "exec", "codestory-service", "ls", "-la", "/repositories"],
                capture_output=True,
                text=True,
                check=False,
            )
            console.print(f"[dim]  Container /repositories contents: {repo_ls.stdout}[/]")

            # Check if target directory exists
            dir_check = subprocess.run(
                [
                    "docker",
                    "exec",
                    "codestory-service",
                    "test",
                    "-d",
                    container_path,
                    "&&",
                    "echo",
                    "exists",
                ],
                shell=True,
                capture_output=True,
                text=True,
                check=False,
            )
            console.print(f"[dim]  Target directory exists: {'exists' in dir_check.stdout}[/]")

            if "exists" in dir_check.stdout:
                # Also check contents of the target directory
                container_ls = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "codestory-service",
                        "ls",
                        "-la",
                        container_path,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                console.print(f"[dim]  Target directory contents: {container_ls.stdout}[/]")
        except Exception as e:
            console.print(f"[dim]  Error checking /repositories: {e}[/]")

    # Automatically mount the repository if needed
    if is_container and auto_mount:
        console.print("Checking if repository is properly mounted...")

        if force_remount:
            console.print("[yellow]Force remount requested. Remounting repository...[/]")
            setup_repository_mount(local_path, console, force_remount=True)
        else:
            # Check if repository is already mounted properly
            if not is_repo_mounted(local_path, console):  # type: ignore[func-returns-value]
                console.print("[yellow]Repository not mounted in container. Setting up mount...[/]")

                # Show what's currently in /repositories to help debug
                try:
                    ls_result = subprocess.run(
                        [
                            "docker",
                            "exec",
                            "codestory-service",
                            "ls",
                            "-la",
                            "/repositories",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    console.print(
                        f"[dim]Current /repositories contents:\n{ls_result.stdout}[/]",
                        style="dim",
                    )
                except Exception as e:
                    console.print(f"[dim]Could not check /repositories: {e}[/]", style="dim")

                # Set up the repository mount
                setup_repository_mount(local_path, console)

                # Wait a moment for the mount to take effect
                time.sleep(2)

                # Verify mount was successful
                verify_check = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "codestory-service",
                        "ls",
                        "-la",
                        container_path,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if verify_check.returncode == 0 and len(verify_check.stdout.strip()) > 0:
                    console.print(f"[green]Repository successfully mounted at {container_path}![/]")
                    console.print(
                        f"[dim]Directory contents:\n{verify_check.stdout}[/]",
                        style="dim",
                    )
                else:
                    console.print(
                        "[yellow]Warning: Repository mount could not be verified. "
                        "Continuing anyway...[/]"
                    )
                    # Show what's in /repositories after mount attempt
                    try:
                        ls_result = subprocess.run(
                            [
                                "docker",
                                "exec",
                                "codestory-service",
                                "ls",
                                "-la",
                                "/repositories",
                            ],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        console.print(
                            f"[dim]/repositories contents after mount attempt:\n"
                            f"{ls_result.stdout}[/]",
                            style="dim",
                        )
                    except Exception:
                        pass
            else:
                console.print(
                    f"[green]Repository is already properly mounted at {container_path}[/]"
                )

    # Path mapping logic
    if is_container:
        console.print("Docker deployment detected. Mapping local path to container path:")
        console.print(f"  Local path:     [cyan]{local_path}[/]")
        console.print(f"  Container path: [cyan]{container_path}[/]")

        # Use container path for ingestion
        ingestion_path = container_path
    else:
        # Use local path directly
        console.print("Using direct path (non-container deployment)")
        ingestion_path = local_path

    try:
        # Prepare scheduling fields
        scheduling_kwargs = {}
        if eta is not None:
            from datetime import datetime
            parsed_eta: object = None
            if isinstance(eta, str):
                try:
                    # Try parsing as ISO 8601 string
                    parsed_eta = datetime.fromisoformat(eta)
                except Exception:
                    try:
                        # Try parsing as integer string timestamp
                        parsed_eta = int(eta)
                    except Exception:
                        console.print(f"[yellow]Warning: Could not parse --eta value '{eta}'[/]")
            elif isinstance(eta, int):
                parsed_eta = eta
            else:
                console.print(f"[yellow]Warning: --eta value '{eta}' is not a recognized type[/]")
            if parsed_eta is not None:
                scheduling_kwargs["eta"] = parsed_eta
        if countdown is not None:
            scheduling_kwargs["countdown"] = countdown

        response = client.start_ingestion(
            ingestion_path,
            priority=priority,
            dependencies=list(dependencies) if dependencies else None,
            **scheduling_kwargs,
        )
        job_id = response.get("job_id")

        if not job_id:
            console.print("[bold red]Error:[/] Failed to start ingestion job - no job ID returned.")
            return
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        # Provide additional help for path-related errors
        if "does not exist" in str(e):
            console.print("\n[yellow]Troubleshooting Suggestions:[/]")
            console.print("1. Make sure your repository is properly mounted:")
            console.print(
                f'   - Try with force remount: [bold]codestory ingest start "{local_path}" '
                f"--force-remount[/]"
            )
            console.print("2. Or manually mount your repository:")
            console.print(f'   - Run: [bold]export REPOSITORY_PATH="{local_path}"[/]')
            console.print("   - Run: [bold]docker-compose down && docker-compose up -d[/]")
            console.print(
                "3. For detailed instructions, see: [bold]docs/deployment/repository_mounting.md[/]"
            )
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
    require_service_available()

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
    require_service_available()

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
    """List all ingestion jobs."""
    require_service_available()

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
        # Ensure all values are properly converted to strings for rendering
        status = str(job.get("status", "unknown"))

        # Extract repository path from either source or repository_path
        repo_path = job.get("repository_path", job.get("source", ""))
        repo_path = "" if repo_path is None else str(repo_path)

        # Format created_at timestamp
        created_at = job.get("created_at", "")
        if isinstance(created_at, int | float):
            from datetime import datetime

            try:
                created_at = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError, OverflowError):
                created_at = str(created_at)
        else:
            created_at = str(created_at) if created_at is not None else ""

        # Get and safely format progress value
        progress = job.get("progress", 0)
        try:
            progress_str = f"{float(progress):.1f}%" if progress is not None else "0.0%"
        except (ValueError, TypeError):
            progress_str = "0.0%"

        # Set status style
        status_style = {
            "completed": "green",
            "failed": "red",
            "cancelled": "yellow",
            "cancelling": "yellow",
            "running": "blue",
            "pending": "magenta",
        }.get(status.lower(), "white")

        table.add_row(
            str(job.get("job_id", "")),
            f"[{status_style}]{status}[/]",
            repo_path,
            created_at,
            progress_str,
        )

    console.print(table)


@ingest.command(
    name="mount",
    help="Mount a repository for ingestion without starting the ingestion process.",
)
@click.argument("repository_path", type=click.Path(exists=True))
@click.option(
    "--force-remount",
    is_flag=True,
    help="Force remount even if repository appears to be mounted.",
)
@click.option("--debug", is_flag=True, help="Show additional debug information.")
@click.pass_context
def mount_repository(
    ctx: click.Context,
    repository_path: str,
    force_remount: bool = False,
    debug: bool = False,
) -> None:
    """
    Mount a repository for ingestion without starting the ingestion process.

    REPOSITORY_PATH is the path to the repository to mount.

    This command handles the mounting process without starting ingestion:
    1. Creates a docker-compose.override.yml file with the repository mount
    2. Recreates the necessary containers with the mount
    3. Verifies that the mount was successful
    """
    require_service_available()

    console: Console = ctx.obj["console"]

    # Get absolute local path
    local_path = os.path.abspath(repository_path)
    repo_name = os.path.basename(local_path)
    container_path = f"/repositories/{repo_name}"

    console.print(f"Mounting repository: [cyan]{local_path}[/] to [cyan]{container_path}[/]")

    # Show debug info if requested
    if debug:
        console.print("[dim]Debug information:[/]")
        console.print(f"[dim]  Repository path: {local_path}[/]")
        console.print(f"[dim]  Repository name: {repo_name}[/]")
        console.print(f"[dim]  Container path: {container_path}[/]")

        # Check if Docker is running
        is_docker = is_docker_running()
        console.print(f"[dim]  Docker is running: {is_docker}[/]")

        if is_docker:
            # Show what's in /repositories
            try:
                ls_result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "codestory-service",
                        "ls",
                        "-la",
                        "/repositories",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                console.print(f"[dim]  Current /repositories contents:\n{ls_result.stdout}[/]")
            except Exception as e:
                console.print(f"[dim]  Could not check /repositories: {e}[/]")

    # Check if already mounted and not forcing remount
    if not force_remount and is_repo_mounted(local_path, console):  # type: ignore[func-returns-value]
        console.print(
            f"[green]Repository {local_path} is already mounted correctly at {container_path}[/]"
        )
        return

    # Perform the mount
    if setup_repository_mount(local_path, console, force_remount):  # type: ignore[func-returns-value]
        console.print(f"[green]Successfully mounted repository: {local_path}[/]")
        console.print(
            f"Now you can run: [bold]codestory ingest start {local_path}[/] to begin ingestion"
        )
    else:
        console.print(f"[red]Failed to mount repository: {local_path}[/]")
        console.print(
            "For detailed instructions, see: [bold]docs/deployment/repository_mounting.md[/]"
        )


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

    overall_task = progress.add_task("[bold]Overall Progress", total=100, status="Initializing...")
    step_tasks: dict[Any, Any] = {}

    # Function to update progress
    def update_progress(data: dict[str, Any]) -> None:
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
                data["steps"] = [
                    {
                        "name": data.get("step", "Processing"),
                        "status": overall_status,
                        "progress": data.get("progress", 0),
                        "message": data.get("message", ""),
                    }
                ]
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
            steps = [
                {
                    "name": data.get("current_step", "Processing"),
                    "status": overall_status,
                    "progress": overall_progress,
                    "message": data.get("message", ""),
                }
            ]

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
            return False  # type: ignore[return-value]

        return True  # type: ignore[return-value]

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


def _display_job_status(console: Console, status: dict[str, Any]) -> None:
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

    # Format timestamps if they're numeric
    created_at = status.get("created_at", "Unknown")
    if isinstance(created_at, int | float):
        from datetime import datetime

        created_at = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
    table.add_row("Created", created_at)

    updated_at = status.get("updated_at", "Unknown")
    if isinstance(updated_at, int | float):
        from datetime import datetime

        updated_at = datetime.fromtimestamp(updated_at).strftime("%Y-%m-%d %H:%M:%S")
    table.add_row("Updated", updated_at)

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
    if status.get("error"):
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