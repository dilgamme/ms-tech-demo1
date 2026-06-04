# Microsoft Foundry Migration to West Europe

Migration completed on 2026-06-01.

## Current Topology

The application data path is aligned in West Europe:

| Resource | Name | Region |
|----------|------|--------|
| App Service | `mstech-demo-router-api` | West Europe |
| Storage account | `mstechdemoragstorage` | West Europe |
| Azure AI Search | `mstech-demo-search-free` | West Europe |
| Virtual network | `vnet-mstech-demo` | West Europe |
| Foundry AIServices account | `ms-tech-demo-resource-we` | West Europe |
| Foundry project | `ms-tech-demo1` | West Europe |

The backend uses:

```text
AZURE_OPENAI_ENDPOINT=https://ms-tech-demo-resource-we.cognitiveservices.azure.com/
```

## Model Deployments

The following deployments are active in `ms-tech-demo-resource-we`:

| Deployment | Model | Version | Capacity |
|------------|-------|---------|----------|
| `gpt-5.4-mini` | `gpt-5.4-mini` | `2026-03-17` | 500 |
| `gpt-5-pro-reasoning` | `gpt-5-pro` | `2025-10-06` | 100 |
| `DeepSeek-V4-Flash` | `DeepSeek-V4-Flash` | `2026-04-23` | 20 |
| `text-embedding-3-small` | `text-embedding-3-small` | `1` | 10 |

The previous Sweden Central account `mstech-demo-resource` is retained temporarily
for rollback with public network access disabled. A rollback requires repointing
the Foundry private endpoint. Do not delete the account until the West Europe path
has been observed during the demo workload.

## Identity and Networking

- The App Service system-assigned managed identity has `Cognitive Services OpenAI User`,
  `Cognitive Services User`, and `Foundry User` on `ms-tech-demo-resource-we`.
- The private endpoint `pe-mstech-demo-foundry` targets `ms-tech-demo-resource-we`.
- Foundry private DNS zones remain linked to `vnet-mstech-demo`.
- Public network access is disabled on `ms-tech-demo-resource-we`.

## Azure AI Search Indexer

The RAG indexer `rag-1779444354799-indexer` previously ran every day on the paid
Search service. That service was removed for cost control and replaced by
free-tier Search service `mstech-demo-search-free`.

Free-tier Search does not support the previous private endpoint/shared private
link indexer path, so indexing is now manual. Create or refresh the lexical index
by pushing selected `.md` and `.txt` files directly:

```bash
export AZURE_SEARCH_ENDPOINT=https://mstech-demo-search-free.search.windows.net
export AZURE_SEARCH_KEY=<search-admin-key>
export AZURE_SEARCH_INDEX=rag-1779444354799
python3 scripts/manual_index_search.py --delete-index --create-index --docs-dir ./docs-to-index
```

If automated indexing every 10 days is required later, use a secure external
trigger such as Azure Functions timer trigger, Logic Apps, or GitHub Actions to
run the same script.

## Managed Model Router Experiment

The managed `model-router` catalog entry is available in Sweden Central but is not
currently published in West Europe. The separate Sweden Central experiment uses:

| Resource | Name | Region |
|----------|------|--------|
| Foundry AIServices account | `ms-tech-demo1-router-se` | Sweden Central |
| Foundry project | `ms-tech-demo1-router` | Sweden Central |
| Model deployment | `model-router` | Sweden Central |

The `model-router` deployment uses version `2025-11-18`, `GlobalStandard` SKU,
capacity `10`, and the `Microsoft.DefaultV2` policy. The private endpoint
`pe-ms-tech-demo1-router-se` targets the experiment account and public network
access is disabled.

A direct authenticated Chat Completions request succeeded and routed a short prompt
to `gpt-4o-mini`. The production application uses a hybrid policy: deterministic
rules retain translation, explicit Pro, RAG, and realtime handling, while general
interactive prompts are sent to the managed router with a West Europe
`gpt-5.4-mini` fallback.

The earlier deployment attempts against the old Sweden Central rollback account
`mstech-demo-resource` failed policy validation. Creating a clean experiment account
resolved that account-specific issue.

## Validation

The migrated private path was verified after public access was disabled:

- Backend health endpoint returned `status: ok`.
- `gpt-5.4-mini` handled a short interactive request.
- `DeepSeek-V4-Flash` handled a summary request.
- RAG retrieved indexed sources and generated an answer using `gpt-5.4-mini`.

`gpt-5-pro-reasoning` remains available but can exceed the demo App Service request
window. Keep it restricted to explicit pro requests.
