@description('Name of the Container Apps Environment')
param name string

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to the Container Apps Environment')
param tags object = {}

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('Application Insights Instrumentation Key')
param appInsightsInstrumentationKey string

@description('Enable detailed monitoring for container apps')
param enableDetailedMonitoring bool = false

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    zoneRedundant: false
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// Create the environment level Dapr components
resource daprComponent 'Microsoft.App/managedEnvironments/daprComponents@2023-05-01' = {
  name: 'appinsights'
  parent: containerAppsEnvironment
  properties: {
    componentType: 'bindings.azure.applicationinsights'
    version: 'v1'
    metadata: [
      {
        name: 'instrumentationKey'
        value: appInsightsInstrumentationKey
      }
    ]
    scopes: []
  }
}

output id string = containerAppsEnvironment.id
output name string = containerAppsEnvironment.name