# Private Endpoint Restore Record

## Current State

On June 7, 2026, five private endpoints and six private DNS zones were removed
from `rg-ms-tech-demo1` to reduce demo costs. The VNet and both subnets were kept.
App Service VNet integration was also kept.

Public network access is temporarily enabled for:

- `ms-tech-demo-resource-we`
- `ms-tech-demo1-router-se`
- `mstechdemoragstorage`

The active Free-tier Search service, `mstech-demo-search-free`, already uses its
public endpoint.

## Removed Private Endpoints

| Endpoint | Target | Group |
|---|---|---|
| `pe-mstech-demo-router-api` | App Service `mstech-demo-router-api` | `sites` |
| `pe-mstech-demo-ragstorage-blob` | Storage `mstechdemoragstorage` | `blob` |
| `pe-mstech-demo-foundry` | AI Services `ms-tech-demo-resource-we` | `account` |
| `pe-ms-tech-demo1-router-se` | AI Services `ms-tech-demo1-router-se` | `account` |
| `pe-mstech-demo-search` | Deleted legacy Search service `mstech-demo-search` | `searchService` |

Do not recreate the legacy Search endpoint. If Search is later upgraded from Free,
create `pe-mstech-demo-search-free` against `mstech-demo-search-free`.

## Removed Private DNS Zones

- `privatelink.azurewebsites.net`
- `privatelink.blob.core.windows.net`
- `privatelink.cognitiveservices.azure.com`
- `privatelink.openai.azure.com`
- `privatelink.search.windows.net`
- `privatelink.services.ai.azure.com`

Each zone used a VNet link named:

```text
link-vnet-mstech-demo-<zone-name-with-dashes>
```

## Restore Procedure

1. Deploy `infra/private-network.bicep` with `enablePrivateEndpoints=true`.
2. Keep `enableSearchPrivateEndpoint=false` while Search remains on the Free tier.
3. Verify App Service can reach Foundry, the router account, Voice Live, Translator,
   and Blob Storage through private DNS.
4. Set public network access to `Disabled` on the two active AI Services accounts
   and Blob Storage only after private connectivity is verified.
5. Run production health, routing, translation, RAG, image, and voice checks.

Example:

```bash
az deployment group create \
  --resource-group rg-ms-tech-demo1 \
  --template-file infra/private-network.bicep \
  --parameters enablePrivateEndpoints=true enableSearchPrivateEndpoint=false
```

## Cost Baseline

Before removal, June 2026 month-to-date actual cost was approximately:

| Resource type | Cost |
|---|---:|
| Private endpoints | `$7.34 USD` |
| Private DNS zones | `$0.61 USD` |

Cost data can lag, so charges may continue appearing briefly after deletion.
