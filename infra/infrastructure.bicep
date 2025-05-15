// This is the main infrastructure Bicep file that contains all the resources
// It's called by main.bicep and handles resource deployment within the resource group

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to all resources')
param tags object

// Container Apps Environment
@description('Container Apps Environment settings')
param containerAppsEnvName string
param logAnalyticsWorkspaceName string
param appInsightsName string

// Key Vault
@description('Key Vault settings')
param keyVaultName string
@secure()
param secretsOfficerObjectId string = ''

// Container Registry
@description('Container Registry settings')
param containerRegistryName string
param containerRegistrySku string = 'Basic'

// Redis
@description('Redis settings')
param redisName string
param redisSku string = 'Basic'
param redisCapacity int = 0

// Neo4j
@description('Neo4j settings')
param neo4jName string
param neo4jUsername string = 'neo4j'
@secure()
param neo4jPassword string

// Service
@description('Service settings')
param serviceName string
param serviceImage string
param servicePort int = 8000
param serviceReplicas int = 1
param serviceMemory string = '1.0Gi'
param serviceCpu string = '0.5'

// Worker
@description('Worker settings')
param workerName string
param workerImage string
param workerReplicas int = 2
param workerMemory string = '1.0Gi'
param workerCpu string = '0.5'

// MCP
@description('MCP settings')
param mcpName string
param mcpImage string
param mcpPort int = 8001
param mcpReplicas int = 1
param mcpMemory string = '1.0Gi'
param mcpCpu string = '0.5'
param mcpClientId string = ''
@secure()
param mcpClientSecret string = ''
param authEnabled bool = true

// GUI
@description('GUI settings')
param guiName string
param guiImage string
param guiPort int = 80
param guiReplicas int = 1
param guiMemory string = '0.5Gi'
param guiCpu string = '0.25'

// OpenAI API Keys
@secure()
param openaiApiKey string = ''

@secure()
param azureOpenaiApiKey string = ''

// Managed Identity
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'code-story-mi'
  location: location
  tags: tags
}

// Create Log Analytics workspace
module logAnalytics './azure/modules/log-analytics.bicep' = {
  name: 'logAnalyticsDeployment'
  params: {
    name: logAnalyticsWorkspaceName
    location: location
    tags: tags
  }
}

// Create Application Insights
module appInsights './azure/modules/app-insights.bicep' = {
  name: 'appInsightsDeployment'
  params: {
    name: appInsightsName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.id
  }
}

// Create Container Registry
module containerRegistry './azure/modules/container-registry.bicep' = {
  name: 'containerRegistryDeployment'
  params: {
    name: containerRegistryName
    location: location
    sku: containerRegistrySku
    tags: tags
    managedIdentityId: managedIdentity.id
  }
}

// Create Key Vault
module keyVault './azure/modules/key-vault.bicep' = {
  name: 'keyVaultDeployment'
  params: {
    name: keyVaultName
    location: location
    tags: tags
    managedIdentityId: managedIdentity.id
    secretsOfficerObjectId: secretsOfficerObjectId
    secrets: [
      {
        name: 'neo4j-password'
        value: neo4jPassword
      }
      {
        name: 'entra-client-secret'
        value: mcpClientSecret
      }
      {
        name: 'openai-api-key'
        value: openaiApiKey
      }
      {
        name: 'azure-openai-api-key'
        value: azureOpenaiApiKey
      }
    ]
  }
}

// Create Container Apps Environment
module containerAppsEnv './azure/modules/container-apps-environment.bicep' = {
  name: 'containerAppsEnvDeployment'
  params: {
    name: containerAppsEnvName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.id
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
  }
}

// Create Redis Cache
module redis './azure/modules/redis.bicep' = {
  name: 'redisDeployment'
  params: {
    name: redisName
    location: location
    tags: tags
    sku: redisSku
    capacity: redisCapacity
  }
}

