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
Name: AzureAppService_PublishProfile_44751b3e1cc1412289a5ed70da06ca2f
Value: Already created by Azure App Service GitHub Actions integration.
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
Name: AZURE_STATIC_WEB_APPS_API_TOKEN_ORANGE_HILL_0DB554803
Value: Already created by Azure Static Web Apps GitHub integration.
```

## Frontend API URL

```
Name: VITE_API_URL
Value: Not required as a repository secret; the generated Static Web Apps workflow sets it as build-time environment.
```

## All Secrets Summary

| Secret Name | Value |
|---|---|
| AzureAppService_PublishProfile_44751b3e1cc1412289a5ed70da06ca2f | Created by Azure |
| AZURE_STATIC_WEB_APPS_API_TOKEN_ORANGE_HILL_0DB554803 | Created by Azure |
| VITE_API_URL | Set in workflow env |

---

Once secrets are added, push to `main` branch and GitHub Actions will auto-deploy.
