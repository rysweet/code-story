#!/usr/bin/env python3
"""
Azure Authentication Renewal Script

This script detects Azure authentication issues and automatically renews authentication tokens.
It can also inject the tokens into Docker containers running the Code Story service.

Usage:
    python azure_auth_renew.py --check     # Check for auth issues without fixing
    python azure_auth_renew.py --renew     # Force renewal of auth tokens
    python azure_auth_renew.py --tenant TENANT_ID  # Specify tenant ID for login
    python azure_auth_renew.py --container service  # Inject tokens into specific container
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("azure_auth_renew")

# Azure token file paths
HOME_DIR = os.path.expanduser("~")
AZURE_DIR = os.path.join(HOME_DIR, ".azure")
MSAL_TOKEN_CACHE = os.path.join(AZURE_DIR, "msal_token_cache.json")
AZURE_PROFILE = os.path.join(AZURE_DIR, "azureProfile.json")
ACCESS_TOKENS = os.path.join(AZURE_DIR, "accessTokens.json")

# Docker container names
SERVICE_CONTAINER = "code-story-service"
WORKER_CONTAINER = "code-story-worker"
MCP_CONTAINER = "code-story-mcp"


def check_logs_for_auth_failures() -> tuple[bool, str | None]:
    """
    Check Docker logs for Azure authentication failures.

    Returns:
        Tuple[bool, Optional[str]]: (auth_failure_detected, tenant_id)
    """
    try:
        # Check service container logs
        cmd = ["docker", "logs", SERVICE_CONTAINER, "--tail", "100"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logs = result.stdout

        # Look for auth failure pattern
        if "DefaultAzureCredential failed to retrieve a token" in logs:
            logger.info("Found authentication failure in service logs")
            # Try to extract tenant ID if available
            tenant_match = re.search(r"tenant '([0-9a-f-]+)'", logs)
            tenant_id = tenant_match.group(1) if tenant_match else None
            return True, tenant_id

        # Check worker container logs
        try:
            cmd = ["docker", "logs", WORKER_CONTAINER, "--tail", "100"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logs = result.stdout

            if "DefaultAzureCredential failed to retrieve a token" in logs:
                logger.info("Found authentication failure in worker logs")
                # Try to extract tenant ID if available
                tenant_match = re.search(r"tenant '([0-9a-f-]+)'", logs)
                tenant_id = tenant_match.group(1) if tenant_match else None
                return True, tenant_id
        except subprocess.CalledProcessError:
            logger.warning("Failed to check worker container logs")

        logger.info("No authentication failures found in logs")
        return False, None
    except Exception as e:
        logger.error(f"Error checking logs: {e}")
        return False, None


def check_health_api_for_auth_issues() -> tuple[bool, str | None]:
    """
    Check service health API for authentication issues.

    Returns:
        Tuple[bool, Optional[str]]: (auth_failure_detected, tenant_id)
    """
    try:
        # Get the service URL from docker env vars or default to localhost
        cmd = [
            "docker",
            "exec",
            SERVICE_CONTAINER,
            "bash",
            "-c",
            "curl -s http://localhost:8000/health",
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        try:
            health_data = json.loads(result.stdout)

            # Check OpenAI component health
            if (
                "components" in health_data
                and "openai" in health_data["components"]
                and health_data["components"]["openai"]["status"] == "unhealthy"
            ):
                error_msg = health_data["components"]["openai"].get("message", "")
                if "DefaultAzureCredential failed to retrieve a token" in error_msg:
                    logger.info("Found authentication failure in health API")
                    # Try to extract tenant ID if available
                    tenant_match = re.search(r"tenant '([0-9a-f-]+)'", error_msg)
                    tenant_id = tenant_match.group(1) if tenant_match else None
                    return True, tenant_id

            logger.info("No authentication failures found in health API")
            return False, None
        except json.JSONDecodeError:
            logger.warning("Failed to parse health API response as JSON")
            return False, None
    except Exception as e:
        logger.error(f"Error checking health API: {e}")
        return False, None


def extract_tenant_id_from_config() -> str | None:
    """
    Extract tenant ID from config files.

    Returns:
        Optional[str]: Tenant ID if found, None otherwise
    """
    try:
        # First try to get from Azure profile
        if os.path.exists(AZURE_PROFILE):
            with open(AZURE_PROFILE) as f:
                profile_data = json.load(f)
                if "subscriptions" in profile_data:
                    for sub in profile_data["subscriptions"]:
                        if "tenantId" in sub:
                            return sub["tenantId"]

        # Try to check docker env vars
        cmd = [
            "docker",
            "exec",
            SERVICE_CONTAINER,
            "bash",
            "-c",
            "grep -r AZURE_TENANT_ID /app/.env* 2>/dev/null || echo ''",
        ]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stdout:
                # Extract tenant ID from env var
                tenant_match = re.search(r"AZURE_TENANT_ID=([0-9a-f-]+)", result.stdout)
                if tenant_match:
                    return tenant_match.group(1)
        except subprocess.CalledProcessError:
            pass

        return None
    except Exception as e:
        logger.error(f"Error extracting tenant ID from config: {e}")
        return None


def get_running_containers() -> list[str]:
    """
    Get list of running Code Story containers.

    Returns:
        List[str]: List of container names
    """
    try:
        cmd = ["docker", "ps", "--format", "{{.Names}}"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        containers = result.stdout.strip().split("\n")

        # Filter for Code Story containers
        code_story_containers = []
        for container in containers:
            if container and any(
                name in container
                for name in [
                    "code-story-service",
                    "code-story-worker",
                    "code-story-mcp",
                    "codestory-service",
                    "codestory-worker",
                    "codestory-mcp",
                ]
            ):
                code_story_containers.append(container)

        return code_story_containers
    except Exception as e:
        logger.error(f"Error getting running containers: {e}")
        return []


def login_to_azure(tenant_id: str | None = None) -> bool:
    """
    Run az login with the specified tenant ID.

    Args:
        tenant_id: Azure tenant ID

    Returns:
        bool: True if login was successful
    """
    try:
        cmd = ["az", "login", "--scope", "https://cognitiveservices.azure.com/.default"]
        if tenant_id:
            cmd.extend(["--tenant", tenant_id])

        logger.info(f"Running Azure login command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Verify login success
        try:
            login_data = json.loads(result.stdout)
            if isinstance(login_data, list) and len(login_data) > 0:
                logger.info("Azure login successful")
                return True
        except json.JSONDecodeError:
            pass

        logger.warning("Azure login command did not return expected output")
        return False
    except Exception as e:
        logger.error(f"Error running Azure login: {e}")
        return False


def inject_azure_tokens_into_container(container_name: str) -> bool:
    """
    Copy Azure token files into a container.

    Args:
        container_name: Name of the container

    Returns:
        bool: True if tokens were successfully injected
    """
    try:
        # Create a tar file containing the Azure token files
        with tempfile.NamedTemporaryFile(suffix=".tar") as temp_tar:
            # Create a temporary directory to organize files
            with tempfile.TemporaryDirectory() as temp_dir:
                azure_dir = os.path.join(temp_dir, ".azure")
                os.makedirs(azure_dir, exist_ok=True)

                # Copy token files to temp directory
                for file_path in [MSAL_TOKEN_CACHE, AZURE_PROFILE, ACCESS_TOKENS]:
                    if os.path.exists(file_path):
                        shutil.copy2(
                            file_path,
                            os.path.join(azure_dir, os.path.basename(file_path)),
                        )

                # Create tar file
                tar_cmd = ["tar", "-cf", temp_tar.name, "-C", temp_dir, ".azure"]
                subprocess.run(tar_cmd, check=True)

                # Copy tar file to container and extract
                subprocess.run(
                    [
                        "docker",
                        "cp",
                        temp_tar.name,
                        f"{container_name}:/tmp/azure_tokens.tar",
                    ],
                    check=True,
                )

                # Extract in container
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        container_name,
                        "bash",
                        "-c",
                        "cd / && tar -xf /tmp/azure_tokens.tar && chmod -R 700 /.azure && rm /tmp/azure_tokens.tar",
                    ],
                    check=True,
                )

                logger.info(
                    f"Successfully injected Azure tokens into container {container_name}"
                )
                return True

    except Exception as e:
        logger.error(f"Error injecting tokens into container {container_name}: {e}")
        return False


def detect_auth_issues() -> tuple[bool, str | None]:
    """
    Detect Azure authentication issues.

    Returns:
        Tuple[bool, Optional[str]]: (auth_failure_detected, tenant_id)
    """
    # Check logs for auth failures
    auth_failure, tenant_id = check_logs_for_auth_failures()
    if auth_failure:
        return True, tenant_id

    # Check health API
    auth_failure, tenant_id = check_health_api_for_auth_issues()
    if auth_failure:
        return True, tenant_id

    return False, None


def renew_authentication(
    tenant_id: str | None = None, container_filter: str | None = None
) -> bool:
    """
    Renew Azure authentication tokens and inject into containers.

    Args:
        tenant_id: Azure tenant ID
        container_filter: Only inject tokens into containers with this name

    Returns:
        bool: True if renewal was successful
    """
    # If no tenant ID provided, try to find one
    if not tenant_id:
        # First try to get from auth error messages
        auth_failure, detected_tenant_id = detect_auth_issues()
        if detected_tenant_id:
            tenant_id = detected_tenant_id
        else:
            # Try to extract from config
            config_tenant_id = extract_tenant_id_from_config()
            if config_tenant_id:
                tenant_id = config_tenant_id

    # Run az login
    login_success = login_to_azure(tenant_id)
    if not login_success:
        return False

    # Get running containers
    containers = get_running_containers()
    if not containers:
        logger.warning("No running Code Story containers found")
        return True  # Login was successful even if no containers to update

    # Inject tokens into containers
    success = True
    for container in containers:
        if container_filter and container_filter not in container:
            continue

        logger.info(f"Injecting tokens into container: {container}")
        if not inject_azure_tokens_into_container(container):
            success = False

    return success


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Azure Authentication Renewal Tool")
    parser.add_argument(
        "--check", action="store_true", help="Check for auth issues without fixing"
    )
    parser.add_argument(
        "--renew", action="store_true", help="Force renewal of auth tokens"
    )
    parser.add_argument("--tenant", help="Specify Azure tenant ID for login")
    parser.add_argument("--container", help="Inject tokens into specific container")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Check mode
        if args.check:
            auth_failure, tenant_id = detect_auth_issues()
            if auth_failure:
                logger.info(
                    f"Azure authentication issues detected. Tenant ID: {tenant_id or 'Unknown'}"
                )
                return 1
            else:
                logger.info("No Azure authentication issues detected")
                return 0

        # Renew mode
        if args.renew or args.tenant or args.container:
            success = renew_authentication(args.tenant, args.container)
            if success:
                logger.info("Azure authentication renewal successful")
                return 0
            else:
                logger.error("Azure authentication renewal failed")
                return 1

        # Default mode - check and renew if needed
        auth_failure, tenant_id = detect_auth_issues()
        if auth_failure:
            logger.info(
                f"Azure authentication issues detected. Tenant ID: {tenant_id or 'Unknown'}"
            )
            success = renew_authentication(tenant_id)
            if success:
                logger.info("Azure authentication renewal successful")
                return 0
            else:
                logger.error("Azure authentication renewal failed")
                return 1
        else:
            logger.info("No Azure authentication issues detected")
            return 0

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
