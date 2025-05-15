@description('Name prefix for monitoring resources')
param namePrefix string

@description('Azure region to deploy resources')
param location string

@description('Tags to apply to resources')
param tags object = {}

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('Application Insights ID')
param appInsightsId string

@description('Resource IDs of container apps to monitor')
param containerAppIds array = []

@description('Resource ID of Neo4j container')
param neo4jContainerId string = ''

@description('Email address for alert notifications')
param alertNotificationEmail string = ''

@description('Enable detailed monitoring')
param enableDetailedMonitoring bool = false

// Create a dashboard for the application
resource dashboard 'Microsoft.Portal/dashboards@2020-09-01-preview' = {
  name: '${namePrefix}-dashboard'
  location: location
  tags: tags
  properties: {
    lenses: [
      {
        order: 0
        parts: [
          {
            position: {
              x: 0
              y: 0
              colSpan: 6
              rowSpan: 4
            }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                  value: 'workspace'
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                  value: {
                    SubscriptionId: subscription().subscriptionId
                    ResourceGroup: resourceGroup().name
                    Name: appInsightsId
                  }
                }
                {
                  name: 'Scope'
                  isOptional: true
                  value: {
                    ResourceIds: [
                      appInsightsId
                    ]
                  }
                }
                {
                  name: 'PartId'
                  isOptional: true
                  value: 'Overview'
                }
                {
                  name: 'Version'
                  isOptional: true
                  value: '2.0'
                }
                {
                  name: 'TimeRange'
                  isOptional: true
                  value: 'PT12H'
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                  value: ''
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                  value: {
                    scope: 'hierarchy'
                  }
                }
                {
                  name: 'Query'
                  isOptional: true
                  value: 'requests\n| summarize count() by resultCode, bin(timestamp, 5m)\n| render timechart'
                }
                {
                  name: 'ControlType'
                  isOptional: true
                  value: 'AnalyticsGrid'
                }
                {
                  name: 'SpecificChart'
                  isOptional: true
                  value: 'Line'
                }
                {
                  name: 'PartTitle'
                  isOptional: true
                  value: 'HTTP Response Codes'
                }
                {
                  name: 'PartSubTitle'
                  isOptional: true
                  value: 'Code Story Service'
                }
              ]
              type: 'Extension/AppInsightsExtension/PartType/AnalyticsPart'
              settings: {}
              asset: {
                idInputName: 'ComponentId'
                type: 'ApplicationInsights'
              }
            }
          }
          {
            position: {
              x: 6
              y: 0
              colSpan: 6
              rowSpan: 4
            }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                  value: 'workspace'
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                  value: {
                    SubscriptionId: subscription().subscriptionId
                    ResourceGroup: resourceGroup().name
                    Name: appInsightsId
                  }
                }
                {
                  name: 'Scope'
                  isOptional: true
                  value: {
                    ResourceIds: [
                      appInsightsId
                    ]
                  }
                }
                {
                  name: 'PartId'
                  isOptional: true
                  value: 'Performance'
                }
                {
                  name: 'Version'
                  isOptional: true
                  value: '2.0'
                }
                {
                  name: 'TimeRange'
                  isOptional: true
                  value: 'PT12H'
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                  value: ''
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                  value: {
                    scope: 'hierarchy'
                  }
                }
                {
                  name: 'Query'
                  isOptional: true
                  value: 'requests\n| summarize responseTime=avg(duration) by bin(timestamp, 5m)\n| render timechart'
                }
                {
                  name: 'ControlType'
                  isOptional: true
                  value: 'AnalyticsChart'
                }
                {
                  name: 'SpecificChart'
                  isOptional: true
                  value: 'Line'
                }
                {
                  name: 'PartTitle'
                  isOptional: true
                  value: 'Response Time'
                }
                {
                  name: 'PartSubTitle'
                  isOptional: true
                  value: 'Average Duration (ms)'
                }
              ]
              type: 'Extension/AppInsightsExtension/PartType/AnalyticsPart'
              settings: {}
              asset: {
                idInputName: 'ComponentId'
                type: 'ApplicationInsights'
              }
            }
          }
          {
            position: {
              x: 0
              y: 4
              colSpan: 6
              rowSpan: 4
            }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                  value: 'workspace'
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                  value: {
                    SubscriptionId: subscription().subscriptionId
                    ResourceGroup: resourceGroup().name
                    Name: appInsightsId
                  }
                }
                {
                  name: 'Scope'
                  isOptional: true
                  value: {
                    ResourceIds: [
                      appInsightsId
                    ]
                  }
                }
                {
                  name: 'PartId'
                  isOptional: true
                  value: 'Failures'
                }
                {
                  name: 'Version'
                  isOptional: true
                  value: '2.0'
                }
                {
                  name: 'TimeRange'
                  isOptional: true
                  value: 'PT12H'
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                  value: ''
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                  value: {
                    scope: 'hierarchy'
                  }
                }
                {
                  name: 'Query'
                  isOptional: true
                  value: 'exceptions\n| summarize count() by type, bin(timestamp, 5m)\n| render timechart'
                }
                {
                  name: 'ControlType'
                  isOptional: true
                  value: 'AnalyticsChart'
                }
                {
                  name: 'SpecificChart'
                  isOptional: true
                  value: 'Line'
                }
                {
                  name: 'PartTitle'
                  isOptional: true
                  value: 'Application Exceptions'
                }
                {
                  name: 'PartSubTitle'
                  isOptional: true
                  value: 'Count by Exception Type'
                }
              ]
              type: 'Extension/AppInsightsExtension/PartType/AnalyticsPart'
              settings: {}
              asset: {
                idInputName: 'ComponentId'
                type: 'ApplicationInsights'
              }
            }
          }
          {
            position: {
              x: 6
              y: 4
              colSpan: 6
              rowSpan: 4
            }
            metadata: {
              inputs: [
                {
                  name: 'resourceTypeMode'
                  isOptional: true
                  value: 'workspace'
                }
                {
                  name: 'ComponentId'
                  isOptional: true
                  value: {
                    SubscriptionId: subscription().subscriptionId
                    ResourceGroup: resourceGroup().name
                    Name: appInsightsId
                  }
                }
                {
                  name: 'Scope'
                  isOptional: true
                  value: {
                    ResourceIds: [
                      appInsightsId
                    ]
                  }
                }
                {
                  name: 'PartId'
                  isOptional: true
                  value: 'Performance'
                }
                {
                  name: 'Version'
                  isOptional: true
                  value: '2.0'
                }
                {
                  name: 'TimeRange'
                  isOptional: true
                  value: 'PT12H'
                }
                {
                  name: 'DashboardId'
                  isOptional: true
                  value: ''
                }
                {
                  name: 'DraftRequestParameters'
                  isOptional: true
                  value: {
                    scope: 'hierarchy'
                  }
                }
                {
                  name: 'Query'
                  isOptional: true
                  value: 'requests\n| where operation_Name contains "ingest"\n| extend requestName = operation_Name\n| summarize responseTime=avg(duration) by requestName, bin(timestamp, 5m)\n| render timechart'
                }
                {
                  name: 'ControlType'
                  isOptional: true
                  value: 'AnalyticsChart'
                }
                {
                  name: 'SpecificChart'
                  isOptional: true
                  value: 'Line'
                }
                {
                  name: 'PartTitle'
                  isOptional: true
                  value: 'Ingestion Performance'
                }
                {
                  name: 'PartSubTitle'
                  isOptional: true
                  value: 'Ingestion Operations'
                }
              ]
              type: 'Extension/AppInsightsExtension/PartType/AnalyticsPart'
              settings: {}
              asset: {
                idInputName: 'ComponentId'
                type: 'ApplicationInsights'
              }
            }
          }
        ]
      }
    ]
    metadata: {
      model: {
        timeRange: {
          value: {
            relative: {
              duration: 24
              timeUnit: 1
            }
          }
          type: 'MsPortalFx.Composition.Configuration.ValueTypes.TimeRange'
        }
        filterLocale: {
          value: 'en-us'
        }
        filters: {
          value: {
            MsPortalFx_TimeRange: {
              model: {
                format: 'utc'
                granularity: 'auto'
                relative: '12h'
              }
              displayCache: {
                name: 'UTC Time'
                value: 'Past 12 hours'
              }
              filteredPartIds: [
                'StartboardPart-AnalyticsPart-a0dbd3ee-323d-41e9-9e5d-6a1b2f3be9f6'
                'StartboardPart-AnalyticsPart-a0dbd3ee-323d-41e9-9e5d-6a1b2f3be9f7'
                'StartboardPart-AnalyticsPart-a0dbd3ee-323d-41e9-9e5d-6a1b2f3be9f8'
                'StartboardPart-AnalyticsPart-a0dbd3ee-323d-41e9-9e5d-6a1b2f3be9f9'
              ]
            }
          }
        }
      }
    }
  }
}

