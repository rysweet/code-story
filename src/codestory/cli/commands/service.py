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
@click.option("--detach", is_flag=True, help="Run the service in the background.")
@click.option("--wait", is_flag=True, help="Wait for the service to start.")
@click.pass_context
def start_service(ctx: click.Context, detach: bool = False, wait: bool = False) -> None:
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
            
        # Build the command
        cmd = [*compose_cmd, "-f", compose_file, "up"]

        if detach:
            cmd.append("-d")

        # Run the command
        console.print(f"Running command: [cyan]{' '.join(cmd)}[/]")

        if detach:
            subprocess.run(cmd, check=True)
        else:
            # If not detached, run in a separate process and wait
            process = subprocess.Popen(cmd)

            if wait:
                console.print("Waiting for service to start...")

                # Poll the health endpoint until it responds
                max_attempts = 30
                for i in range(max_attempts):
                    try:
                        client.check_service_health()
                        console.print("[green]Service is now running.[/]")
                        break
                    except ServiceError:
                        if i < max_attempts - 1:  # Don't sleep on the last iteration
                            time.sleep(1)

                return

            # If not waiting, return immediately
            console.print("[green]Service starting in background.[/]")
            return

        console.print("[green]Service started successfully.[/]")

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error starting service:[/] {str(e)}")
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
@click.option("--detach", is_flag=True, help="Run the service in the background after restart.")
@click.option("--wait", is_flag=True, help="Wait for the service to restart completely.")
@click.pass_context
def restart_service(ctx: click.Context, detach: bool = False, wait: bool = False) -> None:
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
            start_service(ctx, detach, wait)
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
        cmd = [*compose_cmd, "-f", compose_file, "up"]

        if detach:
            cmd.append("-d")

        # Run the command
        console.print(f"Starting service: [cyan]{' '.join(cmd)}[/]")

        if detach:
            subprocess.run(cmd, check=True)
        else:
            # If not detached, run in a separate process
            process = subprocess.Popen(cmd)

        if wait:
            console.print("Waiting for service to start...")

            # Poll the health endpoint until it responds
            max_attempts = 30
            for i in range(max_attempts):
                try:
                    client.check_service_health()
                    console.print("[green]Service restarted successfully.[/]")
                    break
                except ServiceError:
                    if i < max_attempts - 1:  # Don't sleep on the last iteration
                        time.sleep(1)
        else:
            console.print("[green]Service restart initiated.[/]")

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error restarting service:[/] {str(e)}")
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

    try:
        health = client.check_service_health()

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
        console.print(f"[bold red]Service is not running:[/] {str(e)}")
        
        # Check if any containers are running
        containers = get_running_containers()
        if containers:
            console.print("\nDetected running containers that might be part of the service:")
            for container in containers:
                console.print(f"[cyan]{container}[/]")
            console.print("\nYou may want to try stopping them manually or use 'docker compose down'")
            
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