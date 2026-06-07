# Private Data Plane

Private endpoints are temporarily disabled as of June 7, 2026 to reduce demo
costs. The VNet, App Service integration subnet, and private endpoint subnet remain
in place so the private data plane can be restored later.

Deploying `private-network.bicep` does not recreate private endpoints unless
`enablePrivateEndpoints=true` is explicitly supplied.

The public Static Web App remains internet-accessible. The App Service also keeps
public inbound access because browser-hosted JavaScript calls it directly.
App Service WebSockets remain enabled for Voice Live connections from the
public frontend.

When enabled, private endpoints and DNS are configured for:

- App Service
- Blob Storage
- Microsoft Foundry

Azure AI Search private endpoint deployment is optional in
`private-network.bicep` and currently disabled because `mstech-demo-search-free` runs
on the Free tier for the demo. Free-tier Azure AI Search does not support private
endpoints or managed identity data-plane authorization.

App Service retains VNet integration for outbound traffic. Blob Storage and the
free Search service currently use public HTTPS endpoints, and indexing is
performed manually by pushing document chunks into the Search index.

During the temporary public-network period, public network access is enabled for
the active Foundry account, router account, and Blob Storage. Managed identity,
service authentication, application authentication, and HTTPS remain active.

If Search is moved back to Basic or higher, set `enableSearchPrivateEndpoint=true`
when deploying `private-network.bicep`, approve the Search-managed Blob Storage
private endpoint connection, set the Search indexer's
`parameters.configuration.executionEnvironment` value to `private`, and disable
public network access for Search after validation.
