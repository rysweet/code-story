#!/usr/bin/env python3
"""
Azure Token Injection Utility

This script injects Azure authentication tokens from the host system into running
Code Story containers. It's used as part of the authentication renewal process
to ensure all containers have valid Azure credentials.

Usage:
    python inject_azure_tokens.py
    python inject_azure_tokens.py --tenant-id <tenant_id>
    python inject_azure_tokens.py --restart-containers
"""

import argparse
import json
import logging
import os
import subprocess
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("azure-token-injector")

# Container names that need Azure credentials
TARGET_CONTAINERS = ["codestory-service", "codestory-worker"]

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Inject Azure tokens into Code Story containers")
    parser.add_argument("--tenant-id", help="Azure tenant ID to use for authentication")
    parser.add_argument("--restart-containers", action="store_true", 
                        help="Restart containers after token injection")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser.parse_args()

def get_azure_token_location() -> str:
    """Get the location of Azure tokens on the host machine."""
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, ".azure")

def check_docker_available() -> bool:
    """Check if Docker is available on the system."""
    try:
        result = subprocess.run(
            ["docker", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        logger.info(f"Docker is available: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Docker is not available: {e}")
        return False

def get_running_containers() -> List[str]:
    """Get list of running Code Story containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        
        all_containers = result.stdout.strip().split('\n')
        code_story_containers = [
            container for container in all_containers 
            if container.startswith("codestory-") and container
        ]
        
        logger.info(f"Found {len(code_story_containers)} Code Story containers: {code_story_containers}")
        return code_story_containers
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get container list: {e}")
        logger.error(f"stderr: {e.stderr}")
        return []

def extract_tenant_id_from_settings() -> Optional[str]:
    """Extract tenant ID from environment variables or settings files."""
    # Check environment variables first
    tenant_id = os.environ.get("AZURE_TENANT_ID") or os.environ.get("AZURE_OPENAI__TENANT_ID")
    if tenant_id:
        logger.info(f"Found tenant ID in environment variables: {tenant_id}")
        return tenant_id
    
    # Check .codestory.toml file
    try:
        import toml
        config_path = Path(".codestory.toml")
        if config_path.exists():
            config = toml.load(config_path)
            if "azure_openai" in config and "tenant_id" in config["azure_openai"]:
                tenant_id = config["azure_openai"]["tenant_id"]
                logger.info(f"Found tenant ID in .codestory.toml: {tenant_id}")
                return tenant_id
    except ImportError:
        logger.warning("toml package not available, skipping config file check")
    except Exception as e:
        logger.warning(f"Error reading .codestory.toml: {e}")
    
    # Check ~/.azure/config
    azure_config_path = Path(get_azure_token_location()) / "config"
    if azure_config_path.exists():
        try:
            with open(azure_config_path, "r") as f:
                for line in f:
                    if line.strip().startswith("tenant ="):
                        tenant_id = line.split("=")[1].strip()
                        logger.info(f"Found tenant ID in Azure config: {tenant_id}")
                        return tenant_id
        except Exception as e:
            logger.warning(f"Error reading Azure config: {e}")
    
    logger.warning("Could not find tenant ID in environment or config files")
    return None

def extract_tenant_id_from_error(error_message: str) -> Optional[str]:
    """Extract tenant ID from an Azure authentication error message."""
    import re
    
    # Try different patterns from error messages
    patterns = [
        r"tenant '([0-9a-f-]+)'",
        r"tenant ID: ([0-9a-f-]+)",
        r"AADSTS500011.+?'([0-9a-f-]+)'",
        r"AADSTS700003.+?'([0-9a-f-]+)'",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            tenant_id = match.group(1)
            logger.info(f"Extracted tenant ID from error message: {tenant_id}")
            return tenant_id
    
    logger.warning(f"Could not extract tenant ID from error message")
    return None

def check_token_validity() -> Tuple[bool, Optional[str]]:
    """Check if Azure tokens are valid and return error message if not."""
    try:
        result = subprocess.run(
            ["az", "account", "get-access-token", "--output", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning(f"Azure CLI token check failed: {result.stderr}")
            return False, result.stderr
        
        # Try to parse the token info
        token_info = json.loads(result.stdout)
        expires_on = token_info.get("expiresOn", "")
        
        logger.info(f"Token is valid, expires on: {expires_on}")
        return True, None
    except Exception as e:
        logger.error(f"Error checking Azure token validity: {e}")
        return False, str(e)

def inject_tokens_into_container(container_name: str) -> bool:
    """Copy Azure tokens from host into the specified container."""
    try:
        # First check if the container exists and is running
        container_check = subprocess.run(
            ["docker", "container", "inspect", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if container_check.returncode != 0:
            logger.warning(f"Container {container_name} does not exist or is not running")
            return False

        # Get the location of Azure tokens on the host
        token_location = get_azure_token_location()
        
        # Check if the Azure token directory exists and has files
        if not os.path.exists(token_location):
            logger.error(f"Azure token directory {token_location} does not exist")
            print(f"\nAzure token directory not found at {token_location}.")
            print("Please run 'az login' first to create valid Azure credentials.\n")
            return False
        
        # Count the number of files in the token location
        token_files = os.listdir(token_location)
        if not token_files:
            logger.warning(f"Azure token directory {token_location} exists but is empty")
            print(f"\nAzure token directory at {token_location} is empty.")
            print("Please run 'az login' to create valid Azure credentials.\n")
            return False

        # Verify that azureProfile.json exists - critical for authentication
        azure_profile_path = os.path.join(token_location, "azureProfile.json")
        if not os.path.exists(azure_profile_path):
            logger.warning(f"Azure profile file {azure_profile_path} does not exist")
            print(f"\nAzure profile file not found at {azure_profile_path}.")
            print("Please run 'az login' to create a valid Azure profile.\n")
            return False

        # Copy the entire .azure directory into the container
        # We're using both /root/.azure and /home/appuser/.azure to cover all bases
        logger.info(f"Copying Azure tokens from {token_location} to {container_name}")
        
        # Make sure the target directory exists in the container
        mkdir_cmd = [
            "docker", "exec", container_name,
            "bash", "-c", "mkdir -p /root/.azure"
        ]
        
        mkdir_result = subprocess.run(
            mkdir_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if mkdir_result.returncode != 0:
            logger.warning(f"Failed to create /root/.azure directory in {container_name}: {mkdir_result.stderr}")
            # Continue anyway as the cp might succeed if the directory already exists
        
        # First to root user directory
        copy_cmd = [
            "docker", "cp", 
            token_location + "/.", 
            f"{container_name}:/root/.azure/"
        ]
        
        result = subprocess.run(
            copy_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to copy tokens to {container_name}:/root/.azure: {result.stderr}")
            return False
        
        # Verify that the files were copied
        verify_cmd = [
            "docker", "exec", container_name,
            "bash", "-c", "ls -la /root/.azure/"
        ]
        
        verify_result = subprocess.run(
            verify_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if verify_result.returncode != 0 or not verify_result.stdout.strip():
            logger.error(f"Token injection failed: No files found in container after copy")
            return False
        
        logger.info(f"Files in /root/.azure/: {verify_result.stdout}")
        
        # Then to appuser directory if it exists
        appuser_copy_cmd = [
            "docker", "exec", container_name,
            "bash", "-c", 
            "if [ -d '/home/appuser' ]; then mkdir -p /home/appuser/.azure && cp -r /root/.azure/* /home/appuser/.azure/ 2>/dev/null || true; chown -R appuser:appuser /home/appuser/.azure 2>/dev/null || true; fi"
        ]
        
        appuser_result = subprocess.run(
            appuser_copy_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if appuser_result.returncode != 0:
            logger.warning(f"Non-critical error copying to appuser directory: {appuser_result.stderr}")
            # This is non-critical, so continue
        
        logger.info(f"Successfully injected tokens into {container_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error injecting tokens into {container_name}: {e}")
        return False

def restart_container(container_name: str) -> bool:
    """Restart a specific container."""
    try:
        logger.info(f"Restarting container: {container_name}")
        
        # First check if the container exists and is running
        container_check = subprocess.run(
            ["docker", "container", "inspect", "--format", "{{.State.Status}}", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if container_check.returncode != 0:
            logger.warning(f"Container {container_name} does not exist")
            return False
        
        container_status = container_check.stdout.strip()
        logger.info(f"Container {container_name} status before restart: {container_status}")
        
        # If container is not running, try to start it
        if container_status != "running":
            logger.info(f"Container {container_name} is not running (status: {container_status}), trying to start it")
            start_result = subprocess.run(
                ["docker", "start", container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if start_result.returncode != 0:
                logger.error(f"Failed to start {container_name}: {start_result.stderr}")
                return False
            
            logger.info(f"Successfully started {container_name}")
            return True
        
        # Container is running, restart it
        result = subprocess.run(
            ["docker", "restart", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully restarted {container_name}")
            
            # Verify the container is running after restart
            verify_check = subprocess.run(
                ["docker", "container", "inspect", "--format", "{{.State.Status}}", container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if verify_check.returncode == 0 and verify_check.stdout.strip() == "running":
                logger.info(f"Container {container_name} is running after restart")
                return True
            else:
                logger.warning(f"Container {container_name} might not be running properly after restart. Status: {verify_check.stdout.strip() if verify_check.returncode == 0 else 'unknown'}")
                return False
        else:
            logger.error(f"Failed to restart {container_name}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error restarting container {container_name}: {e}")
        return False

def authenticate_with_azure(tenant_id: Optional[str] = None) -> bool:
    """Perform Azure authentication with the given tenant ID."""
    try:
        # First check if Azure CLI is available
        try:
            az_version = subprocess.run(
                ["az", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if az_version.returncode != 0:
                logger.error("Azure CLI is not available or not properly installed")
                print("\nAzure CLI is not available or not properly installed.")
                print("Please install Azure CLI with 'brew install azure-cli' or follow instructions at:")
                print("https://docs.microsoft.com/en-us/cli/azure/install-azure-cli\n")
                return False
                
            logger.info(f"Azure CLI is available: {az_version.stdout.splitlines()[0] if az_version.stdout else 'unknown version'}")
        except Exception as e:
            logger.error(f"Failed to check Azure CLI availability: {e}")
            print("\nAzure CLI is not available on this system.")
            print("Please install Azure CLI with 'brew install azure-cli' or follow instructions at:")
            print("https://docs.microsoft.com/en-us/cli/azure/install-azure-cli\n")
            return False
            
        # Build login command
        if tenant_id:
            login_cmd = ["az", "login", "--tenant", tenant_id]
            logger.info(f"Authenticating with Azure using tenant ID: {tenant_id}")
        else:
            login_cmd = ["az", "login"]
            logger.info("Authenticating with Azure (no tenant ID specified)")
        
        # Try to include scope if using a recent version of Azure CLI
        # Check version to decide if we should add scope
        try:
            version_info = az_version.stdout.splitlines()[0] if az_version.stdout else ""
            import re
            version_match = re.search(r"azure-cli\s+(\d+)\.(\d+)\.(\d+)", version_info)
            if version_match:
                major, minor, patch = map(int, version_match.groups())
                # For Azure CLI 2.30.0 or later, add scope
                if major > 2 or (major == 2 and minor >= 30):
                    login_cmd.extend(["--scope", "https://cognitiveservices.azure.com/.default"])
                    logger.info("Added scope parameter to login command based on Azure CLI version")
        except Exception as e:
            logger.warning(f"Error checking Azure CLI version for scope parameter: {e}")
            # Continue without scope parameter
            
        # Run the login command
        print(f"\nRunning Azure authentication: {' '.join(login_cmd)}")
        print("A browser window should open for you to log in...")
        
        result = subprocess.run(
            login_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Azure authentication successful")
            print("\nAzure authentication successful!")
            
            # Verify authentication by getting token
            verify_cmd = ["az", "account", "get-access-token"]
            
            if tenant_id:
                verify_cmd.extend(["--tenant", tenant_id])
                
            try:
                verify_result = subprocess.run(
                    verify_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if verify_result.returncode == 0:
                    import json
                    token_info = json.loads(verify_result.stdout)
                    
                    # Trim token for display (just first few chars)
                    access_token = token_info.get("accessToken", "")
                    token_preview = access_token[:10] + "..." if access_token else "none"
                    
                    logger.info(f"Verified access token: {token_preview}")
                    
                    # Extract expiration from token
                    expires_on = token_info.get("expiresOn", "unknown")
                    subscription = token_info.get("subscription", "unknown")
                    
                    logger.info(f"Token expires on: {expires_on}, Subscription: {subscription}")
                    print(f"Access token expires on: {expires_on}")
                    print(f"Subscription: {subscription}")
                else:
                    logger.warning(f"Could not verify token after login: {verify_result.stderr}")
            except Exception as e:
                logger.warning(f"Error verifying token after login: {e}")
                
            return True
        else:
            logger.error(f"Azure authentication failed: {result.stderr}")
            
            # Check for common error messages
            if "AADSTS70002" in result.stderr:
                print("\nError: The tenant name or ID is incorrect or not found.")
                print(f"Please verify that the tenant ID '{tenant_id}' is correct.")
            elif "AADSTS50034" in result.stderr:
                print("\nError: The user or application was not found in the directory.")
                print("Please check your Azure AD credentials.")
            elif "AADSTS50076" in result.stderr or "AADSTS50079" in result.stderr:
                print("\nError: Multi-factor authentication (MFA) is required.")
                print("Please complete the MFA process in the browser window.")
            elif "AADSTS65001" in result.stderr:
                print("\nError: Consent required for application access.")
                print("Please complete the consent process in the browser window.")
            else:
                print(f"\nAzure authentication failed: {result.stderr}")
                
            return False
    except Exception as e:
        logger.error(f"Error during Azure authentication: {e}")
        print(f"\nUnexpected error during Azure authentication: {e}")
        return False

def main():
    """Main function to inject Azure tokens into containers."""
    args = parse_arguments()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting Azure token injection")
    
    # Ensure Docker is available
    if not check_docker_available():
        logger.error("Docker is required but not available")
        sys.exit(1)
    
    # Get list of running containers
    containers = get_running_containers()
    codestory_containers = [c for c in containers if c in TARGET_CONTAINERS]
    
    if not codestory_containers:
        logger.warning("No Code Story containers found to inject tokens into")
        sys.exit(0)
    
    # Get tenant ID with priority:
    # 1. Command line argument
    # 2. Environment variables
    # 3. Config files
    # 4. Extract from error messages
    tenant_id = args.tenant_id
    
    # If no tenant ID from CLI, try environment variables or config
    if not tenant_id:
        tenant_id = extract_tenant_id_from_settings()
        
        if tenant_id:
            logger.info(f"Using tenant ID from environment/config: {tenant_id}")
    
    # Check if tokens are valid
    tokens_valid, error_message = check_token_validity()
    
    # If tokens are invalid and no tenant ID yet, try to extract it from error message
    if not tokens_valid and not tenant_id and error_message:
        extracted_tenant_id = extract_tenant_id_from_error(error_message)
        if extracted_tenant_id:
            tenant_id = extracted_tenant_id
            logger.info(f"Extracted tenant ID from error message: {tenant_id}")
    
    # We'll always display the login command, but won't run it automatically unless requested
    if not tokens_valid:
        # Build the login command to show
        if tenant_id:
            login_cmd = f"az login --tenant {tenant_id}"
        else:
            login_cmd = "az login"
            
        # Add scope if needed
        login_cmd += " --scope https://cognitiveservices.azure.com/.default"
        
        # Always print the login command
        print("\n" + "=" * 60)
        print("AZURE AUTHENTICATION REQUIRED")
        print("-" * 60)
        print(f"Please run the following command in a terminal:")
        print(f"  {login_cmd}")
        print("=" * 60 + "\n")
        
        # Let the user know we're using their tenant ID
        if tenant_id:
            print(f"Using tenant ID: {tenant_id}")
            print("This tenant ID was found in your environment configuration.\n")
        
        # Don't proceed without valid tokens
        logger.warning("Azure tokens are invalid or expired. Please authenticate manually.")
        sys.exit(1)
    
    # Inject tokens into each container
    successful_injections = 0
    for container in codestory_containers:
        if inject_tokens_into_container(container):
            successful_injections += 1
    
    logger.info(f"Successfully injected tokens into {successful_injections}/{len(codestory_containers)} containers")
    
    # Restart containers if requested
    if args.restart_containers:
        logger.info("Restarting containers after token injection")
        for container in codestory_containers:
            restart_container(container)
    
    # Wait for containers to be healthy if restarted
    if args.restart_containers and successful_injections > 0:
        logger.info("Waiting for containers to become healthy...")
        time.sleep(5)  # Initial wait
        
        for container in codestory_containers:
            try:
                health_check_cmd = [
                    "docker", "inspect", 
                    "--format", "{{.State.Health.Status}}", 
                    container
                ]
                
                max_attempts = 10
                for attempt in range(max_attempts):
                    result = subprocess.run(
                        health_check_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    status = result.stdout.strip()
                    logger.info(f"Container {container} health status: {status} (attempt {attempt+1}/{max_attempts})")
                    
                    if status == "healthy":
                        break
                    
                    time.sleep(5)  # Wait before next check
            except Exception as e:
                logger.warning(f"Error checking health for {container}: {e}")
    
    logger.info("Azure token injection complete")
    
    # Print success message
    print("\nAzure tokens have been successfully injected into Code Story containers.")
    print(f"Affected containers: {', '.join(codestory_containers)}")
    if args.restart_containers:
        print("Containers have been restarted to use the new tokens.")
    else:
        print("\nNote: For tokens to take effect, you may need to restart containers with:")
        print("  docker restart " + " ".join(codestory_containers))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())