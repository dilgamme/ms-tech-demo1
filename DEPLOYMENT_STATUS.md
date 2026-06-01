# 🚀 MS Tech Demo - Deployment Status

## ✅ What's Done

### Infrastructure (Azure)
- ✅ Resource Group: `rg-ms-tech-demo1` (westeurope)
- ✅ App Service Plan: `plan-mstech-demo` (B1, Linux)
- 🔄 App Service: `mstech-demo-router-api` (Python 3.12) - **Provisioning**
- 📋 Environment Variables: Configured
- 🌍 Region: westeurope

### Code Repository
- ✅ Git repository initialized with all 28 files
- ✅ Main branch ready
- ✅ GitHub Actions workflows configured
- ✅ All source code committed

### Project Files
```
✓ frontend/           - React + Vite chat UI
✓ backend/            - Python FastAPI router
✓ .github/workflows/  - CI/CD pipelines
✓ infra/              - Bicep templates
✓ README.md           - Documentation
✓ GITHUB_SECRETS.md   - Secret configuration
✓ deploy.sh           - Deployment script
```

---

## 🔄 App Service Status

The App Service is currently **provisioning**. This typically takes 2-5 minutes.

**Monitor status:**
```bash
az webapp show --resource-group rg-ms-tech-demo1 --name mstech-demo-router-api --query state -o tsv
```

Expected URL (once running):
```
https://mstech-demo-router-api.azurewebsites.net
```

---

## 📋 Next Steps (To Complete Deployment)

### Step 1: Create GitHub Repository
```bash
# Create new public repo on GitHub: https://github.com/new
# Repository name: ms-tech-demo
# Description: Multi-model AI routing on Azure
```

### Step 2: Push Code to GitHub
```bash
cd /Users/dilgamsharifov/Documents/ms-tech-demo1

# Add GitHub remote
git remote add origin https://github.com/dilgamme/ms-tech-demo.git

# Push to main branch
git push -u origin main
```

### Step 3: Add GitHub Secrets
Go to: **GitHub Repo → Settings → Secrets and variables → Actions**

Add these secrets:

| Secret | Value |
|--------|-------|
| `AZURE_OPENAI_ENDPOINT` | https://ms-tech-demo-resource-we.cognitiveservices.azure.com/ |
| `AZURE_OPENAI_KEY` | Set rotated key directly on App Service |
| `VITE_API_URL` | https://mstech-demo-router-api.azurewebsites.net |
| `AzureAppService_PublishProfile_44751b3e1cc1412289a5ed70da06ca2f` | Created by Azure |
| `AZURE_STATIC_WEB_APPS_API_TOKEN_ORANGE_HILL_0DB554803` | Created by Azure |

**Get App Service Publish Profile:**
```bash
az webapp deployment list-publishing-credentials \
  --resource-group rg-ms-tech-demo1 \
  --name mstech-demo-router-api \
  --query publishingCredentials -o json
```

Azure App Service GitHub Actions integration created the publish profile secret automatically.

### Step 4: Create Static Web App (Frontend)
```bash
az staticwebapp create \
  --name mstech-demo-ui \
  --resource-group rg-ms-tech-demo1 \
  --source https://github.com/dilgamme/ms-tech-demo \
  --location westeurope \
  --branch main \
  --app-location "frontend/dist" \
  --output-location ""
```

Get Static Web App API Token:
```bash
az staticwebapp secrets list \
  --resource-group rg-ms-tech-demo1 \
  --name mstech-demo-ui \
  --query "properties.apiToken" -o tsv
```

Azure Static Web Apps GitHub integration created the Static Web Apps token secret automatically.

### Step 5: Deploy via GitHub Actions
Once secrets are added:
```bash
# Make any change and push
git push origin main
```

GitHub Actions will automatically:
1. Deploy backend to App Service
2. Deploy frontend to Static Web App

---

## 🧪 Testing After Deployment

### Test Backend API
```bash
curl https://mstech-demo-router-api.azurewebsites.net/health
# Expected: {"status":"ok","service":"mstech-router"}
```

### Test Routing Endpoint
```bash
curl -X POST https://mstech-demo-router-api.azurewebsites.net/api/routePrompt \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is machine learning?","messages":[]}'
```

### Visit Frontend
```
https://orange-hill-0db554803.7.azurestaticapps.net
```

---

## 📊 Current Deployment Status

| Component | Status | Region | URL |
|-----------|--------|--------|-----|
| App Service Plan | ✅ Ready | westeurope | - |
| App Service | 🔄 Provisioning | westeurope | https://mstech-demo-router-api.azurewebsites.net |
| Static Web App | ⏳ Not created | westeurope | (Create via Step 4) |
| GitHub Repo | ⏳ Not pushed | - | (Push via Step 2) |

---

## 🔐 Security Notes

⚠️ **Your API key is visible in this file and repository**

**Recommended Actions:**
1. After first deployment test, rotate your Azure OpenAI API key
2. GitHub Secrets are encrypted and safe
3. Never commit `.env` file with real keys
4. Consider using Managed Identity for production

---

## 📞 Troubleshooting

### App Service not ready after 5 minutes
```bash
# Check logs
az webapp log tail --resource-group rg-ms-tech-demo1 --name mstech-demo-router-api
```

### Deployment fails
- Check GitHub Actions logs: Repo → Actions → Recent workflow
- Verify all secrets are set correctly
- Ensure Static Web App has been created

### CORS errors in frontend
- Make sure `VITE_API_URL` secret is set correctly
- Verify backend's CORS config includes Static Web App URL

---

## 📝 Files Reference

- **README.md** - Full project documentation
- **GITHUB_SECRETS.md** - Secret configuration guide
- **DEPLOYMENT.md** - Detailed deployment steps
- **deploy.sh** - Automated deployment script
- **.github/workflows/** - CI/CD pipeline definitions

---

**Status**: Infrastructure provisioning in progress ⏳  
**Subscription**: MSDN Platforms Subscription  
**Resource Group**: rg-ms-tech-demo1  
**Region**: westeurope  
**Created**: 2026-05-17
