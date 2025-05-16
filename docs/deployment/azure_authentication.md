# Azure Authentication Management

This document describes how to manage Azure authentication for Code Story, including how to handle token expiration and renewal.

## Overview

Code Story uses Azure OpenAI services for AI capabilities, which requires Azure authentication. The authentication is managed using the DefaultAzureCredential from the Azure Identity library, which provides a flexible approach to authentication with multiple fallback mechanisms.

When Azure authentication tokens expire (which typically happens every few hours to days, depending on your Azure configuration), Code Story provides automatic detection and renewal capabilities.

## Authentication Flow

1. Code Story uses `DefaultAzureCredential` from Azure Identity library to authenticate with Azure OpenAI
2. This credential provider attempts to authenticate using multiple methods in sequence:
   - Environment variables
   - Managed Identity
   - Visual Studio Code credentials
   - Azure CLI credentials
   - Interactive browser authentication
3. For typical development environments, Code Story relies on Azure CLI credentials
4. These credentials expire periodically and need to be renewed

## Automatic Detection and Renewal

Code Story automatically detects Azure authentication failures and can renew credentials:

1. **Detection**: The OpenAI adapter and health check API automatically detect Azure authentication failures
2. **Auto-renewal**: When specified, the system can automatically renew authentication by running `az login` with the appropriate tenant ID
3. **Container Integration**: The renewed credentials are automatically injected into all Code Story containers

## Renewal Methods

There are several ways to renew Azure authentication:

### CLI Command

The most convenient way to renew authentication is using the Code Story CLI:

```bash
# Basic renewal command
codestory service auth-renew

# With specific tenant ID
codestory service auth-renew --tenant <tenant-id>

# Just check auth status without renewing
codestory service auth-renew --check

# Show detailed output
codestory service auth-renew --verbose
```

### Health Check API

The service health check API supports automatic renewal:

```bash
# Manually trigger auth renewal via health check
curl "http://localhost:8000/health?auto_fix=true"
```

### Status Check

When running `codestory service status`, authentication issues are detected and repair instructions are displayed:

```bash
codestory service status

# With auto-renewal
codestory service status --renew-auth
```

### Direct Script

For advanced troubleshooting, you can directly run the renewal script:

```bash
# On host system
python scripts/azure_auth_renew.py

# With tenant ID
python scripts/azure_auth_renew.py --tenant <tenant-id>

# Check only
python scripts/azure_auth_renew.py --check
```

## Troubleshooting

### Common Issues

1. **Token Expiration**: Azure tokens typically expire after some time (hours to days)
   - Solution: Run `codestory service auth-renew`

2. **Wrong Tenant**: If you're logged into the wrong Azure tenant
   - Solution: Run `codestory service auth-renew --tenant <correct-tenant-id>`

3. **Container Token Synchronization**: Sometimes containers don't sync tokens properly
   - Solution: Run `codestory service restart` to restart all containers with fresh tokens

### Advanced Troubleshooting

For persistent authentication issues:

1. Check which tenant you're using:
   ```bash
   az account show --query tenantId -o tsv
   ```

2. List available tenants:
   ```bash
   az account tenant list -o table
   ```

3. Log in to a specific tenant:
   ```bash
   az login --tenant <tenant-id> --scope https://cognitiveservices.azure.com/.default
   ```

4. Verify containers have access to Azure credentials:
   ```bash
   docker exec codestory-service ls -la /.azure
   docker exec codestory-worker ls -la /.azure
   ```

5. Run a manual injection of tokens:
   ```bash
   python scripts/azure_auth_renew.py --verbose
   ```

## Configuration

Azure authentication settings are managed in Code Story's configuration:

```toml
[azure]
tenant_id = "your-tenant-id"
subscription_id = "your-subscription-id"

[openai]
endpoint = "https://your-resource.openai.azure.com"
api_version = "2025-03-01-preview"
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o"
```

These settings can be managed through environment variables or the configuration file.