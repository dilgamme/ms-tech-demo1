# Private Data Plane

The public Static Web App remains internet-accessible. The App Service also keeps
public inbound access because browser-hosted JavaScript calls it directly.
App Service WebSockets remain enabled for Voice Live connections from the
public frontend.

Private endpoints and DNS are configured for:

- App Service
- Azure AI Search
- Blob Storage
- Microsoft Foundry

App Service uses VNet integration for outbound traffic. Azure AI Search uses a
shared private link and its private execution environment to read Blob Storage.

Public network access is disabled for Azure AI Search and Blob Storage.

Microsoft Foundry keeps public network access enabled because Azure AI Search
shared private links do not support the consolidated AIServices embedding
resource. App Service resolves the Foundry endpoint privately through the VNet;
Search uses the public Foundry endpoint with managed identity.

After deploying `private-network.bicep`, approve the Search-managed Blob Storage
private endpoint connection, set the Search indexer's
`parameters.configuration.executionEnvironment` value to `private`, and disable
public network access for Search and Blob Storage after validation.
