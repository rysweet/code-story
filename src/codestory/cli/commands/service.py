"""
Service commands for the Code Story CLI.
"""

import subprocess
import sys
import time
from typing import Dict, Any, Optional

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
def service():
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
        # Run docker-compose up
        cmd = ["docker-compose", "up"]
        
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
        # Run docker-compose down
        cmd = ["docker-compose", "down"]
        
        # Run the command
        console.print(f"Running command: [cyan]{' '.join(cmd)}[/]")
        subprocess.run(cmd, check=True)
        
        console.print("[green]Service stopped successfully.[/]")
    
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error stopping service:[/] {str(e)}")
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
        
        # Add components to table
        for component, details in health.items():
            status = details.get("status", "unknown")
            status_style = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
            }.get(status.lower(), "white")
            
            message = details.get("message", "")
            
            table.add_row(
                component,
                f"[{status_style}]{status.capitalize()}[/]",
                message
            )
        
        console.print(table)
        
    except ServiceError as e:
        console.print(f"[bold red]Service is not running:[/] {str(e)}")
        sys.exit(1)