@description('Name of the GUI Container App')
param name string

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to GUI Container App')
param tags object = {}

@description('Container Apps Environment ID')
param containerAppsEnvId string

@description('Container Registry Name')
param containerRegistryName string

@description('Container image to deploy')
param image string

@description('Port to expose on the container')
param port int = 80

@description('Minimum number of replicas')
param minReplicas int = 1

@description('Maximum number of replicas')
param maxReplicas int = 3

@description('CPU cores to allocate')
param cpu string = '0.25'

@description('Memory to allocate')
param memory string = '0.5Gi'

@description('Managed Identity ID')
param managedIdentityId string

@description('Service URI (for API calls)')
param serviceUri string

@description('MCP URI (for MCP adapter)')
param mcpUri string

@description('Application Insights Instrumentation Key')
param appInsightsInstrumentationKey string

@description('Entra Auth Settings - True to enable Entra authentication')
param enableEntraAuth bool = false

@description('Entra client ID for frontend authentication')
param entraClientId string = ''

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource gui 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvId
    configuration: {
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: true
        targetPort: port
        transport: 'http'
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'gui'
          image: containerRegistry.properties.loginServer != '' ? '${containerRegistry.properties.loginServer}/${image}' : image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            {
              name: 'API_BASE_URL'
              value: serviceUri
            }
            {
              name: 'MCP_BASE_URL'
              value: mcpUri
            }
            {
              name: 'VITE_ENABLE_AUTH'
              value: string(enableEntraAuth)
            }
            {
              name: 'VITE_ENTRA_CLIENT_ID'
              value: entraClientId
            }
            {
              name: 'VITE_ENTRA_TENANT_ID'
              value: 'your-tenant-id'
            }
            {
              name: 'VITE_ENTRA_REDIRECT_URI'
              value: 'https://${name}.azurecontainerapps.io/'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: 'InstrumentationKey=${appInsightsInstrumentationKey}'
            }
          ]
          probes: [
            {
              type: 'startup'
              httpGet: {
                path: '/'
                port: port
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 1
            }
            {
              type: 'liveness'
              httpGet: {
                path: '/'
                port: port
                scheme: 'HTTP'
              }
              periodSeconds: 30
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 1
            }
            {
              type: 'readiness'
              httpGet: {
                path: '/'
                port: port
                scheme: 'HTTP'
              }
              periodSeconds: 10
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 1
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scale-rule'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output id string = gui.id
output name string = gui.name
output fqdn string = gui.properties.configuration.ingress.fqdn