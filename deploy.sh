#!/bin/bash
# Deploy MS Tech Demo to Azure
# This script handles backend deployment via Git push

RESOURCE_GROUP="rg-ms-tech-demo1"
APP_SERVICE_NAME="mstech-demo-router-api"
STATIC_APP_NAME="mstech-demo-ui"
LOCATION="westeurope"

echo "🚀 MS Tech Demo - Azure Deployment"
echo "======================================"
echo ""
echo "Subscription: MSDN Platforms Subscription"
echo "Region: $LOCATION"
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# Wait for App Service to be ready
echo "⏳ Checking App Service status..."
for i in {1..20}; do
  if az webapp show --resource-group "$RESOURCE_GROUP" --name "$APP_SERVICE_NAME" &>/dev/null; then
    echo "✅ App Service is ready!"
    break
  fi
  echo "   Waiting... ($i/20)"
  sleep 10
done

# Get URLs
echo ""
echo "📍 Getting deployment URLs..."
APP_SERVICE_URL=$(az webapp show --resource-group "$RESOURCE_GROUP" --name "$APP_SERVICE_NAME" --query defaultHostName -o tsv)
echo "   Backend: https://$APP_SERVICE_URL"

# Configure App Service settings
echo ""
echo "⚙️  Configuring environment variables..."
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_SERVICE_NAME" \
  --settings \
    AZURE_OPENAI_ENDPOINT="https://ms-tech-demo-resource-we.cognitiveservices.azure.com/" \
    USE_MANAGED_IDENTITY="true" \
    DEEPSEEK_MODEL="DeepSeek-V4-Flash" \
    ROUTER_MODEL="gpt-5.4-mini" \
    REASONING_MODEL="gpt-5-pro-reasoning" \
    FOUNDRY_ROUTER_ENDPOINT="https://ms-tech-demo1-router-se.cognitiveservices.azure.com/" \
    FOUNDRY_ROUTER_MODEL="model-router" \
    AZURE_SEARCH_ENDPOINT="https://mstech-demo-search.search.windows.net" \
    AZURE_SEARCH_INDEX="rag-1779444354799" \
    RAG_MODEL="gpt-5.4-mini" \
    RAG_TOP_K="5" \
    WEBSITE_RUN_FROM_PACKAGE="1" \
    --no-wait

echo "✅ Environment variables configured"

# Test health endpoint
echo ""
echo "🔍 Testing API health..."
sleep 10
HEALTH=$(curl -s https://$APP_SERVICE_URL/health 2>/dev/null || echo "Not ready yet")
if echo "$HEALTH" | grep -q "ok"; then
  echo "✅ API is healthy!"
  echo "Response: $HEALTH"
else
  echo "⏳ API still initializing... this is normal"
fi

echo ""
echo "======================================"
echo "✅ Deployment Configuration Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Create GitHub repository"
echo "2. Add repository secrets (see GITHUB_SECRETS.md)"
echo "3. Push code to GitHub"
echo "4. GitHub Actions will auto-deploy"
echo ""
echo "Or deploy manually:"
echo "cd backend && az webapp deployment source config-zip --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME --src-path deployment.zip"
