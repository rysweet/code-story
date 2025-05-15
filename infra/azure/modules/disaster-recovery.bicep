@description('Name prefix for disaster recovery resources')
param namePrefix string

@description('Azure region to deploy primary resources')
param primaryLocation string

@description('Azure region to deploy secondary resources (for geo-redundancy)')
param secondaryLocation string

@description('Tags to apply to resources')
param tags object = {}

@description('ID of Log Analytics Workspace')
param logAnalyticsWorkspaceId string

@description('Neo4j database backup retention in days')
param backupRetentionDays int = 7

@description('Storage account tier')
@allowed([
  'Standard'
  'Premium'
])
param storageTier string = 'Standard'

@description('Storage account replication')
@allowed([
  'LRS'
  'GRS'
  'ZRS'
  'GZRS'
])
param storageReplication string = 'GRS'

// Create disaster recovery storage account for automated backups
resource backupStorageAccount 'Microsoft.Storage/storageAccounts@2021-08-01' = {
  name: '${namePrefix}backupsa'
  location: primaryLocation
  tags: tags
  sku: {
    name: '${storageTier}_${storageReplication}'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// Create container for Neo4j backups
resource neo4jBackupContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-08-01' = {
  name: '${backupStorageAccount.name}/default/neo4j-backups'
  properties: {
    publicAccess: 'None'
  }
}

// Create container for configuration backups
resource configBackupContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-08-01' = {
  name: '${backupStorageAccount.name}/default/config-backups'
  properties: {
    publicAccess: 'None'
  }
}

// Create retention lifecycle policy
resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2021-08-01' = {
  name: '${backupStorageAccount.name}/default'
  properties: {
    policy: {
      rules: [
        {
          name: 'RetentionPolicy'
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [
                'blockBlob'
              ]
              prefixMatch: [
                'neo4j-backups/',
                'config-backups/'
              ]
            }
            actions: {
              baseBlob: {
                delete: {
                  daysAfterModificationGreaterThan: backupRetentionDays
                }
              }
            }
          }
        }
      ]
    }
  }
}

// Create secondary storage account in another region for geo-redundancy
resource secondaryBackupStorageAccount 'Microsoft.Storage/storageAccounts@2021-08-01' = {
  name: '${namePrefix}backupsa2'
  location: secondaryLocation
  tags: tags
  sku: {
    name: '${storageTier}_${storageReplication}'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// Create secondary containers
resource secondaryNeo4jBackupContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-08-01' = {
  name: '${secondaryBackupStorageAccount.name}/default/neo4j-backups'
  properties: {
    publicAccess: 'None'
  }
}

resource secondaryConfigBackupContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-08-01' = {
  name: '${secondaryBackupStorageAccount.name}/default/config-backups'
  properties: {
    publicAccess: 'None'
  }
}

// Create Automation Account for scheduled backups
resource automationAccount 'Microsoft.Automation/automationAccounts@2021-06-22' = {
  name: '${namePrefix}-dr-automation'
  location: primaryLocation
  tags: tags
  properties: {
    sku: {
      name: 'Basic'
    }
    encryption: {
      keySource: 'Microsoft.Automation'
    }
  }
}

// Create RunAs account credentials with limited access (in a real implementation)
// Note: For full implementation, you would need to create certificates and service principals

// Create runbook for Neo4j backup
resource neo4jBackupRunbook 'Microsoft.Automation/automationAccounts/runbooks@2019-06-01' = {
  name: '${automationAccount.name}/Neo4jBackup'
  location: primaryLocation
  properties: {
    runbookType: 'PowerShell'
    logVerbose: true
    logProgress: true
    logActivity: true
    description: 'Runbook to backup Neo4j database'
    publishContentLink: {
      uri: 'https://raw.githubusercontent.com/example/neo4j-backup.ps1'
      version: '1.0.0.0'
    }
  }
}

// Create runbook for configuration backup
resource configBackupRunbook 'Microsoft.Automation/automationAccounts/runbooks@2019-06-01' = {
  name: '${automationAccount.name}/ConfigBackup'
  location: primaryLocation
  properties: {
    runbookType: 'PowerShell'
    logVerbose: true
    logProgress: true
    logActivity: true
    description: 'Runbook to backup application configuration'
    publishContentLink: {
      uri: 'https://raw.githubusercontent.com/example/config-backup.ps1'
      version: '1.0.0.0'
    }
  }
}

// Schedule daily backups
resource dailyBackupSchedule 'Microsoft.Automation/automationAccounts/schedules@2020-01-13-preview' = {
  name: '${automationAccount.name}/DailyBackup'
  properties: {
    description: 'Schedule for daily backups'
    startTime: '2023-01-01T02:00:00+00:00'
    frequency: 'Day'
    interval: 1
    timeZone: 'UTC'
  }
}

// Link schedule to Neo4j backup runbook
resource neo4jBackupJobSchedule 'Microsoft.Automation/automationAccounts/jobSchedules@2020-01-13-preview' = {
  name: guid('${automationAccount.name}/Neo4jBackupSchedule')
  properties: {
    runbook: {
      name: neo4jBackupRunbook.name
    }
    schedule: {
      name: dailyBackupSchedule.name
    }
  }
  parent: automationAccount
}

// Link schedule to configuration backup runbook
resource configBackupJobSchedule 'Microsoft.Automation/automationAccounts/jobSchedules@2020-01-13-preview' = {
  name: guid('${automationAccount.name}/ConfigBackupSchedule')
  properties: {
    runbook: {
      name: configBackupRunbook.name
    }
    schedule: {
      name: dailyBackupSchedule.name
    }
  }
  parent: automationAccount
}

// Alert rule for backup failures
resource actionGroup 'microsoft.insights/actionGroups@2019-06-01' = {
  name: '${namePrefix}-dr-alerts'
  location: 'global'
  properties: {
    groupShortName: 'dr-alerts'
    enabled: true
    emailReceivers: [
      {
        name: 'DR Alerts'
        emailAddress: 'dr-alerts@example.com'
        useCommonAlertSchema: true
      }
    ]
  }
}

// Alert for backup failures
resource backupFailureAlert 'microsoft.insights/scheduledQueryRules@2021-08-01' = {
  name: '${namePrefix}-backup-failure-alert'
  location: primaryLocation
  properties: {
    displayName: 'DR Backup Failure Alert'
    description: 'Alerts when backup jobs fail'
    severity: 1
    enabled: true
    evaluationFrequency: 'PT1H'
    scopes: [
      logAnalyticsWorkspaceId
    ]
    targetResourceTypes: [
      'microsoft.operationalinsights/workspaces'
    ]
    windowSize: 'PT1H'
    criteria: {
      allOf: [
        {
          query: 'AzureDiagnostics\n| where Category == "JobStreams" and StreamType_s == "Error"\n| where RunbookName_s in ("Neo4jBackup", "ConfigBackup")\n| project TimeGenerated, RunbookName_s, OperationName, ResultDescription'
          timeAggregation: 'Count'
          dimensions: []
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: false
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
  }
}

// Outputs
output primaryBackupStorageAccountName string = backupStorageAccount.name
output secondaryBackupStorageAccountName string = secondaryBackupStorageAccount.name
output automationAccountName string = automationAccount.name