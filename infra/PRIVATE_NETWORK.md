# Private Data Plane

The public Static Web App remains internet-accessible. The App Service also keeps
public inbound access because browser-hosted JavaScript calls it directly.
App Service WebSockets remain enabled for Voice Live connections from the
public frontend.

Private endpoints and DNS are configured for:

- App Service
- Blob Storage
- Microsoft Foundry

Azure AI Search private endpoint deployment is optional in
`private-network.bicep` and currently disabled because `mstech-demo-search-free` runs
on the Free tier for the demo. Free-tier Azure AI Search does not support private
endpoints or managed identity data-plane authorization.

App Service uses VNet integration for outbound traffic. Blob Storage remains
private. The free Search service uses its public HTTPS endpoint with a Search key,
and indexing is performed manually by pushing document chunks into the index.

Public network access is disabled for Blob Storage and private backend resources
where supported. Azure AI Search is the cost-saving exception while it stays on
the Free tier.

If Search is moved back to Basic or higher, set `enableSearchPrivateEndpoint=true`
when deploying `private-network.bicep`, approve the Search-managed Blob Storage
private endpoint connection, set the Search indexer's
`parameters.configuration.executionEnvironment` value to `private`, and disable
public network access for Search after validation.
