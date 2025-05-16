"""
Service commands for the Code Story CLI.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

import click

# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    import click as rich_click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..client import ServiceClient, ServiceError


@click.group(help="Manage the Code Story service.")
def service() -> None:
    """Command group for service operations."""
    pass


@service.command(name="start", help="Start the Code Story service.")
@click.option("--detach", "--detached", is_flag=True, help="Run the service in the background.")
@click.option("--wait", is_flag=True, help="Wait for the service to start.")
@click.option("--skip-healthchecks", "--skip-health-checks", is_flag=True, help="Skip container healthcheck verification.")
@click.pass_context
def start_service(ctx: click.Context, detach: bool = False, wait: bool = False, skip_healthchecks: bool = False) -> None:
    """
    Start the Code Story service.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Starting Code Story service...")

    # Check if service is already running
    try:
        health = client.check_service_health()
        console.print("[yellow]Service is already running.[/]")
        return
    except ServiceError:
        # Service is not running, continue
        pass

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
            if detach:
                subprocess.run(cmd, check=True)
            else:
                # If not detached, run in a separate process and wait
                process = subprocess.Popen(cmd)

                if wait:
                    console.print("Waiting for service to start...")
                    # Poll the health endpoint until it responds
                    max_attempts = 60  # Increase max attempts
                    for i in range(max_attempts):
                        try:
                            client.check_service_health()
                            console.print("[green]Service is now running.[/]")
                            break
                        except ServiceError:
                            if i < max_attempts - 1:  # Don't sleep on the last iteration
                                time.sleep(2)  # Longer sleep between attempts
                            else:
                                console.print("[yellow]Service health check timed out, but containers might still be starting...[/]")
                                # Continue execution rather than exiting

                    return

                # If not waiting, return immediately
                console.print("[green]Service starting in background.[/]")
                return

            console.print("[green]Service started successfully.[/]")

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error starting service:[/] {str(e)}")
            
            # Check if the error might be related to unhealthy containers
            if "unhealthy" in str(e) and not skip_healthchecks:
                console.print("[yellow]This might be due to container health check failures. You can:[/]")
                console.print("  1. Use --skip-healthchecks to start the service without health checks")
                console.print("  2. Check docker logs for more details about the failure")
                console.print("\nTrying to show logs for potential unhealthy containers...")
                
                # Try to get logs from potentially unhealthy containers
                show_unhealthy_container_logs(compose_cmd, compose_file, console)
            
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error starting service:[/] {str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error starting service:[/] {str(e)}")
        sys.exit(1)


@service.command(name="stop", help="Stop the Code Story service.")
@click.pass_context
def stop_service(ctx: click.Context) -> None:
    """
    Stop the Code Story service.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Stopping Code Story service...")

    # Check if service is running
    try:
        health = client.check_service_health()
    except ServiceError:
        console.print("[yellow]Service is not running.[/]")
        return

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
        console.print(f"[bold red]Error stopping service:[/] {str(e)}")
        sys.exit(1)


@service.command(name="restart", help="Restart the Code Story service.")
@click.option("--detach", "--detached", is_flag=True, help="Run the service in the background after restart.")
@click.option("--wait", is_flag=True, help="Wait for the service to restart completely.")
@click.option("--skip-healthchecks", "--skip-health-checks", is_flag=True, help="Skip container healthcheck verification.")
@click.pass_context
def restart_service(ctx: click.Context, detach: bool = False, wait: bool = False, skip_healthchecks: bool = False) -> None:
    """
    Restart the Code Story service.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Restarting Code Story service...")

    # First stop the service
    try:
        # Check if service is running first
        try:
            health = client.check_service_health()
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
            if detach:
                subprocess.run(cmd, check=True)
            else:
                # If not detached, run in a separate process
                process = subprocess.Popen(cmd)

            if wait:
                console.print("Waiting for service to start...")

                # Poll the health endpoint until it responds
                max_attempts = 60  # Increased from 30
                for i in range(max_attempts):
                    try:
                        client.check_service_health()
                        console.print("[green]Service restarted successfully.[/]")
                        break
                    except ServiceError:
                        if i < max_attempts - 1:  # Don't sleep on the last iteration
                            time.sleep(2)  # Increased from 1
                        else:
                            console.print("[yellow]Service health check timed out, but containers might still be starting...[/]")
            else:
                console.print("[green]Service restart initiated.[/]")
                
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error restarting service:[/] {str(e)}")
            
            # Check if the error might be related to unhealthy containers
            if "unhealthy" in str(e) and not skip_healthchecks:
                console.print("[yellow]This might be due to container health check failures. You can:[/]")
                console.print("  1. Use --skip-healthchecks to restart the service without health checks")
                console.print("  2. Try 'codestory service recover' to fix unhealthy containers")
                console.print("  3. Check docker logs for more details about the failure")
                
                # Try to show logs for potentially unhealthy containers
                show_unhealthy_container_logs(compose_cmd, compose_file, console)
            
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error restarting service:[/] {str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error restarting service:[/] {str(e)}")
        sys.exit(1)


@service.command(name="status", help="Show the status of the Code Story service.")
@click.pass_context
def status(ctx: click.Context) -> None:
    """
    Show the status of the Code Story service.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]

    console.print("Checking Code Story service status...")

    # Check service API health first
    service_api_healthy = False
    try:
        health = client.check_service_health()
        service_api_healthy = True

        # Create status table
        table = Table(title="Service Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="magenta")

        # Add overall status
        overall_status = health.get("status", "unknown")
        status_style = {
            "healthy": "green",
            "degraded": "yellow", 
            "unhealthy": "red"
        }.get(overall_status.lower(), "white")
        table.add_row(
            "Service Overall",
            f"[{status_style}]{overall_status}[/]",
            health.get("timestamp", "")
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
                    details
                )
        
        # Add missing important components if they're not in the response
        important_components = {"redis", "celery", "neo4j"}
        existing_components = set() if "components" not in health else set(c.lower() for c in health["components"].keys())
        
        for component in important_components - existing_components:
            table.add_row(
                component.capitalize(),
                "[yellow]Unknown[/]",
                "Status information not available"
            )

        # Print table and service info
        console.print(table)
        console.print(
            f"[green]Service is running.[/] Version: {health.get('version', 'unknown')}, Uptime: {health.get('uptime', 0)} seconds"
        )

    except ServiceError as e:
        console.print(f"[bold red]Service API is not responding:[/] {str(e)}")
        service_api_healthy = False
    
    # Check Docker container status regardless of API health
    console.print("\n[bold]Docker Container Status:[/]")
    
    # Check if Docker is available
    try:
        process = subprocess.run(
            ["docker", "ps"], 
            check=False, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
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
            # Create container status table
            container_table = Table(title="Container Status")
            container_table.add_column("Container", style="cyan")
            container_table.add_column("Status", style="green")
            container_table.add_column("Health", style="magenta")
            
            # Check status of each container
            for container in containers:
                try:
                    # Get container status
                    status_process = subprocess.run(
                        ["docker", "inspect", "--format", "{{.State.Status}}", container],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Get health status if available
                    health_process = subprocess.run(
                        ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}", container],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
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
                            "N/A": "white"
                        }.get(health_status, "white")
                    else:
                        health_status = "unknown"
                        health_style = "red"
                    
                    # Add row to table
                    container_table.add_row(
                        container,
                        f"[{status_style}]{container_status}[/]",
                        f"[{health_style}]{health_status}[/]"
                    )
                except Exception as e:
                    container_table.add_row(
                        container,
                        "[red]error[/]",
                        f"[red]Error checking status: {str(e)}[/]"
                    )
            
            # Print the table
            console.print(container_table)
            
            # Check if any containers are unhealthy
            unhealthy_containers = []
            try:
                process = subprocess.run(
                    ["docker", "ps", "--filter", "health=unhealthy", "--format", "{{.Names}}"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if process.returncode == 0:
                    unhealthy_containers = [c for c in process.stdout.strip().split('\n') if c and c in containers]
            except Exception:
                pass
            
            if unhealthy_containers:
                console.print(f"\n[bold red]Warning:[/] The following containers are unhealthy: {', '.join(unhealthy_containers)}")
                console.print("Use 'codestory service recover' to attempt automatic recovery")
    
    # Provide advice based on status
    if not service_api_healthy and docker_available and containers:
        console.print("\n[yellow]The service containers are running but the API is not responding.[/]")
        console.print("This might indicate that the service is still starting up or there's an issue with the service container.")
        console.print("Suggestions:")
        console.print("  1. Wait a bit longer for startup to complete (can take up to 2-3 minutes)")
        console.print("  2. Run 'codestory service recover' to try restarting unhealthy containers")
        console.print("  3. Run 'codestory service restart --skip-healthchecks' to restart without health checks")
        console.print("  4. Check container logs with 'docker logs codestory-service'")
        sys.exit(1)
    elif not service_api_healthy:
        sys.exit(1)


def find_docker_compose_file() -> Optional[str]:
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

def get_docker_compose_command() -> List[str]:
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
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
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
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        if process.returncode == 0:
            return ["docker-compose"]
    except Exception:
        pass
    
    # Default to 'docker compose' and hope it works
    return ["docker", "compose"]


@service.command(name="recover", help="Recover from unhealthy container state.")
@click.option("--force", "-f", is_flag=True, help="Force recovery by removing all containers.")
@click.option("--restart-worker", "--restart-workers", is_flag=True, help="Only restart the worker container.")
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
    unhealthy_containers = []
    try:
        process = subprocess.run(
            ["docker", "ps", "--filter", "health=unhealthy", "--format", "{{.Names}}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if process.returncode == 0:
            unhealthy_containers = [c for c in process.stdout.strip().split('\n') if c]
    except Exception as e:
        console.print(f"[yellow]Could not identify unhealthy containers: {str(e)}[/]")
    
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
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", worker_container],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if process.returncode == 0:
                health_status = process.stdout.strip()
                if health_status == "healthy":
                    console.print(f"[green]Worker container is now healthy![/]")
                else:
                    console.print(f"[yellow]Worker container status: {health_status}[/]")
                    console.print("Showing worker logs for debugging:")
                    subprocess.run(["docker", "logs", worker_container], check=False)
            else:
                console.print("[yellow]Could not check worker health status[/]")
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error restarting worker container: {str(e)}[/]")
            console.print("[yellow]Trying a full service recovery instead...[/]")
            force = True  # Fall back to force recovery
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {str(e)}[/]")
            force = True  # Fall back to force recovery
    
    # If unhealthy containers were found or force is specified
    if unhealthy_containers or force:
        if force:
            console.print("[bold]Force recovery requested. Stopping all containers and removing orphans...[/]")
            
            # Stop all containers, remove orphans and volumes
            try:
                # First try with docker compose
                cmd = [*compose_cmd, "-f", compose_file, "down", "--remove-orphans"]
                console.print(f"Running: [cyan]{' '.join(cmd)}[/]")
                subprocess.run(cmd, check=True)
                
                # Make sure all containers are truly stopped
                containers = get_running_containers()
                if containers:
                    console.print("[yellow]Some containers are still running. Stopping them manually...[/]")
                    for container in containers:
                        try:
                            console.print(f"Stopping container: {container}")
                            subprocess.run(["docker", "stop", container], check=True)
                        except Exception as e:
                            console.print(f"[red]Could not stop container {container}: {str(e)}[/]")
            except Exception as e:
                console.print(f"[red]Error stopping containers: {str(e)}[/]")
            
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
                console.print("[green]Service started with health checks disabled via environment variable.[/]")
                console.print("[yellow]Note: Service may take longer to fully initialize.[/]")
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]Error starting service: {str(e)}[/]")
                
                # Fall back to normal startup if environment variable approach fails
                console.print("Falling back to normal startup...")
                cmd = [*compose_cmd, "-f", compose_file, "up", "-d"]
                try:
                    subprocess.run(cmd, check=True)
                    console.print("[green]Service started normally.[/]")
                except subprocess.CalledProcessError as e:
                    console.print(f"[bold red]Error starting service: {str(e)}[/]")
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
                    console.print(f"[red]Error restarting {container}: {str(e)}[/]")
            
            # Wait a bit for containers to initialize
            console.print("Waiting for containers to initialize...")
            time.sleep(5)
            
            # Check if containers are now healthy
            all_healthy = True
            for container in unhealthy_containers:
                process = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", container],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
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
                console.print("[yellow]Some containers are still not healthy. Consider using --force to perform a full recovery.[/]")
    else:
        console.print("[green]No unhealthy containers found.[/]")
        
        # Check if service is running properly
        try:
            health = client.check_service_health()
            console.print("[green]Service is running correctly.[/]")
        except ServiceError:
            console.print("[yellow]Service is not responding despite no unhealthy containers.[/]")
            console.print("Checking all service containers...")
            
            # List all service containers
            try:
                cmd = [*compose_cmd, "-f", compose_file, "ps"]
                subprocess.run(cmd, check=True)
                
                # Suggest a restart if needed
                console.print("\n[yellow]Consider restarting the service with: 'codestory service restart'[/]")
            except Exception as e:
                console.print(f"[red]Error checking service containers: {str(e)}[/]")
                console.print("[yellow]Try a force recovery with: 'codestory service recover --force'[/]")
    
    console.print("[bold]Recovery process completed.[/]")

def get_running_containers() -> List[str]:
    """Get a list of running containers that might be part of the service.
    
    Returns:
        List of container names.
    """
    try:
        # Run docker ps to get running containers
        process = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"], 
            check=False, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode == 0:
            # Filter for containers that might be part of the service
            containers = process.stdout.strip().split('\n')
            return [c for c in containers if c and (
                "codestory" in c.lower() or 
                "neo4j" in c.lower() or 
                "redis" in c.lower() or 
                "service" in c.lower() or
                "worker" in c.lower()
            )]
    except Exception:
        pass
    
    return []


def show_unhealthy_container_logs(compose_cmd: List[str], compose_file: str, console: Console) -> None:
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            console.print("[yellow]Could not get container status information[/]")
            return
        
        # Parse the output to find containers
        container_lines = process.stdout.strip().split('\n')
        unhealthy_containers = []
        
        # Try to parse each line as JSON
        import json
        for line in container_lines:
            try:
                container_info = json.loads(line)
                if "Name" in container_info:
                    # Check for health status in the 'Status' field if available
                    if "Status" in container_info and "unhealthy" in container_info["Status"].lower():
                        unhealthy_containers.append(container_info["Name"])
            except json.JSONDecodeError:
                # Older Docker versions might not support JSON format
                # Fallback to checking for 'unhealthy' in the line
                if "unhealthy" in line.lower():
                    # Extract container name from line
                    parts = line.split()
                    if parts:
                        unhealthy_containers.append(parts[0])  # First column is usually name
        
        # If no unhealthy containers found by parsing, try a direct approach with docker ps
        if not unhealthy_containers:
            process = subprocess.run(
                ["docker", "ps", "--filter", "health=unhealthy", "--format", "{{.Names}}"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if process.returncode == 0:
                unhealthy_containers = [c for c in process.stdout.strip().split('\n') if c]
        
        # Specifically check worker container if no unhealthy containers found
        if not unhealthy_containers:
            worker_containers = ["codestory-worker", "worker"]
            for worker in worker_containers:
                process = subprocess.run(
                    ["docker", "logs", worker],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if process.returncode == 0:
                    unhealthy_containers.append(worker)
        
        # Show logs for unhealthy containers
        if unhealthy_containers:
            console.print(f"\n[bold]Found potentially unhealthy containers:[/] {', '.join(unhealthy_containers)}")
            for container in unhealthy_containers:
                console.print(f"\n[bold cyan]Logs for {container}:[/]")
                logs_cmd = ["docker", "logs", container]
                try:
                    logs = subprocess.run(
                        logs_cmd,
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        capture_output=True
                    )
                    if logs.stdout:
                        # Limit output to last 20 lines to avoid overwhelming the console
                        last_lines = logs.stdout.strip().split('\n')[-20:]
                        for line in last_lines:
                            console.print(f"  {line}")
                    if logs.stderr and logs.stderr.strip():
                        console.print("[bold red]Error output:[/]")
                        # Limit error output too
                        last_error_lines = logs.stderr.strip().split('\n')[-10:]
                        for line in last_error_lines:
                            console.print(f"  {line}")
                except Exception as e:
                    console.print(f"[red]Could not get logs for {container}: {str(e)}[/]")
        else:
            console.print("[yellow]No specific unhealthy containers identified. Check all container logs for more details.[/]")
            
    except Exception as e:
        console.print(f"[yellow]Error checking unhealthy containers: {str(e)}[/]")
