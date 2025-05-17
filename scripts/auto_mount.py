#!/usr/bin/env python3
"""
Auto-mount script for Code Story repository ingestion.
This script automatically mounts repositories and restarts Docker containers when needed.
"""

import os
import sys
import subprocess
import time
import argparse
import shutil

def run_command(command, capture_output=True, shell=True):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            shell=shell,
            check=True
        )
        return result.stdout if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error output: {e.stderr}")
        return None

def is_docker_running():
    """Check if Docker is running and containers exist."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=codestory-service", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        return "codestory-service" in result.stdout
    except Exception:
        return False

def get_current_mounts():
    """Get current repository mounts from Docker containers."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "codestory-service", "--format", "{{json .Mounts}}"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout
    except Exception:
        return ""

def is_repo_mounted(repo_path):
    """Check if repository is already mounted correctly for ingestion.
    
    This checks both the actual mount and whether the path is accessible
    inside the container at the expected location.
    """
    # First, check if path appears in mounts
    mounts = get_current_mounts()
    mount_found = f"{repo_path}" in mounts
    
    # Even if mount is found, check if the path actually exists in the container
    # This is needed because we might have a parent directory mounted but not the specific repo
    repo_name = os.path.basename(repo_path)
    container_path = f"/repositories/{repo_name}"
    
    try:
        # Check if path exists in container
        result = subprocess.run(
            ["docker", "exec", "codestory-service", "test", "-d", container_path, "&&", "echo", "exists"],
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        path_exists = "exists" in result.stdout
        
        if not path_exists:
            # Try to inspect what's actually in /repositories
            inspect_result = subprocess.run(
                ["docker", "exec", "codestory-service", "ls", "-la", "/repositories"],
                capture_output=True,
                text=True,
                check=False
            )
            print(f"Container /repositories directory contents:\n{inspect_result.stdout}")
        
        return path_exists
    except Exception as e:
        print(f"Error checking if repository is mounted in container: {e}")
        return False

def setup_repository_mount(repo_path):
    """Set up repository mount and restart containers if necessary."""
    repo_path = os.path.abspath(repo_path)
    
    # Check if path exists
    if not os.path.isdir(repo_path):
        print(f"Error: Directory {repo_path} does not exist")
        return False
    
    # Check if Docker is running
    if not is_docker_running():
        print("Starting Docker containers with repository mount...")
        # Start containers with repository mount
        os.environ["REPOSITORY_PATH"] = repo_path
        run_command("docker-compose up -d", capture_output=False)
        
        # Wait for service to be ready
        wait_for_service()
        return True
    
    # Check if repository is already mounted
    if is_repo_mounted(repo_path):
        print(f"Repository {repo_path} is already mounted correctly")
        return True
    
    # Repository needs to be mounted and containers restarted
    print(f"Mounting repository {repo_path} and restarting containers...")
    
    # Stop containers
    run_command("docker-compose down", capture_output=False)
    
    # Get repo name for specific mounting
    repo_name = os.path.basename(repo_path)
    
    # Create a custom .env file for Docker Compose with specific repository mounting
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    with open(env_file_path, "w") as f:
        # This defines a specific mount for just this repository
        f.write(f"REPOSITORY_SOURCE={repo_path}\n")
        f.write(f"REPOSITORY_DEST=/repositories/{repo_name}\n")
    
    print(f"Created .env file with specific mount:\n  {repo_path} -> /repositories/{repo_name}")
    
    # Also set environment variable as backup
    os.environ["REPOSITORY_SOURCE"] = repo_path
    os.environ["REPOSITORY_DEST"] = f"/repositories/{repo_name}"
    
    # Create repository config
    create_repo_config(repo_path)
    
    # Update docker-compose.yml temporarily
    try:
        # Create a docker-compose.override.yml file for custom mounts
        override_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.override.yml")
        with open(override_file_path, "w") as f:
            f.write(f"""services:
  service:
    volumes:
      - {repo_path}:/repositories/{repo_name}
  worker:
    volumes:
      - {repo_path}:/repositories/{repo_name}
""")
        print(f"Created docker-compose.override.yml with specific mount configuration")
    except Exception as e:
        print(f"Error creating override file: {e}")
    
    # Start containers
    run_command("docker-compose up -d", capture_output=False)
    
    # Wait for service to be ready
    wait_success = wait_for_service()
    
    # Verify repository is actually mounted correctly after restart
    if wait_success:
        verification = is_repo_mounted(repo_path)
        if verification:
            print(f"Successfully verified repository is mounted correctly at /repositories/{repo_name}")
        else:
            print(f"Warning: Repository may not be mounted correctly. Continuing anyway.")
        
        # Get container mount info for debugging
        inspect_result = subprocess.run(
            ["docker", "inspect", "codestory-service", "--format", "{{json .Mounts}}"],
            capture_output=True,
            text=True,
            check=False
        )
        print(f"Container mounts:\n{inspect_result.stdout}")
        
        return True
    
    return False

def wait_for_service():
    """Wait for the service to be ready."""
    print("Waiting for service to be ready...")
    attempts = 0
    max_attempts = 30
    
    while attempts < max_attempts:
        try:
            health_status = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", "codestory-service"],
                capture_output=True,
                text=True,
                check=False
            ).stdout.strip()
            
            print(f"Service status: {health_status} (attempt {attempts+1}/{max_attempts})")
            
            if health_status == "healthy":
                print("Service is ready!")
                return True
                
            time.sleep(5)
            attempts += 1
        except Exception as e:
            print(f"Error checking service status: {e}")
            time.sleep(5)
            attempts += 1
    
    print("Service did not become ready in time")
    return False

