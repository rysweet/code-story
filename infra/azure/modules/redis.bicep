@description('Name of the Redis Cache')
param name string

@description('Azure region to deploy resources')
param location string

@description('SKU for the Redis Cache')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param sku string = 'Basic'

@description('The size of the Redis cache to deploy')
@allowed([
  0
  1
  2
  3
  4
  5
  6
])
param capacity int = 0

@description('Tags to apply to the Redis Cache')
param tags object = {}

resource redis 'Microsoft.Cache/redis@2022-06-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: sku
      family: sku == 'Premium' ? 'P' : 'C'
      capacity: capacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

output id string = redis.id
output name string = redis.name
output hostName string = redis.properties.hostName
output port int = redis.properties.sslPort
output connectionString string = '${redis.properties.hostName}:${redis.properties.sslPort},password=${listKeys(redis.id, '2022-06-01').primaryKey},ssl=True,abortConnect=False'