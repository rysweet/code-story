from typing import Any

"""Service commands for the Code Story CLI."""

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

# Import rich_click if available, otherwise create a stub
try:
    import rich_click as click
except ImportError:
    import click
from rich.console import Console
from rich.table import Table

from ..client import ServiceClient, ServiceError
from ..require_service_available import require_service_available


@click.group(help="Manage the Code Story service.")
def service() -> None:
    """Command group for service operations."""
    pass


def docker_image_needs_rebuild(service_name: str = "service") -> bool:
    """Check if the Docker image for the given service needs to be rebuilt.
    
    Compares the hash of the Dockerfile and source code.
    Returns True if the image is missing or the code has changed since the last build.
    """
    dockerfile = Path(f"Dockerfile.{service_name}")
    src_dir = Path("src/")
    hash_file = Path(f".docker_{service_name}_build_hash")
    hash_md5 = hashlib.md5()
    # Hash Dockerfile
    if dockerfile.exists():
        hash_md5.update(dockerfile.read_bytes())
    # Hash all .py files in src/
    for pyfile in src_dir.rglob("*.py"):
        hash_md5.update(pyfile.read_bytes())
    new_hash = hash_md5.hexdigest()
    # Compare to last build hash
    if not hash_file.exists() or hash_file.read_text().strip() != new_hash:
        hash_file.write_text(new_hash)
        return True
    return False


@service.command(name="start", help="Start the Code Story service.")
@click.option("--detach", "--detached", is_flag=True, help="Run the service in the background.")
@click.option("--wait", is_flag=True, help="Wait for the service to start.")
@click.option(
    "--skip-healthchecks",
    "--skip-health-checks",
    is_flag=True,
    help="Skip container healthcheck verification.",
)
@click.pass_context
def start_service(
    ctx: click.Context,
    detach: bool = False,
    wait: bool = False,
    skip_healthchecks: bool = False,
) -> None:
    """Start the Code Story service."""
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Starting Code Story service...")

    # Check current service status without raising exception
    try:
        client.check_service_health()
        console.print("[yellow]Checking if service is currently running... Yes[/]")
        console.print("[yellow]Found Code Story service running, restarting it now[/]")
        ctx.invoke(stop_service)
    except ServiceError:
        console.print("[yellow]Checking if service is currently running... No[/]")

    # Start the service with Docker Compose
    try:
        # Find the docker-compose file to use
        compose_file = find_docker_compose_file()
        if not compose_file:
            console.print("[bold red]Error:[/] Could not find docker-compose.yml file")
            sys.exit(1)

        # Check if 'docker compose' or 'docker-compose' should be used
        compose_cmd = get_docker_compose_command()

        # Build the start command
        cmd = [*compose_cmd, "-f", compose_file]

        # If skipping healthchecks, add the flag
        if skip_healthchecks:
            cmd.extend(["up", "--no-healthcheck"])
        else:
            cmd.append("up")

        if detach:
            cmd.append("-d")

        # Run the command
        console.print(f"Running command: [cyan]{' '.join(cmd)}[/]")

        try:
            # Before starting, check if rebuild is needed
            if docker_image_needs_rebuild("service"):
                console.print(
                    "[yellow]Code or Dockerfile changed. Rebuilding service image...[/yellow]"
                )
                subprocess.run(["docker", "compose", "build", "service"], check=True)

            if detach:
                subprocess.run(cmd, check=True)
                console.print("[green]Service started successfully.[/]")
                # Show status after starting in detached mode
                ctx.invoke(status)
            else:
                # If not detached, run in a separate process and wait
                subprocess.Popen(cmd)

                if wait:
                    console.print("Waiting for service to start...")
                    # Poll the health endpoint until it responds
                    max_attempts = 60  # Increase max attempts
                    for i in range(max_attempts):
                        try:
                            client.check_service_health()
                            console.print("[green]Service is now running.[/]")
                            # Show status after service is running
                            ctx.invoke(status)
                            break
                        except ServiceError:
                            if i < max_attempts - 1:  # Don't sleep on the last iteration
                                time.sleep(2)  # Longer sleep between attempts
                            else:
                                console.print(
                                    "[yellow]Service health check timed out, but containers "
                                    "might still be starting...[/]"
                                )
                                # Continue execution rather than exiting

                # If not waiting, return immediately
                console.print("[green]Service starting in background.[/]")
                # Show status after starting in foreground
                ctx.invoke(status)
                return

            console.print("[green]Service started successfully.[/]")

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error starting service:[/] {e!s}")

            # Check if the error might be related to unhealthy containers
            if "unhealthy" in str(e) and not skip_healthchecks:
                console.print(
                    "[yellow]This might be due to container health check failures. You can:[/]"
                )
                console.print(
                    "  1. Use --skip-healthchecks to start the service without health checks"
                )
                console.print("  2. Check docker logs for more details about the failure")
                console.print("\nTrying to show logs for potential unhealthy containers...")

                # Try to get logs from potentially unhealthy containers
                show_unhealthy_container_logs(compose_cmd, compose_file, console)

            sys.exit(1)

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error starting service:[/] {e!s}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error starting service:[/] {e!s}")
        sys.exit(1)


