#!/usr/bin/env python
"""Script to verify that required environment variables are set.

This script checks that all required environment variables are present in
the .env file and provides guidance for setting up the environment correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from codestory.config.settings import get_settings, refresh_settings


required_env_vars = {
    "OPENAI__ENDPOINT": "Azure OpenAI API endpoint (e.g., https://your-resource.openai.azure.com)",
    "OPENAI__TENANT_ID": "Azure AD tenant ID for authentication",
    "OPENAI__SUBSCRIPTION_ID": "Azure subscription ID",
    "OPENAI__EMBEDDING_MODEL": "OpenAI embedding model to use (default: text-embedding-3-small)",
    "OPENAI__CHAT_MODEL": "OpenAI chat model to use (default: gpt-4o)",
    "OPENAI__REASONING_MODEL": "OpenAI model for reasoning tasks (default: gpt-4o)"
}


def check_env_file_exists():
    """Check if .env file exists in project root."""
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("\n❌ ERROR: .env file is missing!")
        print(f"Please create a .env file at {env_path}")
        print("You can use .env-template as a starting point:")
        print(f"cp {env_path.parent / '.env-template'} {env_path}\n")
        return False
        
    return True


def check_env_vars():
    """Check for required environment variables in settings."""
    try:
        # Refresh settings to load from .env
        refresh_settings()
        settings = get_settings()
        
        # Check OpenAI settings
        if not hasattr(settings, "openai"):
            print("\n❌ ERROR: OpenAI settings are missing!")
            print("Please check your .env file and make sure OpenAI settings are properly configured.\n")
            return False
            
        missing = []
        openai_settings = settings.openai
        
        # Check required OpenAI settings
        for env_var, description in required_env_vars.items():
            var_name = env_var.split("__")[1].lower()
            if not hasattr(openai_settings, var_name) or getattr(openai_settings, var_name) is None:
                missing.append((env_var, description))
        
        if missing:
            print("\n❌ ERROR: Some required environment variables are missing!")
            print("Please add the following to your .env file:\n")
            
            for var, desc in missing:
                print(f"{var}=YOUR_VALUE_HERE  # {desc}")
                
            print("\nRefer to .env-template for examples.")
            return False
            
        return True
            
    except Exception as e:
        print(f"\n❌ ERROR: Failed to load settings: {str(e)}")
        return False


def check_azure_login():
    """Check if logged in to correct Azure tenant."""
    try:
        settings = get_settings()
        tenant_id = settings.openai.tenant_id
        
        if not tenant_id:
            print("\n⚠️ WARNING: No tenant_id configured, skipping Azure login check")
            return True
            
        import subprocess
        
        # Check current tenant
        result = subprocess.run(
            ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print("\n⚠️ WARNING: Not logged in to Azure CLI")
            print(f"Run the following command to login:")
            print(f"az login --tenant {tenant_id}\n")
            return False
            
        current_tenant = result.stdout.strip()
        
        if current_tenant != tenant_id:
            print(f"\n⚠️ WARNING: Logged in to wrong tenant: {current_tenant}")
            print(f"Expected tenant: {tenant_id}")
            print(f"Run the following command to login to the correct tenant:")
            print(f"az login --tenant {tenant_id}\n")
            return False
            
        # Check subscription
        subscription_id = settings.openai.subscription_id
        if subscription_id:
            result = subprocess.run(
                ["az", "account", "show", "--query", "id", "-o", "tsv"],
                capture_output=True,
                text=True,
                check=False
            )
            
            current_subscription = result.stdout.strip()
            
            if current_subscription != subscription_id:
                print(f"\n⚠️ WARNING: Using wrong subscription: {current_subscription}")
                print(f"Expected subscription: {subscription_id}")
                print(f"Run the following command to set the correct subscription:")
                print(f"az account set --subscription {subscription_id}\n")
                return False
                
        return True
        
    except ImportError:
        print("\n⚠️ WARNING: Azure CLI not installed, skipping Azure login check")
        return True
    except Exception as e:
        print(f"\n⚠️ WARNING: Failed to check Azure login: {str(e)}")
        return True


def main():
    """Run all environment checks."""
    print("🔍 Checking environment configuration...")
    
    env_file_ok = check_env_file_exists()
    if not env_file_ok:
        return False
        
    env_vars_ok = check_env_vars()
    if not env_vars_ok:
        return False
        
    azure_login_ok = check_azure_login()
    
    if env_file_ok and env_vars_ok and azure_login_ok:
        print("\n✅ Environment is properly configured!")
        return True
        
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)