// Create Neo4j container
module neo4j './azure/modules/neo4j.bicep' = {
  name: 'neo4jDeployment'
  params: {
    name: neo4jName
    location: location
    tags: tags
    containerAppsEnvId: containerAppsEnv.outputs.id
    username: neo4jUsername
    password: neo4jPassword
    keyVaultName: keyVault.outputs.name
  }
}

// Create Service container app
module service './azure/modules/service.bicep' = {
  name: 'serviceDeployment'
  params: {
    name: serviceName
    location: location
    tags: tags
    containerAppsEnvId: containerAppsEnv.outputs.id
    containerRegistryName: containerRegistry.outputs.name
    image: serviceImage
    port: servicePort
    minReplicas: 1
    maxReplicas: serviceReplicas
    memory: serviceMemory
    cpu: serviceCpu
    managedIdentityId: managedIdentity.id
    neo4jUri: 'bolt://${neo4j.outputs.fqdn}:7687'
    neo4jUsername: neo4jUsername
    keyVaultName: keyVault.outputs.name
    redisUri: 'redis://${redis.outputs.hostName}:${redis.outputs.port}'
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
  }
  dependsOn: [
    neo4j
    redis
    keyVault
  ]
}

// Create Worker container app
module worker './azure/modules/worker.bicep' = {
  name: 'workerDeployment'
  params: {
    name: workerName
    location: location
    tags: tags
    containerAppsEnvId: containerAppsEnv.outputs.id
    containerRegistryName: containerRegistry.outputs.name
    image: workerImage
    minReplicas: 1
    maxReplicas: workerReplicas
    memory: workerMemory
    cpu: workerCpu
    managedIdentityId: managedIdentity.id
    neo4jUri: 'bolt://${neo4j.outputs.fqdn}:7687'
    neo4jUsername: neo4jUsername
    keyVaultName: keyVault.outputs.name
    redisUri: 'redis://${redis.outputs.hostName}:${redis.outputs.port}'
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
  }
  dependsOn: [
    neo4j
    redis
    service
    keyVault
  ]
}

// Create MCP container app
module mcp './azure/modules/mcp.bicep' = {
  name: 'mcpDeployment'
  params: {
    name: mcpName
    location: location
    tags: tags
    containerAppsEnvId: containerAppsEnv.outputs.id
    containerRegistryName: containerRegistry.outputs.name
    image: mcpImage
    port: mcpPort
    minReplicas: 1
    maxReplicas: mcpReplicas
    memory: mcpMemory
    cpu: mcpCpu
    managedIdentityId: managedIdentity.id
    neo4jUri: 'bolt://${neo4j.outputs.fqdn}:7687'
    neo4jUsername: neo4jUsername
    serviceUri: 'https://${service.outputs.fqdn}'
    keyVaultName: keyVault.outputs.name
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
  }
  dependsOn: [
    service
    neo4j
    keyVault
  ]
}

// Create GUI container app
module gui './azure/modules/gui.bicep' = {
  name: 'guiDeployment'
  params: {
    name: guiName
    location: location
    tags: tags
    containerAppsEnvId: containerAppsEnv.outputs.id
    containerRegistryName: containerRegistry.outputs.name
    image: guiImage
    port: guiPort
    minReplicas: 1
    maxReplicas: guiReplicas
    memory: guiMemory
    cpu: guiCpu
    managedIdentityId: managedIdentity.id
    serviceUri: 'https://${service.outputs.fqdn}'
    mcpUri: 'https://${mcp.outputs.fqdn}'
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
    enableEntraAuth: authEnabled
    entraClientId: mcpClientId
  }
  dependsOn: [
    service
    mcp
  ]
}

// Outputs
output containerRegistryName string = containerRegistry.outputs.name
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output keyVaultName string = keyVault.outputs.name
output serviceFqdn string = service.outputs.fqdn
output mcpFqdn string = mcp.outputs.fqdn
output guiFqdn string = gui.outputs.fqdn
output neo4jFqdn string = neo4j.outputs.fqdn