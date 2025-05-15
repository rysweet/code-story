targetScope = 'subscription'

// The main bicep module to deploy Code Story using azd
@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g., dev, test, prod)')
param environmentName string = 'dev'

@minLength(1)
@description('Azure region to deploy resources')
param location string = deployment().location

@description('Resource Group to deploy into')
param resourceGroupName string = ''

// Optional parameters to override the default azd values
@description('Azure Container Registry name')
param containerRegistryName string = ''

@description('Container Apps Environment name')
param containerAppsEnvName string = ''

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string = ''

@description('Application Insights name')
param appInsightsName string = ''

@description('Key Vault name')
param keyVaultName string = ''

// Neo4j settings
@description('Neo4j container app name')
param neo4jName string = ''

@description('Neo4j username')
param neo4jUsername string = 'neo4j'

@secure()
@description('Neo4j password')
param neo4jPassword string

// Redis settings
@description('Redis cache name')
param redisName string = ''

@description('Redis SKU')
param redisSku string = 'Basic'

@description('Redis capacity')
param redisCapacity int = 0

// Service settings (main API service)
@description('Service container app name')
param serviceName string = ''

@description('Service image name')
param serviceImage string = ''

@description('Service container port')
param servicePort int = 8000

@description('Service memory')
param serviceMemory string = '1.0Gi'

@description('Service CPU')
param serviceCpu string = '0.5'

@description('Service replicas')
param serviceReplicas int = 1

// Worker settings (Celery worker)
@description('Worker container app name')
param workerName string = ''

@description('Worker image name')
param workerImage string = ''

@description('Worker memory')
param workerMemory string = '1.0Gi'

@description('Worker CPU')
param workerCpu string = '0.5'

@description('Worker replicas')
param workerReplicas int = 2

// MCP settings
@description('MCP container app name')
param mcpName string = ''

@description('MCP image name')
param mcpImage string = ''

@description('MCP container port')
param mcpPort int = 8001

@description('MCP memory')
param mcpMemory string = '1.0Gi'

@description('MCP CPU')
param mcpCpu string = '0.5'

@description('MCP replicas')
param mcpReplicas int = 1

@description('Enable authentication')
param authEnabled bool = false

@description('Entra Client ID')
param mcpClientId string = ''

@secure()
@description('Entra Client Secret')
param mcpClientSecret string = ''

// GUI settings
@description('GUI container app name')
param guiName string = ''

@description('GUI image name')
param guiImage string = ''

@description('GUI container port')
param guiPort int = 80

@description('GUI memory')
param guiMemory string = '0.5Gi'

@description('GUI CPU')
param guiCpu string = '0.25'

@description('GUI replicas')
param guiReplicas int = 1

// OpenAI API Keys
@secure()
@description('OpenAI API Key')
param openaiApiKey string = ''

@secure()
@description('Azure OpenAI API Key')
param azureOpenaiApiKey string = ''

@secure()
@description('Object ID of the AAD user who should get Secrets Officer access to the vault')
param secretsOfficerObjectId string = ''

var tags = { 
  'azd-env-name': environmentName
  Environment: environmentName
  Application: 'CodeStory'
  ManagedBy: 'azd'
}

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Resource name generation
var resourceGroupName_computed = !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
var containerAppsEnvName_computed = !empty(containerAppsEnvName) ? containerAppsEnvName : '${abbrs.appManagedEnvironments}${environmentName}'
var logAnalyticsWorkspaceName_computed = !empty(logAnalyticsWorkspaceName) ? logAnalyticsWorkspaceName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
var appInsightsName_computed = !empty(appInsightsName) ? appInsightsName : '${abbrs.insightsComponents}${resourceToken}'
var containerRegistryName_computed = !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
var keyVaultName_computed = !empty(keyVaultName) ? keyVaultName : '${abbrs.keyVaultVaults}${resourceToken}'
var neo4jName_computed = !empty(neo4jName) ? neo4jName : '${abbrs.appContainerApps}neo4j-${resourceToken}'
var redisName_computed = !empty(redisName) ? redisName : '${abbrs.cacheRedis}${resourceToken}'
var serviceName_computed = !empty(serviceName) ? serviceName : '${abbrs.appContainerApps}service-${resourceToken}'
var workerName_computed = !empty(workerName) ? workerName : '${abbrs.appContainerApps}worker-${resourceToken}'
var mcpName_computed = !empty(mcpName) ? mcpName : '${abbrs.appContainerApps}mcp-${resourceToken}'
var guiName_computed = !empty(guiName) ? guiName : '${abbrs.appContainerApps}gui-${resourceToken}'

// 1. Create a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName_computed
  location: location
  tags: tags
}

// 2. Deploy all resources to the resource group
module infrastructure './infrastructure.bicep' = {
  scope: resourceGroup
  name: 'infrastructure'
  params: {
    location: location
    tags: tags
    containerAppsEnvName: containerAppsEnvName_computed
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName_computed
    appInsightsName: appInsightsName_computed
    containerRegistryName: containerRegistryName_computed
    keyVaultName: keyVaultName_computed
    neo4jName: neo4jName_computed
    neo4jUsername: neo4jUsername
    neo4jPassword: neo4jPassword
    redisName: redisName_computed
    redisSku: redisSku
    redisCapacity: redisCapacity
    serviceName: serviceName_computed
    serviceImage: !empty(serviceImage) ? serviceImage : 'nginx:latest' // Default placeholder
    servicePort: servicePort
    serviceReplicas: serviceReplicas
    serviceMemory: serviceMemory
    serviceCpu: serviceCpu
    workerName: workerName_computed
    workerImage: !empty(workerImage) ? workerImage : 'nginx:latest' // Default placeholder
    workerReplicas: workerReplicas
    workerMemory: workerMemory
    workerCpu: workerCpu
    mcpName: mcpName_computed
    mcpImage: !empty(mcpImage) ? mcpImage : 'nginx:latest' // Default placeholder
    mcpPort: mcpPort
    mcpReplicas: mcpReplicas
    mcpMemory: mcpMemory
    mcpCpu: mcpCpu
    mcpClientId: mcpClientId
    mcpClientSecret: mcpClientSecret
    authEnabled: authEnabled
    guiName: guiName_computed
    guiImage: !empty(guiImage) ? guiImage : 'nginx:latest' // Default placeholder
    guiPort: guiPort
    guiReplicas: guiReplicas
    guiMemory: guiMemory
    guiCpu: guiCpu
    openaiApiKey: openaiApiKey
    azureOpenaiApiKey: azureOpenaiApiKey
    secretsOfficerObjectId: secretsOfficerObjectId
  }
}

// 3. Output important variables
output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = infrastructure.outputs.containerRegistryLoginServer
output AZURE_KEY_VAULT_NAME string = infrastructure.outputs.keyVaultName
output AZURE_SERVICE_FQDN string = infrastructure.outputs.serviceFqdn
output AZURE_MCP_FQDN string = infrastructure.outputs.mcpFqdn
output AZURE_GUI_FQDN string = infrastructure.outputs.guiFqdn
output AZURE_NEO4J_FQDN string = infrastructure.outputs.neo4jFqdn
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId