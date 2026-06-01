# Azure AI Foundry Migration to West Europe

This guide documents the migration of Azure AI Foundry from Sweden Central to West Europe to reduce latency and align with other project resources.

## 📋 Pre-Migration Checklist

- [x] Infrastructure code updated (main.bicep now uses `westeurope`)
- [x] Private network already configured for West Europe
- [ ] Azure AI Foundry project created in West Europe region
- [ ] Models deployed in new Foundry project:
  - [ ] `DeepSeek-V4-Flash`
  - [ ] `gpt-5.4-mini`
  - [ ] `gpt-5-pro-reasoning`
- [ ] API endpoints updated in backend configuration
- [ ] Testing completed

## 🔧 Steps to Complete Migration

### Step 1: Create Azure AI Foundry Project in West Europe

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure AI Foundry** → **Projects**
3. Create a new project in **West Europe** region:
   - **Project Name**: `ms-tech-demo` (or preferred name)
   - **Resource Group**: `rg-ms-tech-demo1`
   - **Region**: `West Europe`
   - **Hub**: Create new or use existing
   - **Storage Account**: Use `mstechdemoragstorage` (already in West Europe)
   - **Key Vault**: Create new in West Europe

### Step 2: Deploy Models in New Foundry Project

Once the Foundry project is created:

1. **Deploy DeepSeek-V4-Flash**
   - In your Foundry project → **Models + Endpoints**
   - Click **Deploy** → **Model**
   - Select **DeepSeek-V4-Flash**
   - Choose **Deployment name**: `DeepSeek-V4-Flash`
   - Configure quota/resources as needed
   - Deploy

2. **Deploy GPT-5-mini**
   - Click **Deploy** → **Model**
   - Select **gpt-5.4-mini**
   - Deployment name: `gpt-5-mini`
   - Deploy

3. **Deploy GPT-5-Pro (Reasoning)**
   - Click **Deploy** → **Model**
   - Select **gpt-5-pro-reasoning` or similar
   - Deployment name: `gpt-5-pro-reasoning`
   - Deploy

### Step 3: Update Backend Configuration

Once models are deployed, update your backend to use the new West Europe Foundry endpoint:

1. Get the **API Endpoint** from your Foundry project:
   - Project Settings → API Endpoints
   - Copy the endpoint URL

2. Update your App Service configuration:
   ```bash
   az webapp config appsettings set \
     --resource-group rg-ms-tech-demo1 \
     --name mstech-demo-router-api \
     --settings FOUNDRY_ENDPOINT="<new-west-europe-endpoint>"
   ```

3. Or update via Azure Portal:
   - App Service → Configuration → Application Settings
   - Update `FOUNDRY_ENDPOINT` to new West Europe value

### Step 4: Deploy Infrastructure

Run the deployment:

```bash
az deployment group create \
  --resource-group rg-ms-tech-demo1 \
  --template-file infra/main.bicep \
  --parameters location=westeurope
```

Or use Azure Developer CLI:

```bash
azd up --environment prod
```

### Step 5: Test and Verify

1. **Test Model Routing**
   ```bash
   curl -X POST https://mstech-demo-router-api.azurewebsites.net/api/chat \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "Hello"}]}'
   ```

2. **Verify Latency**
   - Check response times from your frontend
   - Monitor Application Insights metrics
   - Confirm reduced latency vs previous region

3. **Run End-to-End Tests**
   ```bash
   npm test --workspace=frontend
   pytest backend/tests
   ```

### Step 6: Cleanup (Optional)

Once migration is confirmed successful:

1. Delete old Sweden Central Foundry project (if applicable)
2. Remove any unused resources from previous region
3. Update documentation

## 📊 Regional Consistency

After migration, all resources will be in **West Europe**:

| Resource | Region | Status |
|----------|--------|--------|
| App Service | West Europe | ✅ |
| Storage Account (RAG) | West Europe | ✅ |
| Azure AI Search | West Europe | ✅ |
| Virtual Network | West Europe | ✅ |
| Private Endpoints | West Europe | ✅ |
| **Azure AI Foundry** | **West Europe** | ⏳ *In Progress* |

## 🔐 Security Notes

- Private endpoints are configured in `infra/private-network.bicep`
- Foundry account will be accessible via private endpoint: `pe-mstech-demo-foundry`
- Managed identity access is preferred over API keys
- All resources remain within Azure private network

## 📝 Configuration Files Updated

- `infra/main.bicep`: Changed default location from `eastus` to `westeurope`
- `.azure/infrastructure-plan.json`: Already configured for West Europe
- `infra/private-network.bicep`: Already configured for West Europe

## 🚨 Troubleshooting

### Models not deploying?
- Ensure you have sufficient quota in West Europe region
- Check Foundry project has correct permissions
- Verify model availability in target region

### High latency still?
- Check Application Insights → Performance metrics
- Verify frontend is also in West Europe (Static Web App location)
- Review network path in private endpoints

### Connection failures?
- Verify Foundry private endpoint is properly configured
- Check VNet integration on App Service
- Review NSG and firewall rules

## 📞 Support

For issues during migration, check:
- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- Application Insights logs
- App Service diagnostic logs
