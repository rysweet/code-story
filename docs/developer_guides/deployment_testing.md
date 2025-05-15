# Deployment Testing Guide

This guide covers the automated testing procedures for validating Code Story deployments. It includes information on creating test environments, running validation tests, and interpreting test results.

## Overview

The deployment testing framework includes:

1. Scripts to create isolated test environments in Azure
2. Validation tests to verify all components are functioning correctly
3. Automated cleanup procedures to remove test resources

## Prerequisites

Before running deployment tests, ensure you have:

- Azure CLI installed and logged in
- Azure Developer CLI (azd) installed
- Docker installed and running
- Permissions to create resources in your Azure subscription

## Creating a Test Deployment

Use the `create_test_deployment.sh` script to create a complete test deployment:

```bash
./infra/scripts/create_test_deployment.sh --env-name my-test-env
```

This script:
1. Creates a new azd environment with a unique name
2. Provisions all necessary Azure resources
3. Deploys the application code
4. Optionally runs validation tests

### Script Options

```
--env-name NAME          Environment name for the test deployment (default: test-env-timestamp)
--location LOCATION      Azure region for deployment (default: eastus)
--subscription ID        Azure subscription ID to use (uses default if not specified)
--clean                  Clean up existing environment with the same name if it exists
--skip-tests             Skip running tests after deployment
```

## Running Validation Tests

If you already have a deployment and want to test it, use the `test_deployment.sh` script:

```bash
./infra/scripts/test_deployment.sh --service-url https://myservice.azurecontainerapps.io
```

### Script Options

```
--service-url URL        Base URL of the service API (required)
--mcp-url URL            Base URL of the MCP API
--gui-url URL            Base URL of the GUI
--neo4j-uri URI          Neo4j connection URI (with protocol)
--neo4j-username USER    Neo4j username (default: neo4j)
--neo4j-password PASS    Neo4j password
--test-repo URL          Git repo URL to use for testing ingestion
--skip-ingestion         Skip ingestion tests (faster)
--json                   Output results in JSON format
```

## Test Categories

The validation tests check:

1. **Service Endpoints** - Core API functionality
2. **MCP Endpoints** - Model Context Protocol functionality
3. **GUI Endpoints** - Web interface accessibility
4. **Neo4j Database** - Database connection and queries
5. **Configuration API** - System configuration access
6. **Ingestion Workflow** - End-to-end repository processing

## Interpreting Test Results

The test script outputs:

- A summary of passed, failed, and skipped tests
- Total execution time
- Detailed error information for failed tests
- Optionally, a JSON output format for CI/CD integration

## Continuous Integration Testing

For CI/CD pipelines, you can use the test scripts in headless mode:

```bash
./infra/scripts/create_test_deployment.sh \
  --env-name ci-test-$BUILD_ID \
  --skip-tests && \
./infra/scripts/test_deployment.sh \
  --service-url https://$SERVICE_FQDN \
  --json > test_results.json
```

## Cleaning Up Test Deployments

To remove a test deployment:

```bash
# Using azd directly
azd env select my-test-env && azd down

# Or manually delete the resource group
az group delete --name rg-my-test-env -y
```

## Common Testing Scenarios

### Basic Sanity Check

Quick test to verify service is responding:

```bash
./infra/scripts/test_deployment.sh \
  --service-url https://myservice.azurecontainerapps.io \
  --skip-ingestion
```

### Complete System Test

Comprehensive test including repository ingestion:

```bash
./infra/scripts/test_deployment.sh \
  --service-url https://myservice.azurecontainerapps.io \
  --mcp-url https://mymcp.azurecontainerapps.io \
  --gui-url https://mygui.azurecontainerapps.io \
  --neo4j-uri bolt://myneo4j.azurecontainerapps.io:7687 \
  --neo4j-username neo4j \
  --neo4j-password mypassword \
  --test-repo https://github.com/example/test-repo
```

## Troubleshooting

### Common Issues

1. **Timeouts during deployment** - Azure Container Apps can take 10-15 minutes to become fully available. Increase the timeout values in the test script if necessary.

2. **Authentication failures** - Ensure you're properly authenticated with Azure CLI (`az login`) and have the necessary permissions.

3. **Resource limits** - Azure subscriptions have limits on the number of resources. Clean up unused test environments.

4. **Neo4j connection issues** - Verify the Neo4j password and ensure the Neo4j port (7687) is accessible.

### Getting More Details

For more detailed logs during deployment:

```bash
azd env select my-test-env
azd provision --debug
azd deploy --debug
```

## Best Practices

1. Use a dedicated subscription or resource group for tests
2. Include deployment tests in your CI/CD pipeline
3. Always clean up test environments after use
4. Test with different repository sizes to validate scaling
5. Run tests in multiple regions for global deployments
6. Maintain a small test repository specifically designed for quick validation