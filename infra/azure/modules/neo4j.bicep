@description('Name of the Neo4j Container App')
param name string

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to Neo4j Container App')
param tags object = {}

@description('Container Apps Environment ID')
param containerAppsEnvId string

@description('Neo4j username')
param username string = 'neo4j'

// This parameter is not used directly in this template
// as we retrieve the password from Key Vault instead
@secure()
param password string = ''

@description('Key Vault name for storing secrets')
param keyVaultName string

var neo4jImage = 'neo4j:5.20.0'
var neo4jPort = 7474
var neo4jBoltPort = 7687

resource neo4jContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvId
    configuration: {
      ingress: {
        external: true
        targetPort: neo4jPort
        transport: 'http'
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
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
          name: 'neo4j'
          image: neo4jImage
          resources: {
            cpu: json('1.0')
            memory: '2.0Gi'
          }
          env: [
            {
              name: 'NEO4J_AUTH'
              value: '${username}/$(neo4j-password)'
            }
            {
              name: 'NEO4J_PLUGINS'
              value: '["apoc", "graph-data-science"]'
            }
            {
              name: 'NEO4J_dbms_memory_heap_initial__size'
              value: '512m'
            }
            {
              name: 'NEO4J_dbms_memory_heap_max__size'
              value: '1G'
            }
            {
              name: 'NEO4J_dbms_memory_pagecache_size'
              value: '512m'
            }
          ]
          volumeMounts: [
            {
              mountPath: '/data'
              volumeName: 'neo4j-data'
            }
            {
              mountPath: '/logs'
              volumeName: 'neo4j-logs'
            }
          ]
          probes: [
            {
              type: 'startup'
              httpGet: {
                path: '/'
                port: neo4jPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 30
              periodSeconds: 10
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 5
            }
            {
              type: 'liveness'
              httpGet: {
                path: '/'
                port: neo4jPort
                scheme: 'HTTP'
              }
              periodSeconds: 30
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
      volumes: [
        {
          name: 'neo4j-data'
          storageType: 'AzureFile'
          storageName: 'neo4j-data-storage'
        }
        {
          name: 'neo4j-logs'
          storageType: 'AzureFile'
          storageName: 'neo4j-logs-storage'
        }
      ]
    }
  }
}

resource neo4jBoltContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${name}-bolt'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvId
    configuration: {
      ingress: {
        external: true
        targetPort: neo4jBoltPort
        transport: 'tcp'
        allowInsecure: false
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'neo4j-bolt'
          image: 'nginx:alpine'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          command: [
            '/bin/sh'
            '-c'
          ]
          args: [
            'nginx -g "daemon off;" && echo "server { listen 7687; location / { proxy_pass ${neo4jContainerApp.properties.configuration.ingress.fqdn}:7687; proxy_http_version 1.1; } }" > /etc/nginx/conf.d/default.conf && nginx -s reload'
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output id string = neo4jContainerApp.id
output name string = neo4jContainerApp.name
output fqdn string = neo4jContainerApp.properties.configuration.ingress.fqdn
output boltFqdn string = neo4jBoltContainerApp.properties.configuration.ingress.fqdn