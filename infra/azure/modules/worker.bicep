@description('Name of the Worker Container App')
param name string

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to Worker Container App')
param tags object = {}

@description('Container Apps Environment ID')
param containerAppsEnvId string

@description('Container Registry Name')
param containerRegistryName string

@description('Container image to deploy')
param image string

@description('Port for health checks')
param healthPort int = 8080

@description('Minimum number of replicas')
param minReplicas int = 1

@description('Maximum number of replicas')
param maxReplicas int = 3

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

resource worker 'Microsoft.App/containerApps@2023-05-01' = {
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
          name: 'worker'
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
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
            {
              name: 'ENVIRONMENT'
              value: 'production'
            }
            {
              name: 'WORKER_CONCURRENCY'
              value: '4'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: 'InstrumentationKey=${appInsightsInstrumentationKey}'
            }
          ]
          // Note: Azure Container Apps doesn't support exec probes directly
          // In a real implementation, we would need to add a health endpoint
          // that executes the Celery ping command and returns the status
          probes: [
            {
              type: 'startup'
              httpGet: {
                path: '/health'
                port: healthPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              failureThreshold: 5
              successThreshold: 1
              timeoutSeconds: 3
            }
            {
              type: 'liveness'
              httpGet: {
                path: '/health'
                port: healthPort
                scheme: 'HTTP'
              }
              periodSeconds: 30
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'queue-based-autoscaling'
            custom: {
              type: 'redis'
              metadata: {
                host: redisUri
                port: '6379'
                queueName: 'celery'
                queueLength: '10'
                isExternalQueue: 'true'
              }
              auth: []
            }
          }
        ]
      }
    }
  }
}

output id string = worker.id
output name string = worker.name