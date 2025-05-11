@description('Name of the Service Container App')
param name string

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to Service Container App')
param tags object = {}

@description('Container Apps Environment ID')
param containerAppsEnvId string

@description('Container Registry Name')
param containerRegistryName string

@description('Container image to deploy')
param image string

@description('Port to expose on the container')
param port int = 8000

@description('Minimum number of replicas')
param minReplicas int = 1

@description('Maximum number of replicas')
param maxReplicas int = 1

@description('CPU cores to allocate')
param cpu string = '0.5'

@description('Memory to allocate')
param memory string = '1.0Gi'

@description('Managed Identity ID')
param managedIdentityId string

@description('Neo4j URI')
param neo4jUri string

@description('Neo4j Username')
param neo4jUsername string = 'neo4j'

@description('Key Vault name for storing secrets')
param keyVaultName string

@description('Redis URI')
param redisUri string

@description('Application Insights Instrumentation Key')
param appInsightsInstrumentationKey string

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource service 'Microsoft.App/containerApps@2023-05-01' = {
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
        corsPolicy: {
          allowedOrigins: [
            'https://*.azurecontainerapps.io'
            'http://localhost:5173'
          ]
          allowedMethods: [
            'GET'
            'POST'
            'PUT'
            'DELETE'
            'OPTIONS'
            'HEAD'
            'PATCH'
          ]
          allowedHeaders: [
            '*'
          ]
          exposeHeaders: [
            '*'
          ]
          maxAge: 3600
          allowCredentials: true
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: managedIdentityId
        }
      ]
      secrets: [
        {
          name: 'neo4j-password'
          keyVaultUrl: 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/secrets/neo4j-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'service'
          image: containerRegistry.properties.loginServer != '' ? '${containerRegistry.properties.loginServer}/${image}' : image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            {
              name: 'NEO4J_URI'
              value: neo4jUri
            }
            {
              name: 'NEO4J_USER'
              value: neo4jUsername
            }
            {
              name: 'NEO4J_PASSWORD'
              secretRef: 'neo4j-password'
            }
            {
              name: 'REDIS_URI'
              value: redisUri
            }
            {
              name: 'SERVICE_HOST'
              value: '0.0.0.0'
            }
            {
              name: 'SERVICE_PORT'
              value: string(port)
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
            {
              name: 'ENVIRONMENT'
              value: 'production'
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
                path: '/health'
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
                path: '/health'
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
                path: '/health'
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

output id string = service.id
output name string = service.name
output fqdn string = service.properties.configuration.ingress.fqdn