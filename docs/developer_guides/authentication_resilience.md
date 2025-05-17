# Authentication Resilience Guide

This guide explains how to handle authentication issues and configure Code Story for resilient operation when Azure authentication is unavailable or experiencing issues.

## Overview

Code Story's LLM functionality relies on Azure authentication to communicate with OpenAI services. In some cases, you might encounter authentication failures due to:

- Expired Azure tokens
- Network issues
- Missing Azure credentials
- Issues with Azure CLI installation

This guide introduces resilient operation modes that allow services to start and operate even when authentication is not optimal.

## Resilient Authentication Features

Code Story provides several resilience mechanisms:

1. **Automatic Fallback**: The service can automatically switch to API key authentication when Azure AD fails
2. **Resilient Health Checks**: Health endpoint continues working even with authentication issues
3. **Degraded Mode**: Services can run with reduced functionality when OpenAI is unavailable
4. **Override Configuration**: Simple Docker Compose override for authentication-resilient operation

## Using docker-compose.override.yml

The simplest way to enable authentication resilience is to use the provided Docker Compose override:

1. Create a `docker-compose.override.yml` file in your project root:

```yaml
# Docker Compose override file for authentication-resilient mode
services:
  service:
    environment:
      # Allow service to start without strict OpenAI model checks
      - CODESTORY_NO_MODEL_CHECK=true
      
      # Use fallback API key authentication instead of Azure AD
      # Replace with your actual API key for production use
      - OPENAI__API_KEY=your-actual-api-key
      
      # Use LLM resilient mode that handles fallbacks automatically
      - CODESTORY_LLM_MODE=fallback
      - CODESTORY_LLM_ALLOW_FALLBACK=true
      
  worker:
    environment:
      # Same settings for worker to ensure consistent behavior
      - CODESTORY_NO_MODEL_CHECK=true
      - OPENAI__API_KEY=your-actual-api-key
      - CODESTORY_LLM_MODE=fallback
      - CODESTORY_LLM_ALLOW_FALLBACK=true
```

2. Start the service with this override configuration:

```bash
docker-compose up -d
```

The services will now use fallback authentication and can operate even when Azure AD is unavailable.

## Environment Variables

You can configure authentication resilience using these environment variables:

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `CODESTORY_NO_MODEL_CHECK` | Bypass strict model validation | `true`, `1`, `yes` |
| `OPENAI__API_KEY` | Fallback API key for direct auth | `sk-your-api-key` |
| `CODESTORY_LLM_MODE` | LLM operation mode | `normal`, `fallback`, `disabled` |
| `CODESTORY_LLM_ALLOW_FALLBACK` | Allow automatic fallback to API key | `true`, `false` |
| `CODESTORY_LLM_PROVIDER` | LLM provider to use | `openai`, `azure_openai` |

## Automatic Token Renewal

In addition to fallback authentication, Code Story provides automatic token renewal:

1. Use the CLI to check service health and monitor authentication status:

```bash
codestory service status
```

2. If you detect Azure authentication issues, use the auth-renew command:

```bash
codestory service auth-renew
```

3. For specific Azure tenants, specify the tenant ID:

```bash
codestory service auth-renew --tenant your-tenant-id
```

## Understanding Health Status

The service health endpoint provides detailed information about component status:

- **healthy**: Everything is working properly
- **degraded**: Some components are not optimal but service is operational
- **unhealthy**: Critical components are not working

When running in resilient mode, the service may report "degraded" status but will continue to function.

## Troubleshooting

If you encounter authentication issues:

1. Check the service logs:
```bash
docker logs codestory-service
```

2. Look for authentication errors:
```bash
docker logs codestory-service | grep "Azure authentication"
```

3. Try renewing authentication:
```bash
codestory service auth-renew
```

4. If persistent issues occur, use the override file as described above

## Security Considerations

When using API key authentication instead of Azure AD:

- Store API keys securely
- Use environment variables for API keys, not hardcoded values
- Consider using a more secure approach in production environments
- Remember that fallback mode may have reduced security compared to Azure AD

## When to Use Authentication Resilience

Authentication resilience is recommended in these scenarios:

- Development environments where Azure AD is not configured
- CI/CD pipelines where Azure auth is difficult
- Demo environments that need to work without Azure credentials
- Recovery scenarios where normal authentication is temporarily unavailable

For production deployments, we recommend using the standard Azure AD authentication when possible.

## Related Topics

- [Service Recovery Guide](./service_recovery.md)
- [Deployment Troubleshooting](./deployment_troubleshooting.md)
- [Configuration Options](../user_guides/configuration.md)