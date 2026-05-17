# GitHub Secrets Configuration

Add these secrets to your GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

## Azure OpenAI Runtime Settings

Set the Azure OpenAI endpoint and rotated key directly on App Service. They are not required as GitHub Actions secrets for the current workflow.

## App Service Deployment

Get publish profile:
```bash
az webapp deployment list-publishing-credentials \
  --resource-group rg-ms-tech-demo1 \
  --name mstech-demo-router-api \
  --query publishingCredentials -o json > publish-profile.json
```

```
Name: AZURE_APP_SERVICE_PUBLISH_PROFILE
Value: (contents of publish-profile.json)
```

## Frontend Deployment

For Static Web App, get the API token:
```bash
STATIC_APP_RESOURCE_ID="/subscriptions/YOUR_SUB_ID/resourceGroups/rg-ms-tech-demo1/providers/Microsoft.Web/staticSites/mstech-demo-ui"

az rest --method post \
  --uri "${STATIC_APP_RESOURCE_ID}/listSecrets?api-version=2021-01-15" \
  --query properties.apiToken -o tsv
```

```
Name: AZURE_STATIC_WEB_APPS_API_TOKEN
Value: (token from above)
```

## Frontend API URL

```
Name: VITE_API_URL
Value: https://mstech-demo-router-api.azurewebsites.net
```

## All Secrets Summary

| Secret Name | Value |
|---|---|
| AZURE_APP_SERVICE_PUBLISH_PROFILE | {publish profile JSON} |
| AZURE_STATIC_WEB_APPS_API_TOKEN | {static app token} |
| VITE_API_URL | https://mstech-demo-router-api.azurewebsites.net |

---

Once secrets are added, push to `main` branch and GitHub Actions will auto-deploy.
