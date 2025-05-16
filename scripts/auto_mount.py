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
    """Check if repository is already mounted."""
    mounts = get_current_mounts()
    return f"{repo_path}" in mounts

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
        print(f"Repository {repo_path} is already mounted")
        return True
    
    # Repository needs to be mounted and containers restarted
    print(f"Mounting repository {repo_path} and restarting containers...")
    
    # Stop containers
    run_command("docker-compose down", capture_output=False)
    
    # Set environment variable
    os.environ["REPOSITORY_PATH"] = repo_path
    
    # Create repository config
    create_repo_config(repo_path)
    
    # Start containers
    run_command("docker-compose up -d", capture_output=False)
    
    # Wait for service to be ready
    return wait_for_service()

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
    
    args = parser.parse_args()
    
    # Mount repository
    print(f"Setting up repository mount for {args.repository_path}...")
    if not setup_repository_mount(args.repository_path):
        print("Failed to set up repository mount")
        sys.exit(1)
    
    # Run ingestion if not disabled
    if not args.no_ingest:
        print(f"Running ingestion for {args.repository_path}...")
        ingest_repository(args.repository_path, args.no_progress)
    
    print("Done!")

if __name__ == "__main__":
    main()