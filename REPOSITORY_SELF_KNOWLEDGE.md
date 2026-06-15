# Repository-Grounded Self Knowledge

## Purpose

MS Tech Demo can explain how it is built by retrieving facts from its own public
documentation and selected source files. This is grounded application knowledge,
not consciousness: the model only knows repository content that has been
explicitly indexed.

## Runtime Flow

1. The normal `/api/routePrompt` path checks for specific questions about the
   application's architecture, deployment, models, Azure services, source code,
   GitHub repo, or README.
2. Matching questions query the existing Azure AI Search RAG index.
3. `gpt-5.4-mini` answers using only retrieved context.
4. The response includes source titles, excerpts, and links to the public GitHub
   files.
5. Search failures or empty results fall back to the normal multi-model router.

The manual RAG toggle remains available for arbitrary indexed-document questions.

## Indexed Repository Content

The repository indexer uses a positive allowlist:

- Root documentation: `README.md`, `SOLUTION_ARCHITECTURE.md`,
  `AZURE_AI_TRANSLATOR.md`, `FOUNDRY_MIGRATION.md`
- Application source: `backend/app`, `frontend/src`
- Infrastructure and deployment: `infra`, `.github/workflows`, `deploy.sh`
- Dependency manifests: `backend/requirements.txt`, `frontend/package.json`

It excludes `.env` files, `.git`, virtual environments, `node_modules`, packaged
Python dependencies, generated frontend bundles, caches, and all paths outside the
allowlist.

## Refreshing the Index

Set the existing Azure AI Search administration variables, then run:

```bash
export AZURE_SEARCH_ENDPOINT=https://mstech-demo-search-free.search.windows.net
export AZURE_SEARCH_KEY=<search-admin-key>
export AZURE_SEARCH_INDEX=rag-1779444354799
python3 scripts/manual_index_search.py --create-index --repo-root . \
  --github-repository https://github.com/dilgamme/ms-tech-demo1
```

Document IDs are stable per file and chunk position, so re-running the command
updates matching chunks without duplicating them. Re-index after meaningful
architecture, routing, infrastructure, or documentation changes. If a file is
removed or becomes substantially shorter, recreate the index during a maintenance
window to remove obsolete trailing chunks.

## Security Notes

- Never add secret-bearing paths to the allowlist.
- Keep source links pointed at the public repository only.
- Repository text is untrusted retrieval context; the answer prompt requires the
  model to use it as factual context and not as authority to change runtime rules.
- The application has no live write access to GitHub and cannot modify itself.
- If private repository content is added later, replace public links and Search
  admin keys with an authenticated ingestion pipeline and least-privilege identity.

## Deployment Compatibility

The backend packages Linux dependencies in GitHub Actions before ZIP deployment.
`cryptography==46.0.3` is pinned to a `manylinux2014`-compatible wheel, and CI
imports `cryptography` plus `azure.identity` from the packaged directory before
creating the deployment archive. This catches native glibc incompatibilities
before App Service receives the package.