@service.command(name="stop", help="Stop the Code Story service.")
@click.pass_context
def stop_service(ctx: click.Context) -> None:
    """Stop the Code Story service."""
    ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Stopping Code Story service...")

    # Stop the service with Docker Compose
    try:
        # Find the docker-compose file to use
        compose_file = find_docker_compose_file()
        if not compose_file:
            console.print("[bold red]Error:[/] Could not find docker-compose.yml file")
            sys.exit(1)

        # Check if 'docker compose' or 'docker-compose' should be used
        compose_cmd = get_docker_compose_command()

        # Build the command
        cmd = [*compose_cmd, "-f", compose_file, "down"]

        # Run the command
        console.print(f"Running command: [cyan]{' '.join(cmd)}[/]")
        subprocess.run(cmd, check=True)

        console.print("[green]Service stopped successfully.[/]")

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error stopping service:[/] {e!s}")
        sys.exit(1)


@service.command(name="restart", help="Restart the Code Story service.")
@click.option(
    "--detach",
    "--detached",
    is_flag=True,
    help="Run the service in the background after restart.",
)
@click.option("--wait", is_flag=True, help="Wait for the service to restart completely.")
@click.option(
    "--skip-healthchecks",
    "--skip-health-checks",
    is_flag=True,
    help="Skip container healthcheck verification.",
)
@click.pass_context
def restart_service(
    ctx: click.Context,
    detach: bool = False,
    wait: bool = False,
    skip_healthchecks: bool = False,
) -> None:
    """Restart the Code Story service."""
    require_service_available()

    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Restarting Code Story service...")

    # First stop the service
    try:
        # Check if service is running first
        try:
            client.check_service_health()
        except ServiceError:
            console.print("[yellow]Service is not running, starting fresh.[/]")
            start_service(ctx, detach, wait, skip_healthchecks)
            return

        # Find the docker-compose file to use
        compose_file = find_docker_compose_file()
        if not compose_file:
            console.print("[bold red]Error:[/] Could not find docker-compose.yml file")
            sys.exit(1)

        # Check if 'docker compose' or 'docker-compose' should be used
        compose_cmd = get_docker_compose_command()

        # Build the stop command
        cmd = [*compose_cmd, "-f", compose_file, "down"]

        # Run the command
        console.print(f"Stopping service: [cyan]{' '.join(cmd)}[/]")
        subprocess.run(cmd, check=True)

        # Wait a moment for containers to fully stop
        time.sleep(2)

        # Now start the service again
        # Build the start command
        cmd = [*compose_cmd, "-f", compose_file]

        # If skipping healthchecks, add the flag
        if skip_healthchecks:
            cmd.extend(["up", "--no-healthcheck"])
        else:
            cmd.append("up")

        if detach:
            cmd.append("-d")

        # Run the command
        console.print(f"Starting service: [cyan]{' '.join(cmd)}[/]")

        try:
            # Before starting, check if rebuild is needed
            if docker_image_needs_rebuild("service"):
                console.print(
                    "[yellow]Code or Dockerfile changed. Rebuilding service image...[/yellow]"
                )
                subprocess.run(["docker", "compose", "build", "service"], check=True)

            if detach:
                subprocess.run(cmd, check=True)
                console.print("[green]Service started successfully.[/]")
                # Show status after starting in detached mode
                ctx.invoke(status)
            else:
                # If not detached, run in a separate process
                subprocess.Popen(cmd)

            if wait:
                console.print("Waiting for service to start...")

                # Poll the health endpoint until it responds
                max_attempts = 60  # Increased from 30
                for i in range(max_attempts):
                    try:
                        client.check_service_health()
                        console.print("[green]Service restarted successfully.[/]")
                        # Show status after service is running
                        ctx.invoke(status)
                        break
                    except ServiceError:
                        if i < max_attempts - 1:  # Don't sleep on the last iteration
                            time.sleep(2)  # Increased from 1
                        else:
                            console.print(
                                "[yellow]Service health check timed out, but containers "
                                "might still be starting...[/]"
                            )
            else:
                console.print("[green]Service restart initiated.[/]")

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error restarting service:[/] {e!s}")

            # Check if the error might be related to unhealthy containers
            if "unhealthy" in str(e) and not skip_healthchecks:
                console.print(
                    "[yellow]This might be due to container health check failures. You can:[/]"
                )
                console.print(
                    "  1. Use --skip-healthchecks to restart the service without health checks"
                )
                console.print("  2. Try 'codestory service recover' to fix unhealthy containers")
                console.print("  3. Check docker logs for more details about the failure")

                # Try to show logs for potentially unhealthy containers
                show_unhealthy_container_logs(compose_cmd, compose_file, console)

            sys.exit(1)

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error restarting service:[/] {e!s}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error restarting service:[/] {e!s}")
        sys.exit(1)