// Create alert rules
resource actionGroup 'microsoft.insights/actionGroups@2019-06-01' = if (!empty(alertNotificationEmail)) {
  name: '${namePrefix}-alerts'
  location: 'global'
  properties: {
    groupShortName: 'codestory'
    enabled: true
    emailReceivers: [
      {
        name: 'Email Alert'
        emailAddress: alertNotificationEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

// HTTP 5xx Errors Alert
resource httpErrorsAlert 'microsoft.insights/scheduledQueryRules@2021-08-01' = if (!empty(alertNotificationEmail)) {
  name: '${namePrefix}-http-5xx-errors'
  location: location
  properties: {
    displayName: 'HTTP 5xx Errors Alert'
    description: 'Alerts when HTTP 5xx errors exceed threshold'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      appInsightsId
    ]
    targetResourceTypes: [
      'microsoft.insights/components'
    ]
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: 'requests\n| where resultCode >= 500\n| summarize count() by bin(timestamp, 5m)\n| where count_ > 5'
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

// High Response Time Alert
resource highResponseTimeAlert 'microsoft.insights/scheduledQueryRules@2021-08-01' = if (!empty(alertNotificationEmail)) {
  name: '${namePrefix}-high-response-time'
  location: location
  properties: {
    displayName: 'High Response Time Alert'
    description: 'Alerts when average response time exceeds threshold'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      appInsightsId
    ]
    targetResourceTypes: [
      'microsoft.insights/components'
    ]
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: 'requests\n| summarize avg(duration) by bin(timestamp, 5m)\n| where avg_duration > 5000'
          timeAggregation: 'Average'
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

// Exception Rate Alert
resource exceptionRateAlert 'microsoft.insights/scheduledQueryRules@2021-08-01' = if (!empty(alertNotificationEmail)) {
  name: '${namePrefix}-exception-rate'
  location: location
  properties: {
    displayName: 'Exception Rate Alert'
    description: 'Alerts when exception rate exceeds threshold'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      appInsightsId
    ]
    targetResourceTypes: [
      'microsoft.insights/components'
    ]
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: 'exceptions\n| summarize count() by bin(timestamp, 5m)\n| where count_ > 10'
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

// CPU Usage Alert if container app IDs are provided
resource cpuUsageAlert 'microsoft.insights/scheduledQueryRules@2021-08-01' = if (!empty(alertNotificationEmail) && !empty(containerAppIds)) {
  name: '${namePrefix}-high-cpu-usage'
  location: location
  properties: {
    displayName: 'High CPU Usage Alert'
    description: 'Alerts when CPU usage exceeds threshold'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      logAnalyticsWorkspaceId
    ]
    targetResourceTypes: [
      'microsoft.operationalinsights/workspaces'
    ]
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: 'ContainerAppSystemLogs_CL\n| where ContainerAppName_s in~ ("service", "worker", "mcp")\n| where Log_s contains "cpu:"  \n| extend cpuUsage = extract("cpu: *([0-9.]+)%", 1, Log_s)\n| extend cpuUsageValue = todouble(cpuUsage)\n| where cpuUsageValue > 80\n| summarize AggregatedValue = max(cpuUsageValue) by bin(TimeGenerated, 5m), ContainerAppName_s'
          timeAggregation: 'Maximum'
          dimensions: [
            {
              name: 'ContainerAppName_s'
              operator: 'Include'
              values: [
                '*'
              ]
            }
          ]
          operator: 'GreaterThan'
          threshold: 80
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

// Memory Usage Alert if container app IDs are provided
resource memoryUsageAlert 'microsoft.insights/scheduledQueryRules@2021-08-01' = if (!empty(alertNotificationEmail) && !empty(containerAppIds)) {
  name: '${namePrefix}-high-memory-usage'
  location: location
  properties: {
    displayName: 'High Memory Usage Alert'
    description: 'Alerts when memory usage exceeds threshold'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      logAnalyticsWorkspaceId
    ]
    targetResourceTypes: [
      'microsoft.operationalinsights/workspaces'
    ]
    windowSize: 'PT5M'
    criteria: {
      allOf: [
        {
          query: 'ContainerAppSystemLogs_CL\n| where ContainerAppName_s in~ ("service", "worker", "mcp")\n| where Log_s contains "memory:"  \n| extend memoryUsage = extract("memory: *([0-9.]+)%", 1, Log_s)\n| extend memoryUsageValue = todouble(memoryUsage)\n| where memoryUsageValue > 80\n| summarize AggregatedValue = max(memoryUsageValue) by bin(TimeGenerated, 5m), ContainerAppName_s'
          timeAggregation: 'Maximum'
          dimensions: [
            {
              name: 'ContainerAppName_s'
              operator: 'Include'
              values: [
                '*'
              ]
            }
          ]
          operator: 'GreaterThan'
          threshold: 80
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

// Neo4j Disk Space Alert (if neo4j container ID is provided)
resource neo4jDiskSpaceAlert 'microsoft.insights/scheduledQueryRules@2021-08-01' = if (!empty(alertNotificationEmail) && !empty(neo4jContainerId)) {
  name: '${namePrefix}-neo4j-disk-space'
  location: location
  properties: {
    displayName: 'Neo4j Disk Space Alert'
    description: 'Alerts when Neo4j disk space exceeds threshold'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT15M'
    scopes: [
      logAnalyticsWorkspaceId
    ]
    targetResourceTypes: [
      'microsoft.operationalinsights/workspaces'
    ]
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: 'ContainerAppSystemLogs_CL\n| where ContainerAppName_s == "neo4j"\n| where Log_s contains "Disk usage:"  \n| extend diskUsage = extract("Disk usage: *([0-9.]+)%", 1, Log_s)\n| extend diskUsageValue = todouble(diskUsage)\n| where diskUsageValue > 80\n| summarize AggregatedValue = max(diskUsageValue) by bin(TimeGenerated, 15m)'
          timeAggregation: 'Maximum'
          dimensions: []
          operator: 'GreaterThan'
          threshold: 80
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

// Create a workbook for detailed application monitoring
resource workbook 'Microsoft.Insights/workbooks@2021-08-01' = if (enableDetailedMonitoring) {
  name: guid('${namePrefix}-workbook')
  location: location
  kind: 'shared'
  properties: {
    displayName: 'Code Story Detailed Monitoring'
    serializedData: loadTextContent('../templates/monitoring-workbook.json')
    sourceId: appInsightsId
    category: 'workbook'
    version: '1.0'
  }
}

output dashboardId string = dashboard.id
output dashboardName string = dashboard.name
output actionGroupId string = !empty(alertNotificationEmail) ? actionGroup.id : ''
output workbookId string = enableDetailedMonitoring ? workbook.id : ''