def create_repo_config(repo_path):
    """Create repository configuration file."""
    config_dir = os.path.join(repo_path, ".codestory")
    os.makedirs(config_dir, exist_ok=True)
    
    config_file = os.path.join(config_dir, "repository.toml")
    repo_name = os.path.basename(repo_path)
    
    with open(config_file, "w") as f:
        f.write(f"""# CodeStory repository configuration
# Created by auto_mount.py

[repository]
name = "{repo_name}"
local_path = "{repo_path}"
container_path = "/repositories/{repo_name}"
mounted = true
mount_time = "{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}"
auto_mounted = true
""")
    
    print(f"Created repository config at {config_file}")
    return True

def ingest_repository(repo_path, no_progress=False):
    """Run ingestion for the repository."""
    repo_path = os.path.abspath(repo_path)
    
    # Get codestory CLI path
    codestory_cmd = shutil.which("codestory")
    if not codestory_cmd:
        print("Error: codestory command not found. Make sure it's installed.")
        return False
    
    # Run ingestion command
    cmd = [codestory_cmd, "ingest", "start", repo_path, "--container"]
    if no_progress:
        cmd.append("--no-progress")
    
    print(f"Running ingestion with command: {' '.join(cmd)}")
    subprocess.run(cmd, check=False)
    return True

def main():
    parser = argparse.ArgumentParser(description="Mount and ingest a repository with Code Story")
    parser.add_argument("repository_path", help="Path to the repository to ingest")
    parser.add_argument("--no-progress", action="store_true", help="Don't show progress updates")
    parser.add_argument("--no-ingest", action="store_true", help="Only mount repository, don't run ingestion")
    parser.add_argument("--force-remount", action="store_true", help="Force remount even if repository seems to be mounted")
    parser.add_argument("--debug", action="store_true", help="Show additional debug information")
    
    args = parser.parse_args()
    
    # Get absolute repository path
    repo_path = os.path.abspath(args.repository_path)
    repo_name = os.path.basename(repo_path)
    
    # Debug info if requested
    if args.debug:
        print("Debug information:")
        print(f"  Repository path: {repo_path}")
        print(f"  Repository name: {repo_name}")
        
        # Check if containers are running
        docker_ps = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False
        )
        print(f"  Docker containers: {docker_ps.stdout}")
        
        # Check if directory exists
        print(f"  Repository exists: {os.path.isdir(repo_path)}")
        
        # Check current mounts
        mounts = get_current_mounts()
        print(f"  Current mounts: {mounts}")
        
        # Check contents of /repositories in container
        try:
            repo_ls = subprocess.run(
                ["docker", "exec", "codestory-service", "ls", "-la", "/repositories"],
                capture_output=True,
                text=True,
                check=False
            )
            print(f"  Container /repositories contents: {repo_ls.stdout}")
        except Exception as e:
            print(f"  Error checking /repositories: {e}")
    
    # Mount repository
    print(f"Setting up repository mount for {repo_path}...")
    
    # Force remount if requested
    if args.force_remount:
        print("Forcing remount of repository...")
        # Stop containers
        run_command("docker-compose down", capture_output=False)
        # Reset mount flag for setup_repository_mount
        if not setup_repository_mount(repo_path):
            print("Failed to set up repository mount")
            sys.exit(1)
    else:
        # Regular mount logic
        if not setup_repository_mount(repo_path):
            print("Failed to set up repository mount")
            sys.exit(1)
    
    # Run ingestion if not disabled
    if not args.no_ingest:
        print(f"Running ingestion for {repo_path}...")
        ingest_repository(repo_path, args.no_progress)
    
    print("Done!")

if __name__ == "__main__":
    main()