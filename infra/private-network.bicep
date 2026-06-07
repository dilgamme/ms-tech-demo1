param location string = 'westeurope'
param webAppName string = 'mstech-demo-router-api'
param searchServiceName string = 'mstech-demo-search-free'
param storageAccountName string = 'mstechdemoragstorage'
param foundryAccountName string = 'ms-tech-demo-resource-we'
param routerExperimentAccountName string = 'ms-tech-demo1-router-se'
param enablePrivateEndpoints bool = false
param enableSearchPrivateEndpoint bool = false

resource webApp 'Microsoft.Web/sites@2023-12-01' existing = {
  name: webAppName
}

resource searchService 'Microsoft.Search/searchServices@2025-05-01' existing = {
  name: searchServiceName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryAccountName
}

resource routerExperimentAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: routerExperimentAccountName
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-mstech-demo'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
    privateEndpointVNetPolicies: 'Disabled'
    subnets: [
      {
        name: 'snet-appservice-integration'
        properties: {
          addressPrefix: '10.42.1.0/24'
          delegations: [
            {
              name: '0'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '10.42.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

resource appServiceSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: vnet
  name: 'snet-appservice-integration'
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: vnet
  name: 'snet-private-endpoints'
}

resource webAppVnetIntegration 'Microsoft.Web/sites/networkConfig@2023-12-01' = {
  parent: webApp
  name: 'virtualNetwork'
  properties: {
    subnetResourceId: appServiceSubnet.id
    swiftSupported: true
  }
}

var privateDnsZoneNames = [
  'privatelink.azurewebsites.net'
  'privatelink.search.windows.net'
  'privatelink.blob.${environment().suffixes.storage}'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
]

resource privateDnsZones 'Microsoft.Network/privateDnsZones@2024-06-01' = [for zoneName in privateDnsZoneNames: if (enablePrivateEndpoints) {
  name: zoneName
  location: 'global'
}]

resource privateDnsLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (zoneName, index) in privateDnsZoneNames: if (enablePrivateEndpoints) {
  parent: privateDnsZones[index]
  name: 'link-vnet-mstech-demo-${replace(zoneName, '.', '-')}'
  location: 'global'
  properties: {
    registrationEnabled: false
    resolutionPolicy: 'Default'
    virtualNetwork: {
      id: vnet.id
    }
  }
}]

resource webAppPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-mstech-demo-router-api'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: 'pec-mstech-demo-router-api'
        properties: {
          privateLinkServiceId: webApp.id
          groupIds: [
            'sites'
          ]
        }
      }
    ]
  }
}

resource searchPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (enablePrivateEndpoints && enableSearchPrivateEndpoint) {
  name: 'pe-mstech-demo-search-free'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: 'pec-mstech-demo-search-free'
        properties: {
          privateLinkServiceId: searchService.id
          groupIds: [
            'searchService'
          ]
        }
      }
    ]
  }
}

resource storagePrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-mstech-demo-ragstorage-blob'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: 'pec-mstech-demo-ragstorage-blob'
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'blob'
          ]
        }
      }
    ]
  }
}

resource foundryPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-mstech-demo-foundry'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: 'pec-mstech-demo-foundry'
        properties: {
          privateLinkServiceId: foundryAccount.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource routerExperimentPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-ms-tech-demo1-router-se'
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: 'pec-ms-tech-demo1-router-se'
        properties: {
          privateLinkServiceId: routerExperimentAccount.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource webAppPrivateDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (enablePrivateEndpoints) {
  parent: webAppPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'azurewebsites'
        properties: {
          privateDnsZoneId: privateDnsZones[0].id
        }
      }
    ]
  }
}

resource searchPrivateDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (enablePrivateEndpoints && enableSearchPrivateEndpoint) {
  parent: searchPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'search'
        properties: {
          privateDnsZoneId: privateDnsZones[1].id
        }
      }
    ]
  }
}

resource storagePrivateDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (enablePrivateEndpoints) {
  parent: storagePrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob'
        properties: {
          privateDnsZoneId: privateDnsZones[2].id
        }
      }
    ]
  }
}

resource foundryPrivateDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (enablePrivateEndpoints) {
  parent: foundryPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cognitiveservices'
        properties: {
          privateDnsZoneId: privateDnsZones[3].id
        }
      }
      {
        name: 'openai'
        properties: {
          privateDnsZoneId: privateDnsZones[4].id
        }
      }
      {
        name: 'services-ai'
        properties: {
          privateDnsZoneId: privateDnsZones[5].id
        }
      }
    ]
  }
}

resource routerExperimentPrivateDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (enablePrivateEndpoints) {
  parent: routerExperimentPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cognitiveservices'
        properties: {
          privateDnsZoneId: privateDnsZones[3].id
        }
      }
      {
        name: 'openai'
        properties: {
          privateDnsZoneId: privateDnsZones[4].id
        }
      }
      {
        name: 'services-ai'
        properties: {
          privateDnsZoneId: privateDnsZones[5].id
        }
      }
    ]
  }
}

resource searchStorageSharedPrivateLink 'Microsoft.Search/searchServices/sharedPrivateLinkResources@2025-05-01' = if (enablePrivateEndpoints && enableSearchPrivateEndpoint) {
  parent: searchService
  name: 'spl-mstech-demo-ragstorage-blob'
  properties: {
    groupId: 'blob'
    privateLinkResourceId: storageAccount.id
    requestMessage: 'Allow Azure AI Search private indexer access to RAG blob storage.'
    status: 'Approved'
  }
}

output vnetId string = vnet.id
output appServicePrivateEndpointId string = enablePrivateEndpoints ? webAppPrivateEndpoint.id : ''
output searchPrivateEndpointId string = enablePrivateEndpoints && enableSearchPrivateEndpoint ? searchPrivateEndpoint.id : ''
output storagePrivateEndpointId string = enablePrivateEndpoints ? storagePrivateEndpoint.id : ''
output foundryPrivateEndpointId string = enablePrivateEndpoints ? foundryPrivateEndpoint.id : ''
output routerExperimentPrivateEndpointId string = enablePrivateEndpoints ? routerExperimentPrivateEndpoint.id : ''
