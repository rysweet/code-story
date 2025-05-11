@description('Name of the Key Vault')
param name string

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to the Key Vault')
param tags object = {}

@description('ID of the Managed Identity that will have access to the vault')
param managedIdentityId string

@description('Object ID of the AAD user who should get Secrets Officer access to the vault')
@secure()
param secretsOfficerObjectId string = ''

@description('Secrets to be stored in Key Vault')
param secrets array = []

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    tenantId: tenant().tenantId
    accessPolicies: concat(
      [
        {
          objectId: reference(managedIdentityId, '2023-01-31').principalId
          tenantId: tenant().tenantId
          permissions: {
            secrets: [
              'get'
              'list'
            ]
          }
        }
      ], 
      !empty(secretsOfficerObjectId) ? [
        {
          objectId: secretsOfficerObjectId
          tenantId: tenant().tenantId
          permissions: {
            secrets: [
              'get'
              'list'
              'set'
              'delete'
              'backup'
              'restore'
              'recover'
              'purge'
            ]
          }
        }
      ] : []
    )
    sku: {
      name: 'standard'
      family: 'A'
    }
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// Create secrets
@batchSize(1)
resource keyVaultSecrets 'Microsoft.KeyVault/vaults/secrets@2022-07-01' = [for secret in secrets: {
  parent: keyVault
  name: secret.name
  properties: {
    value: secret.value
  }
}]

output id string = keyVault.id
output name string = keyVault.name
output uri string = keyVault.properties.vaultUri