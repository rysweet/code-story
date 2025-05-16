#!/usr/bin/env python3
"""
Azure Authentication Helper for Code Story (DEPRECATED)

DEPRECATED: This script has been replaced by the more comprehensive azure_auth_renew.py.
Please use the newer script instead, which supports token injection into containers.

This script checks and renews Azure authentication credentials.
It detects authentication failures in logs and provides a convenient way 
to renew Azure credentials when needed.
"""

import argparse
import logging
import os
import re
import subprocess
import sys
from typing import Optional, Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("azure-auth-helper")

# Regular expressions for detecting auth failures in logs
AUTH_FAILURE_PATTERNS = [
    r"DefaultAzureCredential failed to retrieve a token from the included credentials",
    r"ERROR: AADSTS700003: Device object was not found in the tenant",
    r"ManagedIdentityCredential authentication unavailable",
    r"az login --scope https://cognitiveservices\.azure\.com/\.default"
]

# Tenant ID extraction pattern
TENANT_ID_PATTERN = r"tenant '([0-9a-f-]+)'"

def extract_tenant_id_from_error(error_message: str) -> Optional[str]:
    """Extract tenant ID from an error message.
    
    Args:
        error_message: Error message containing tenant ID
        
    Returns:
        Extracted tenant ID or None if not found
    """
    match = re.search(TENANT_ID_PATTERN, error_message)
    if match:
        return match.group(1)
    return None

def check_az_login_status() -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if user is logged in to Azure CLI.
    
    Returns:
        Tuple of (is_logged_in, current_tenant_id, current_subscription_id)
    """
    try:
        # Check current login status
        result = subprocess.run(
            ["az", "account", "show", "--query", "[tenantId, id]", "-o", "tsv"],
            check=False,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return False, None, None
        
        # Extract tenant ID and subscription ID
        output_lines = result.stdout.strip().split('\n')
        if len(output_lines) >= 2:
            tenant_id = output_lines[0].strip()
            subscription_id = output_lines[1].strip()
            return True, tenant_id, subscription_id
        
        return True, None, None
    
    except Exception as e:
        logger.error(f"Error checking Azure CLI login status: {e}")
        return False, None, None

def get_tenant_id_from_settings() -> Optional[str]:
    """Get Azure tenant ID from settings.
    
    Returns:
        Tenant ID from settings or None if not found
    """
    try:
        # Try to import from the codebase
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from codestory.config.settings import get_settings
        
        settings = get_settings()
        
        # Check multiple places where tenant ID might be stored
        tenant_id = None
        
        # Check openai settings
        if hasattr(settings, "openai") and hasattr(settings.openai, "tenant_id"):
            tenant_id = settings.openai.tenant_id
            
        # Check azure settings if not found
        if not tenant_id and hasattr(settings, "azure") and hasattr(settings.azure, "tenant_id"):
            tenant_id = settings.azure.tenant_id
            
        return tenant_id
    
    except ImportError:
        logger.warning("Could not import settings. Continuing without tenant ID from settings.")
        return None
    except Exception as e:
        logger.error(f"Error getting tenant ID from settings: {e}")
        return None

def check_logs_for_auth_failures(log_file: str = None) -> Tuple[bool, Optional[str]]:
    """Check logs for Azure authentication failures.
    
    Args:
        log_file: Optional path to log file. If None, reads from docker logs.
        
    Returns:
        Tuple of (auth_failure_detected, tenant_id)
    """
    try:
        # Read logs either from file or from docker
        log_content = ""
        
        if log_file and os.path.exists(log_file):
            with open(log_file, 'r') as f:
                log_content = f.read()
        else:
            # Try to get logs from codestory-service container
            try:
                log_result = subprocess.run(
                    ["docker", "logs", "codestory-service", "--tail", "200"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if log_result.returncode == 0:
                    log_content = log_result.stdout
            except Exception as e:
                logger.error(f"Error reading Docker logs: {e}")
        
        # Check for auth failure patterns
        for pattern in AUTH_FAILURE_PATTERNS:
            if re.search(pattern, log_content):
                # Auth failure detected, try to extract tenant ID
                tenant_id = extract_tenant_id_from_error(log_content)
                return True, tenant_id
        
        return False, None
    
    except Exception as e:
        logger.error(f"Error checking logs for auth failures: {e}")
        return False, None

def login_to_azure(tenant_id: Optional[str] = None) -> bool:
    """Log in to Azure with the specified tenant ID.
    
    Args:
        tenant_id: Optional tenant ID to use for login
        
    Returns:
        True if login successful, False otherwise
    """
    try:
        # Build command based on whether tenant ID is provided
        cmd = ["az", "login"]
        if tenant_id:
            cmd.extend(["--tenant", tenant_id])
            
        # Add --scope for cognitive services
        cmd.extend(["--scope", "https://cognitiveservices.azure.com/.default"])
        
        # Execute login command
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            check=False,
        )
        
        return result.returncode == 0
    
    except Exception as e:
        logger.error(f"Error logging in to Azure: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Azure Authentication Helper for Code Story")
    parser.add_argument("--check", action="store_true", help="Check for authentication failures")
    parser.add_argument("--login", action="store_true", help="Force login to Azure")
    parser.add_argument("--tenant", help="Specify Azure tenant ID")
    parser.add_argument("--log-file", help="Path to log file to check")
    
    args = parser.parse_args()
    
    # Get tenant ID in order of precedence: command line > logs > settings > current login
    tenant_id = args.tenant
    
    # Check logs for auth failures if requested or if no tenant ID provided
    if args.check or (args.login and not tenant_id):
        auth_failure, log_tenant_id = check_logs_for_auth_failures(args.log_file)
        
        if auth_failure:
            print("Authentication failure detected in logs")
            if log_tenant_id and not tenant_id:
                tenant_id = log_tenant_id
                print(f"Found tenant ID in logs: {tenant_id}")
    
    # If still no tenant ID, try to get from settings
    if not tenant_id:
        settings_tenant_id = get_tenant_id_from_settings()
        if settings_tenant_id:
            tenant_id = settings_tenant_id
            print(f"Using tenant ID from settings: {tenant_id}")
    
    # Check current login status
    is_logged_in, current_tenant_id, current_subscription_id = check_az_login_status()
    
    if is_logged_in:
        print(f"Currently logged in to Azure")
        print(f"Tenant ID: {current_tenant_id}")
        print(f"Subscription ID: {current_subscription_id}")
        
        # If tenant ID specified and different from current, prompt for login
        if tenant_id and tenant_id != current_tenant_id:
            print(f"Current tenant ({current_tenant_id}) doesn't match requested tenant ({tenant_id})")
            if args.login or input("Log in to the requested tenant? (y/n): ").lower() == 'y':
                login_to_azure(tenant_id)
    else:
        print("Not currently logged in to Azure")
        
        # Login if requested or if auth failure detected
        if args.login:
            login_to_azure(tenant_id)
        else:
            print(f"Run `{sys.argv[0]} --login" + (f" --tenant {tenant_id}" if tenant_id else "") + "` to log in")

if __name__ == "__main__":
    main()