@service.command(name="status", help="Show the status of the Code Story service.")
@click.option(
    "--renew-auth",
    "--renew-credentials",
    "--renew",
    is_flag=True,
    help="Automatically renew Azure credentials if needed.",
)
@click.pass_context
def status(ctx: click.Context, renew_auth: bool = False) -> None:
    """Show the status of the Code Story service.

    Args:
        ctx: The Click context object.
        renew_auth: If True, automatically renew Azure credentials if needed.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Checking Code Story service status...")

    auto_renew = renew_auth  # CLI flag always triggers auto-renew
    try:
        health = client.check_service_health(auto_fix=False)
        openai = health.get("components", {}).get("openai", {})
        if (
            openai.get("status") == "unhealthy"
            and openai.get("details", {}).get("type") == "AuthenticationError"
        ):
            auto_renew = True
            # Run az login directly in the user's shell for interactive auth
            tenant_id = openai.get("details", {}).get("tenant_id")
            renewal_cmd = [
                "az",
                "login",
                "--scope",
                "https://cognitiveservices.azure.com/.default",
            ]
            if tenant_id:
                renewal_cmd.extend(["--tenant", tenant_id])
            console.print(
                "[yellow]Azure credentials expired. Launching interactive Azure login...[/yellow]"
            )
            import subprocess

            subprocess.run(renewal_cmd, check=True)
            console.print("[green]Azure login complete. Injecting tokens into containers...")
            ctx.invoke(renew_azure_auth, tenant=tenant_id, inject=True)
            # After renewal, re-check health
            health = client.check_service_health(auto_fix=False)
            console.print(
                "[green]Azure authentication renewed. Service health after renewal:[/green]"
            )
    except ServiceError as e:
        if "Azure authentication credentials expired" in str(e):
            auto_renew = True
            # Fallback: run az login without tenant
            console.print(
                "[yellow]Azure credentials expired. Launching interactive Azure login...[/yellow]"
            )
            import subprocess

            subprocess.run(
                [
                    "az",
                    "login",
                    "--scope",
                    "https://cognitiveservices.azure.com/.default",
                ],
                check=True,
            )
            console.print("[green]Azure login complete. Injecting tokens into containers...")
            ctx.invoke(renew_azure_auth, inject=True)
            health = client.check_service_health(auto_fix=False)
            console.print(
                "[green]Azure authentication renewed. Service health after renewal:[/green]"
            )
        else:
            raise

    if auto_renew:
        console.print(
            "[yellow]Azure credentials expired or renewal requested. "
            "Attempting automatic renewal...[/yellow]"
        )
        # Call the CLI auth-renew command (in-process)
        ctx.invoke(renew_azure_auth)
        # After renewal, re-check health
        try:
            health = client.check_service_health(auto_fix=False)
            console.print(
                "[green]Azure authentication renewed. Service health after renewal:[/green]"
            )
        except ServiceError as e:
            console.print(f"[red]Service health check failed after renewal: {e}[/red]")
            return
    else:
        health = client.check_service_health(auto_fix=False)

    # Create status table
    table = Table(title="Service Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="magenta")

    # Add overall status
    overall_status = health.get("status", "unknown")
    status_style = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}.get(
        overall_status.lower(), "white"
    )
    table.add_row(
        "Service Overall",
        f"[{status_style}]{overall_status}[/]",
        health.get("timestamp", ""),
    )

    # Add components to table if they exist
    if "components" in health:
        for component_name, component_data in health["components"].items():
            status = component_data.get("status", "unknown")
            status_style = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
            }.get(status.lower(), "white")

            # Get details from component data if available
            details = ""
            if "details" in component_data and isinstance(component_data["details"], dict):
                if "message" in component_data["details"]:
                    details = component_data["details"]["message"]
                elif "error" in component_data["details"]:
                    details = component_data["details"]["error"]
                elif component_name.lower() == "celery":
                    # Add specific details for Celery
                    active_workers = component_data["details"].get("active_workers", 0)
                    registered_tasks = component_data["details"].get("registered_tasks", 0)
                    details = f"Workers: {active_workers}, Tasks: {registered_tasks}"
                elif component_name.lower() == "redis":
                    # Add specific details for Redis
                    connection = component_data["details"].get("connection", "")
                    details = f"Connection: {connection}"

            # Add the component row to the table
            table.add_row(
                component_name.capitalize(),
                f"[{status_style}]{status.capitalize()}[/]",
                details,
            )

    # Add missing important components if they're not in the response
    important_components = {"redis", "celery", "neo4j"}
    existing_components = (
        set() if "components" not in health else {c.lower() for c in health["components"]}
    )

    for component in important_components - existing_components:
        table.add_row(
            component.capitalize(),
            "[yellow]Unknown[/]",
            "Status information not available",
        )

    # Print table and service info
    console.print(table)
    version = health.get('version', 'unknown')
    uptime = health.get('uptime', 0)
    console.print(
        f"[green]Service is running.[/] Version: {version}, Uptime: {uptime} seconds"
    )

    # Check Docker container status regardless of API health
    console.print("\n[bold]Docker Container Status:[/]")

    # Check if Docker is available
    try:
        process = subprocess.run(
            ["docker", "ps"],
            check=False,
            capture_output=True,
        )
        docker_available = process.returncode == 0
    except Exception:
        docker_available = False

    if not docker_available:
        console.print("[yellow]Docker is not available or running.[/]")
    else:
        # Get all relevant running containers
        containers = get_running_containers()

        if not containers:
            console.print("[yellow]No Code Story containers are currently running.[/]")
            console.print("Use 'codestory service start' to start the service.")
        else:
            container_table = Table(title="Container Status")
            container_table.add_column("Container", style="cyan")
            container_table.add_column("Status", style="green")
            container_table.add_column("Health", style="magenta")
            # Check status of each container
            for container in containers:
                try:
                    # Get container status
                    status_process = subprocess.run(
                        [
                            "docker",
                            "inspect",
                            "--format",
                            "{{.State.Status}}",
                            container,
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    # Get health status if available
                    health_process = subprocess.run(
                        [
                            "docker",
                            "inspect",
                            "--format",
                            "{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}",
                            container,
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    if status_process.returncode == 0:
                        container_status = status_process.stdout.strip()
                        status_style = "green" if container_status == "running" else "yellow"
                    else:
                        container_status = "unknown"
                        status_style = "red"

                    if health_process.returncode == 0:
                        health_status = health_process.stdout.strip()
                        health_style = {
                            "healthy": "green",
                            "unhealthy": "red",
                            "starting": "yellow",
                            "N/A": "white",
                        }.get(health_status, "white")
                    else:
                        health_status = "unknown"
                        health_style = "red"

                    # Add row to table
                    container_table.add_row(
                        container,
                        f"[{status_style}]{container_status}[/]",
                        f"[{health_style}]{health_status}[/]",
                    )
                except Exception as e:
                    container_table.add_row(
                        container,
                        "[red]error[/]",
                        f"[red]Error checking status: {e!s}[/]",
                    )

            # Print the table
            console.print(container_table)

            # Check if any containers are unhealthy
            unhealthy_containers: list[Any] = []
            try:
                process = subprocess.run(  # TODO: Fix type compatibility  # type: ignore[assignment]
                    [
                        "docker",
                        "ps",
                        "--filter",
                        "health=unhealthy",
                        "--format",
                        "{{.Names}}",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if process.returncode == 0:
                    unhealthy_containers = [
                        c for c in process.stdout.strip().split("\n") if c and c in containers  # type: ignore[assignment]
                    ]
            except Exception:
                pass

            if unhealthy_containers:
                console.print(
                    f"\n[bold red]Warning:[/] The following containers are unhealthy: "
                    f"{', '.join(unhealthy_containers)}"
                )
                console.print(
                    "Use 'codestory service recover' to attempt automatic recovery"
                )

    # Provide advice based on status
    if docker_available and containers:
        console.print(
            "\n[yellow]The service containers are running but the API is not "
            "responding.[/]"
        )
        console.print(
            "This might indicate that the service is still starting up or there's "
            "an issue with the service container."
        )
        console.print("Suggestions:")
        console.print("  1. Wait a bit longer for startup to complete (can take up to 2-3 minutes)")
        console.print("  2. Run 'codestory service recover' to try restarting unhealthy containers")
        console.print(
            "  3. Run 'codestory service restart --skip-healthchecks' to restart "
            "without health checks"
        )
        console.print("  4. Check container logs with 'docker logs codestory-service'")
        sys.exit(1)


def find_docker_compose_file() -> str | None:
    """Find the docker-compose file to use.

    Tries different variants and locations of the docker-compose file.

    Returns:
        The path to the docker-compose file, or None if not found.
    """
    # Try different variants of the docker-compose file name
    compose_file_names = [
        "docker-compose.yml",
        "docker-compose.yaml",
        "docker-compose.dev.yml",
        "docker-compose.dev.yaml",
        "docker-compose.local.yml",
        "docker-compose.local.yaml",
    ]

    # First look in the current directory
    for filename in compose_file_names:
        if os.path.exists(filename):
            return filename

    # Then try looking in the project root
    try:
        from codestory.config.settings import get_project_root

        project_root = get_project_root()
        for filename in compose_file_names:
            file_path = os.path.join(project_root, filename)
            if os.path.exists(file_path):
                return file_path
    except Exception:
        pass

    # If no file is found, return None
    return None


def get_docker_compose_command() -> list[str]:
    """Get the appropriate docker compose command.

    Checks if 'docker compose' or 'docker-compose' should be used.

    Returns:
        The command to use for docker compose.
    """
    # Try 'docker compose' (newer approach)
    try:
        process = subprocess.run(
            ["docker", "compose", "version"],
            check=False,
            capture_output=True,
        )
        if process.returncode == 0:
            return ["docker", "compose"]
    except Exception:
        pass

    # Fall back to 'docker-compose' (older approach)
    try:
        process = subprocess.run(
            ["docker-compose", "version"],
            check=False,
            capture_output=True,
        )
        if process.returncode == 0:
            return ["docker-compose"]
    except Exception:
        pass

    # Default to 'docker compose' and hope it works
    return ["docker", "compose"]


@service.command(name="auth-renew", help="Renew Azure authentication tokens across all containers.")
@click.option("--tenant", help="Specify Azure tenant ID.")
@click.option("--check", is_flag=True, help="Only check authentication status without renewing.")
@click.option("--inject", is_flag=True, help="Inject tokens into containers after authentication.")
@click.option("--restart", is_flag=True, help="Restart containers after token injection.")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed output from the renewal process.",
)
@click.pass_context
def renew_azure_auth(
    ctx: click.Context,
    tenant: str | None = None,
    check: bool = False,
    inject: bool = True,
    restart: bool = False,
    verbose: bool = False,
) -> None:
    """Renew Azure authentication tokens across all containers.

    This command will:
    1. Check if there are Azure authentication issues
    2. Run az login if needed
    3. Inject the authentication tokens into all Code Story containers
    4. Optionally restart containers to ensure they use the new tokens

    Args:
        ctx: The Click context object.
        tenant: Optional tenant ID to use for login
        check: Only check auth status without renewing
        inject: Inject tokens into containers after authentication
        restart: Restart containers after token injection
        verbose: Show detailed output
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("[bold]Azure Authentication Renewal[/]")

    # Build the command to run the token injection script
    script_path = os.path.join(os.path.dirname(__file__), "../../../scripts/inject_azure_tokens.py")

    # Check if we can find the script
    if not os.path.exists(script_path):
        # Try to find it relative to project root
        try:
            from codestory.config.settings import get_project_root

            script_path = os.path.join(get_project_root(), "scripts/inject_azure_tokens.py")
        except Exception:
            # Fallback to absolute path based on current file
            script_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "../../../../scripts/inject_azure_tokens.py",
                )
            )

    # Build the command arguments
    cmd = [sys.executable, script_path]

    if tenant:
        cmd.extend(["--tenant-id", tenant])
    if restart:
        cmd.append("--restart-containers")
    if verbose:
        cmd.append("--verbose")

    # Check if we're running inside a container
    inside_container = os.path.exists("/.dockerenv")

    if inside_container:
        # We're inside a container, run the script directly
        console.print("Running azure token injection inside container...")
        try:
            if verbose:
                # Run with output shown
                process = subprocess.run(cmd, check=False)
                success = process.returncode == 0
            else:
                # Capture output
                process = subprocess.run(  # TODO: Fix type compatibility  # type: ignore[assignment]
                    cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                success = process.returncode == 0

                # Show the output if successful
                if success and process.stdout:
                    console.print(process.stdout)

                # Show a summary if not successful
                if not success:
                    console.print("[red]Azure authentication renewal failed.[/]")
                    console.print("Run with --verbose for full output.")
                    # Show the last few lines of the error
                    if process.stderr:
                        error_lines = process.stderr.strip().split("\n")[-5:]  # type: ignore[assignment]
                        console.print("\n[bold red]Error output:[/]")
                        for line in error_lines:
                            console.print(f"  {line}")

            if success:
                console.print("[green]Azure authentication tokens updated successfully.[/]")
            else:
                sys.exit(1)

        except Exception as e:
            console.print(f"[bold red]Error running token injection: {e!s}[/]")
            sys.exit(1)
    else:
        # We're on the host, access the API or run the script directly
        if inject:
            # Try to call the auth-renew endpoint first if service is running
            try:
                # Check if service is running
                health = client.check_service_health(timeout=5)

                # Call the auth-renew endpoint
                console.print("Service is running, calling auth-renew API endpoint...")

                # Build the URL with query parameters
                url = f"{client.base_url}/auth-renew"
                params: list[Any] = []
                if tenant:
                    params.append(f"tenant_id={tenant}")
                if restart:
                    params.append("restart_containers=true")

                if params:
                    url += "?" + "&".join(params)

                # Send the request
                response = client.session.get(url)

                if response.status_code == 200:
                    result = response.json()

                    # Display the login command if provided
                    if "login_command" in result:
                        # Add tenant ID context if available
                        if "auth_message" in result:
                            console.print(f"\n[bold]{result['auth_message']}[/]")

                        console.print("\n[bold]Azure authentication required:[/]")
                        console.print(f"[cyan]{result['login_command']}[/]\n")

                        # Add more context from the auth details if available
                        if "auth_details" in result and isinstance(result["auth_details"], dict):
                            auth_details = result["auth_details"]
                            if "tenant_id" in auth_details:
                                console.print(f"[bold]Tenant ID:[/] {auth_details['tenant_id']}")
                            if "scope" in auth_details:
                                console.print(f"[bold]Scope:[/] {auth_details['scope']}")
                            if "tenant_source" in result:
                                console.print(f"[bold]Source:[/] {result['tenant_source']}")
                            console.print("")

                        # Run the login command if --verbose is used
                        if verbose:
                            console.print("Executing login command automatically...")
                            login_cmd = result["login_command"].split()
                            try:
                                subprocess.run(login_cmd, check=True)
                                console.print("[green]Authentication successful![/]")

                                # Call the endpoint again to inject tokens
                                console.print("Injecting tokens into containers...")
                                response = client.session.get(url)
                                if response.status_code == 200:
                                    console.print("[green]Token injection completed.[/]")
                                else:
                                    console.print(
                                        f"[yellow]Token injection returned status code "
                                        f"{response.status_code}[/]"
                                    )

                            except Exception as e:
                                console.print(f"[red]Error during authentication: {e!s}[/]")
                                console.print("Please run the command manually.")

                    # Check token injection status
                    if "token_injection" in result:
                        token_result = result["token_injection"]
                        if "status" in token_result:
                            status = token_result["status"]
                            if status == "success":
                                console.print("[green]Token injection successful![/]")
                            else:
                                console.print(f"[yellow]Token injection status: {status}[/]")

                                # Show error details if available
                                if "error" in token_result:
                                    console.print(f"[red]Error: {token_result['error']}[/]")

                                # Fallback to manual script execution
                                console.print("Falling back to direct script execution...")

                    console.print("[green]Authentication renewal process completed via API.[/]")

                    # Check OpenAI component status
                    try:
                        health = client.check_service_health()
                        if "components" in health and "openai" in health["components"]:
                            openai_status = health["components"]["openai"].get("status")
                            if openai_status == "healthy":
                                console.print("[green]OpenAI component is now healthy![/]")
                            else:
                                console.print(
                                    f"[yellow]OpenAI component status: {openai_status}[/]"
                                )
                    except Exception:
                        pass

                    # Exit early if the API call succeeded
                    return
                else:
                    console.print(f"[yellow]API returned status code {response.status_code}[/]")
                    console.print("Falling back to direct script execution...")
            except Exception as e:
                console.print(f"[yellow]Could not use API for token renewal: {e!s}[/]")
                console.print("Running token injection script directly...")

        # Run the script directly if API approach failed or wasn't attempted
        try:
            # Make sure the script is executable
            if os.path.exists(script_path):
                try:
                    os.chmod(script_path, 0o755)  # Make executable
                except Exception:
                    pass  # Ignore permission errors

            # Run the script with the appropriate arguments
            if verbose:
                process = subprocess.run(cmd, check=False)
                success = process.returncode == 0
            else:
                process = subprocess.run(  # TODO: Fix type compatibility  # type: ignore[assignment]
                    cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                success = process.returncode == 0

                # Show the output if successful
                if success and process.stdout:
                    console.print(process.stdout)

                # Show errors if not successful
                if not success:
                    console.print("[red]Token injection failed.[/]")
                    console.print("Run with --verbose for full output.")
                    if process.stderr:
                        error_lines = process.stderr.strip().split("\n")[-5:]  # type: ignore[assignment]
                        console.print("\n[bold red]Error output:[/]")
                        for line in error_lines:
                            console.print(f"  {line}")
                    sys.exit(1)

            if success:
                console.print("[green]Azure authentication renewed successfully.[/]")

                # Check service health after token injection
                try:
                    console.print("Checking service health after token injection...")
                    try:
                        health = client.check_service_health(timeout=5)

                        # Check OpenAI component
                        if "components" in health and "openai" in health["components"]:
                            openai_status = health["components"]["openai"].get("status", "unknown")
                            if openai_status == "healthy":
                                console.print("[green]OpenAI component is now healthy![/]")
                            else:
                                console.print(
                                    f"[yellow]OpenAI component status: {openai_status}[/]"
                                )
                                console.print("Token injection might not have fixed all issues.")
                        else:
                            console.print("[yellow]Could not verify OpenAI component health.[/]")
                    except Exception as inner_e:
                        console.print(f"[yellow]Could not check service health: {inner_e!s}[/]")
                except Exception as e:
                    console.print(f"[yellow]Error during token injection: {e!s}[/]")
        except Exception as e:
            console.print(f"[bold red]Error running token injection: {e!s}[/]")
            sys.exit(1)


@service.command(name="recover", help="Recover from unhealthy container state.")
@click.option("--force", "-f", is_flag=True, help="Force recovery by removing all containers.")
@click.option(
    "--restart-worker",
    "--restart-workers",
    is_flag=True,
    help="Only restart the worker container.",
)
@click.pass_context
def recover_service(ctx: click.Context, force: bool = False, restart_worker: bool = False) -> None:
    """
    Recover the service from unhealthy container state.

    This command attempts to fix issues with unhealthy containers by:
    1. Identifying unhealthy containers
    2. Showing their logs
    3. Either restarting specific containers or forcing a complete reset
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("[bold]Starting Code Story service recovery...[/]")

    # Find the docker-compose file
    compose_file = find_docker_compose_file()
    if not compose_file:
        console.print("[bold red]Error:[/] Could not find docker-compose.yml file")
        sys.exit(1)

    # Get docker compose command
    compose_cmd = get_docker_compose_command()

    # Identify unhealthy containers
    unhealthy_containers: list[Any] = []
    try:
        process = subprocess.run(
            ["docker", "ps", "--filter", "health=unhealthy", "--format", "{{.Names}}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode == 0:
            unhealthy_containers = [c for c in process.stdout.strip().split("\n") if c]
    except Exception as e:
        console.print(f"[yellow]Could not identify unhealthy containers: {e!s}[/]")

    # If specifically requested to restart worker only
    if restart_worker:
        console.print("[bold]Attempting to restart worker container...[/]")
        try:
            # Try to restart the worker container
            worker_container = "codestory-worker"
            subprocess.run(["docker", "restart", worker_container], check=True)
            console.print(f"[green]Successfully restarted {worker_container}[/]")

            # Wait a bit for the container to initialize
            console.print("Waiting for worker to initialize...")
            time.sleep(5)

            # Check worker health
            process = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    worker_container,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if process.returncode == 0:
                health_status = process.stdout.strip()
                if health_status == "healthy":
                    console.print("[green]Worker container is now healthy![/]")
                else:
                    console.print(f"[yellow]Worker container status: {health_status}[/]")
                    console.print("Showing worker logs for debugging:")
                    subprocess.run(["docker", "logs", worker_container], check=False)
            else:
                console.print("[yellow]Could not check worker health status[/]")
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error restarting worker container: {e!s}[/]")
            console.print("[yellow]Trying a full service recovery instead...[/]")
            force = True  # Fall back to force recovery
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {e!s}[/]")
            force = True  # Fall back to force recovery

    # If unhealthy containers were found or force is specified
    if unhealthy_containers or force:
        if force:
            console.print(
                "[bold]Force recovery requested. Stopping all containers and removing orphans...[/]"
            )

            # Stop all containers, remove orphans and volumes
            try:
                # First try with docker compose
                cmd = [*compose_cmd, "-f", compose_file, "down", "--remove-orphans"]
                console.print(f"Running: [cyan]{' '.join(cmd)}[/]")
                subprocess.run(cmd, check=True)

                # Make sure all containers are truly stopped
                containers = get_running_containers()
                if containers:
                    console.print(
                        "[yellow]Some containers are still running. Stopping them manually...[/]"
                    )
                    for container in containers:
                        try:
                            console.print(f"Stopping container: {container}")
                            subprocess.run(["docker", "stop", container], check=True)
                        except Exception as e:
                            console.print(f"[red]Could not stop container {container}: {e!s}[/]")
            except Exception as e:
                console.print(f"[red]Error stopping containers: {e!s}[/]")

            # Wait a moment for everything to settle
            console.print("Waiting for containers to stop...")
            time.sleep(3)

            # Start the service again
            console.print("[bold]Starting service...[/]")

            # Try with environment variable approach
            env = os.environ.copy()
            env["COMPOSE_DOCKER_CLI_NO_HEALTHCHECK"] = "1"

            cmd = [*compose_cmd, "-f", compose_file, "up", "-d"]
            console.print(f"Running: [cyan]{' '.join(cmd)}[/]")
            try:
                subprocess.run(cmd, check=True, env=env)
                console.print(
                    "[green]Service started with health checks disabled via "
                    "environment variable.[/]"
                )
                console.print("[yellow]Note: Service may take longer to fully initialize.[/]")
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]Error starting service: {e!s}[/]")

                # Fall back to normal startup if environment variable approach fails
                console.print("Falling back to normal startup...")
                cmd = [*compose_cmd, "-f", compose_file, "up", "-d"]
                try:
                    subprocess.run(cmd, check=True)
                    console.print("[green]Service started normally.[/]")
                except subprocess.CalledProcessError as e:
                    console.print(f"[bold red]Error starting service: {e!s}[/]")
                    sys.exit(1)
        else:
            # Targeted recovery for specific unhealthy containers
            console.print(f"[bold]Found unhealthy containers: {', '.join(unhealthy_containers)}[/]")

            # Show logs for unhealthy containers
            for container in unhealthy_containers:
                console.print(f"\n[bold cyan]Logs for {container}:[/]")
                subprocess.run(["docker", "logs", "--tail", "20", container], check=False)

            # Restart unhealthy containers
            console.print("\n[bold]Attempting to restart unhealthy containers...[/]")
            for container in unhealthy_containers:
                try:
                    console.print(f"Restarting container: {container}")
                    subprocess.run(["docker", "restart", container], check=True)
                    console.print(f"[green]Successfully restarted {container}[/]")
                except subprocess.CalledProcessError as e:
                    console.print(f"[red]Error restarting {container}: {e!s}[/]")

            # Wait a bit for containers to initialize
            console.print("Waiting for containers to initialize...")
            time.sleep(5)

            # Check if containers are now healthy
            all_healthy = True
            for container in unhealthy_containers:
                process = subprocess.run(
                    [
                        "docker",
                        "inspect",
                        "--format",
                        "{{.State.Health.Status}}",
                        container,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if process.returncode == 0:
                    health_status = process.stdout.strip()
                    if health_status != "healthy":
                        all_healthy = False
                        console.print(f"[yellow]Container {container} is still {health_status}[/]")
                else:
                    all_healthy = False
                    console.print(f"[yellow]Could not check health status of {container}[/]")

            if all_healthy:
                console.print("[green bold]All containers are now healthy![/]")
            else:
                console.print(
                    "[yellow]Some containers are still not healthy. Consider using "
                    "--force to perform a full recovery.[/]"
                )
    else:
        console.print("[green]No unhealthy containers found.[/]")

        # Check if service is running properly
        try:
            client.check_service_health()
            console.print("[green]Service is running correctly.[/]")
        except ServiceError:
            console.print("[yellow]Service is not responding despite no unhealthy containers.[/]")
            console.print("Checking all service containers...")

            # List all service containers
            try:
                cmd = [*compose_cmd, "-f", compose_file, "ps"]
                subprocess.run(cmd, check=True)

                # Suggest a restart if needed
                console.print(
                    "\n[yellow]Consider restarting the service with: 'codestory service restart'[/]"
                )
            except Exception as e:
                console.print(f"[red]Error checking service containers: {e!s}[/]")
                console.print(
                    "[yellow]Try a force recovery with: 'codestory service recover --force'[/]"
                )

    console.print("[bold]Recovery process completed.[/]")


def get_running_containers() -> list[str]:
    """Get a list of running containers that might be part of the service.

    Returns:
        List of container names.
    """
    try:
        # Run docker ps to get running containers
        process = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            check=False,
            capture_output=True,
            text=True,
        )

        if process.returncode == 0:
            # Filter for containers that might be part of the service
            containers = process.stdout.strip().split("\n")
            return [
                c
                for c in containers
                if c
                and (
                    "codestory" in c.lower()
                    or "neo4j" in c.lower()
                    or "redis" in c.lower()
                    or "service" in c.lower()
                    or "worker" in c.lower()
                )
            ]
    except Exception:
        pass

    return []


def show_unhealthy_container_logs(
    compose_cmd: list[str], compose_file: str, console: Console
) -> None:
    """Show logs for potentially unhealthy containers.

    Args:
        compose_cmd: The docker compose command to use.
        compose_file: Path to the docker-compose file.
        console: Rich console for output.
    """
    try:
        # Get a list of all containers in the compose project
        ps_cmd = [*compose_cmd, "-f", compose_file, "ps", "--format", "json"]
        process = subprocess.run(
            ps_cmd,
            check=False,
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            console.print("[yellow]Could not get container status information[/]")
            return

        # Parse the output to find containers
        container_lines = process.stdout.strip().split("\n")
        unhealthy_containers: list[Any] = []

        # Try to parse each line as JSON
        import json

        for line in container_lines:
            try:
                container_info = json.loads(line)
                if "Name" in container_info:
                    container_name = container_info["Name"]
                    # Check if the container is unhealthy
                    if "State" in container_info and "Health" in container_info["State"]:
                        health_status = container_info["State"]["Health"].get("Status")
                        if health_status == "unhealthy":
                            unhealthy_containers.append(container_name)
                            console.print(f"[red]Container {container_name} is unhealthy.[/]")

                            # Show the last few lines of the container logs
                            if "LogPath" in container_info["GraphDriver"]:
                                log_path = container_info["GraphDriver"]["LogPath"]
                                console.print(f"  Log file: {log_path}")
                                try:
                                    # Show last 10 lines of the log file
                                    with open(log_path) as log_file:
                                        # Seek to the end of the file
                                        log_file.seek(0, os.SEEK_END)
                                        # Read the last 10 lines
                                        for _ in range(10):
                                            line = log_file.readline()
                                            if not line:
                                                break  # EOF
                                            console.print(f"  {line.strip()}")
                                except Exception as e:
                                    console.print(f"  [red]Error reading log file: {e!s}[/]")
            except Exception as e:
                console.print(f"[red]Error parsing container info: {e!s}[/]")
                continue

        if not unhealthy_containers:
            console.print("[green]All containers are healthy.[/]")
    except Exception as e:
        console.print(f"[red]Error showing unhealthy container logs: {e!s}[/]")