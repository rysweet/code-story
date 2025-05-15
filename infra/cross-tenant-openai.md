# Cross-Tenant Azure OpenAI Access

This document outlines the configuration required to access Azure OpenAI resources located in a different tenant than the one where the Code Story application is deployed.

## Scenario

In enterprise environments, you may need to:
1. Deploy the Code Story application in Tenant A (e.g., your primary organizational tenant)
2. Access Azure OpenAI resources located in Tenant B (e.g., a specialized AI resources tenant)

## Authentication Options

### Option 1: Service Principal with Cross-Tenant Access

1. **Create a Service Principal in the Azure OpenAI Tenant (Tenant B)**:
   ```bash
   # Login to the OpenAI tenant
   az login --tenant <openai-tenant-id>
   
   # Create service principal
   az ad sp create-for-rbac --name "CodeStory-OpenAI-Access" --skip-assignment
   
   # Note the appId, password, and tenant values
   ```

2. **Grant the Service Principal Access to OpenAI**:
   ```bash
   # Assign Cognitive Services User role to the service principal
   az role assignment create \
     --assignee <service-principal-app-id> \
     --role "Cognitive Services User" \
     --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<openai-account-name>
   ```

3. **Configure Multi-Tenant Access**:
   - Navigate to Azure Portal → Azure Active Directory → App Registrations
   - Find and select your registered application
   - Go to Authentication → Supported account types
   - Select "Accounts in any organizational directory (Any Azure AD directory - Multitenant)"
   - Save changes

4. **Store Credentials in Application Tenant's Key Vault (Tenant A)**:
   ```bash
   # Switch to application tenant
   az login --tenant <application-tenant-id>
   
   # Add secrets to Key Vault
   az keyvault secret set --vault-name <key-vault-name> --name "OpenAIClientId" --value "<service-principal-app-id>"
   az keyvault secret set --vault-name <key-vault-name> --name "OpenAIClientSecret" --value "<service-principal-password>"
   az keyvault secret set --vault-name <key-vault-name> --name "OpenAITenantId" --value "<openai-tenant-id>"
   ```

5. **Update Application Configuration**:
   ```yaml
   AZURE_OPENAI_AUTH_MODE: "service_principal"
   AZURE_OPENAI_TENANT_ID: "<openai-tenant-id>"
   AZURE_OPENAI_CLIENT_ID: "<service-principal-app-id>"
   AZURE_OPENAI_CLIENT_SECRET: "<service-principal-password>"
   AZURE_OPENAI_ENDPOINT: "https://<openai-resource-name>.openai.azure.com/"
   ```

### Option 2: User-Assigned Managed Identity with Workload Identity Federation (Recommended)

This approach is more secure as it doesn't require storing secrets.

1. **Create a User-Assigned Managed Identity in Application Tenant (Tenant A)**:
   ```bash
   # Login to application tenant
   az login --tenant <application-tenant-id>
   
   # Create managed identity
   az identity create --name "CodeStory-OpenAI-Identity" --resource-group <resource-group> --location <location>
   
   # Note the clientId, principalId, and resourceId
   ```

2. **Set Up Workload Identity Federation**:
   ```bash
   # Login to OpenAI tenant
   az login --tenant <openai-tenant-id>
   
   # Register the managed identity as a service principal in the OpenAI tenant
   az ad sp create --id <managed-identity-client-id>
   
   # Assign Cognitive Services User role
   az role assignment create \
     --assignee <managed-identity-client-id> \
     --role "Cognitive Services User" \
     --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<openai-account-name>
   ```

3. **Update Container App Configuration**:
   ```bicep
   resource containerApp 'Microsoft.App/containerApps@2022-03-01' = {
     // ... existing properties
     identity: {
       type: 'UserAssigned'
       userAssignedIdentities: {
         '<managed-identity-resource-id>': {}
       }
     }
     // ... other properties
   }
   ```

4. **Update Application Configuration**:
   ```yaml
   AZURE_OPENAI_AUTH_MODE: "managed_identity"
   AZURE_OPENAI_TENANT_ID: "<openai-tenant-id>"
   AZURE_OPENAI_CLIENT_ID: "<managed-identity-client-id>"
   AZURE_OPENAI_ENDPOINT: "https://<openai-resource-name>.openai.azure.com/"
   ```

## Code Changes Required

### OpenAI Client Implementation

```python
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.core.credentials import TokenCredential
from openai import AzureOpenAI

class CrossTenantOpenAIClient:
    def __init__(self, config):
        self.endpoint = config.AZURE_OPENAI_ENDPOINT
        self.api_version = config.AZURE_OPENAI_API_VERSION
        self.auth_mode = config.AZURE_OPENAI_AUTH_MODE
        self.tenant_id = config.AZURE_OPENAI_TENANT_ID
        
        # Get credential based on auth mode
        if self.auth_mode == "service_principal":
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=config.AZURE_OPENAI_CLIENT_ID,
                client_secret=config.AZURE_OPENAI_CLIENT_SECRET
            )
        elif self.auth_mode == "managed_identity":
            self.credential = DefaultAzureCredential(
                managed_identity_client_id=config.AZURE_OPENAI_CLIENT_ID,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}"
            )
        else:
            raise ValueError(f"Unsupported auth mode: {self.auth_mode}")
            
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            azure_ad_token_provider=self._get_token
        )
    
    def _get_token(self):
        token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token
        
    def complete(self, prompt, **kwargs):
        # Use the client to call OpenAI API
        response = self.client.completions.create(
            prompt=prompt,
            **kwargs
        )
        return response
```

## Infrastructure Changes

To incorporate these options into the Azure Bicep templates, add the following to the Key Vault module:

```bicep
// In key-vault.bicep
param openaiTenantId string = ''
param openaiClientId string = ''
@secure()
param openaiClientSecret string = ''

// Add these secrets if using service principal authentication
resource openaiTenantIdSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(openaiTenantId)) {
  parent: keyVault
  name: 'openai-tenant-id'
  properties: {
    value: openaiTenantId
  }
}

resource openaiClientIdSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(openaiClientId)) {
  parent: keyVault
  name: 'openai-client-id'
  properties: {
    value: openaiClientId
  }
}

resource openaiClientSecretSecret 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = if (!empty(openaiClientSecret)) {
  parent: keyVault
  name: 'openai-client-secret'
  properties: {
    value: openaiClientSecret
  }
}
```

## Troubleshooting

### Common Issues:

1. **Invalid Authentication**:
   - Ensure the service principal or managed identity has the correct permissions
   - Verify tenant IDs are correct in the configuration

2. **Access Denied**:
   - Check RBAC assignments on the Azure OpenAI resource
   - Ensure the application has been granted multi-tenant permissions if using service principal

3. **Token Acquisition Failures**:
   - Check network connectivity between tenants
   - Verify the credential configuration (client ID, tenant ID, etc.)

### Logging and Diagnostics:

Enable verbose logging in your application to troubleshoot authentication issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

1. **Principle of Least Privilege**: Grant only necessary permissions to the service principal or managed identity
2. **Secret Rotation**: Set up regular rotation for service principal credentials
3. **Auditing**: Enable diagnostic logging for all cross-tenant operations
4. **Network Security**: Consider implementing Private Endpoints for the OpenAI resources

## References

- [Microsoft Entra ID Cross-Tenant Access](https://learn.microsoft.com/en-us/azure/active-directory/external-identities/cross-tenant-access-overview)
- [Azure OpenAI Service Authentication](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/managed-identity)
- [Workload Identity Federation](https://learn.microsoft.com/en-us/azure/active-directory/workload-identities/workload-identity-federation)