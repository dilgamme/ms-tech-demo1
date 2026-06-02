# MS Tech Demo - Multi-Model AI Routing on Azure

Production-ready demo showcasing enterprise multi-model AI architecture with intelligent routing, cost optimization, and Azure deployment.

## 🎯 Features

- **Hybrid Multi-Model Routing**: Deterministic special-case routes plus the managed Foundry model-router for general interactive prompts
- **Intent Classification**: GPT-5-mini classifier handles prompts that do not match deterministic routing rules
- **React Frontend**: Modern chat UI with localStorage persistence
- **FastAPI Backend**: High-performance Python backend with CORS support
- **Azure Deployment**: Static Web App + App Service with CI/CD pipelines
- **Future-Ready**: Architecture designed for microphone, vision, memory, and RAG integrations

## 🏗️ Architecture

```
┌─────────────────────┐
│   React UI (Vite)   │
│ Static Web App      │
└──────────┬──────────┘
           │ HTTPS
           ▼
┌─────────────────────┐
│  FastAPI Backend    │
│  App Service        │
│  Python 3.12        │
└──────────┬──────────┘
           │ Azure OpenAI
           ▼
┌─────────────────────┐
│ Azure AI Foundry    │
├─────────────────────┤
│ • DeepSeek-V4       │ (translation/summary)
│ • GPT-5-mini        │ (realtime/fallback)
│ • GPT-5-Pro         │ (explicit deep reasoning)
│ • model-router      │ (general interactive prompts)
└─────────────────────┘
```

## 📋 Prerequisites

- Azure subscription with resource group `rg-ms-tech-demo1`
- Azure AI Foundry models deployed:
  - `DeepSeek-V4-Flash`
  - `gpt-5.4-mini`
  - `gpt-5-pro-reasoning`
  - `model-router`
- Azure OpenAI endpoint and either managed identity access or an API key for local development
- GitHub account
- Node.js 18+ and Python 3.12+

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/dilgamme/ms-tech-demo.git
cd ms-tech-demo

# Frontend setup
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your backend URL

# Backend setup
cd ../backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

### 2. Run Locally

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
# API available at http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# UI available at http://localhost:3000 or http://localhost:5173
```

### 3. Deploy to Azure

**Prerequisites:**
- Azure CLI installed and authenticated
- Static Web App created: `mstech-demo-ui`
- App Service created: `mstech-demo-router-api`

**Deploy Infrastructure (optional, if not created):**
```bash
az deployment group create \
  --resource-group rg-ms-tech-demo1 \
  --template-file infra/main.bicep
```

**Configure GitHub Secrets** (in your GitHub repo):
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint
- `VITE_API_URL`: Your backend App Service URL
- `AZURE_STATIC_WEB_APPS_API_TOKEN_ORANGE_HILL_0DB554803`: Created by Azure Static Web Apps GitHub integration
- `AzureAppService_PublishProfile_44751b3e1cc1412289a5ed70da06ca2f`: Created by Azure App Service GitHub Actions integration

**Push to Deploy:**
```bash
git push origin main
# GitHub Actions automatically deploys frontend and backend
```

## 📝 API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok", "service": "mstech-router"}
```

### Route Prompt
```
POST /api/routePrompt

Request:
{
  "prompt": "What is machine learning?",
  "messages": []
}

Response:
{
  "modelUsed": "gpt-4o-mini-2024-07-18",
  "reason": "Rule match: short/simple query → Foundry model-router | Foundry model-router selected gpt-4o-mini-2024-07-18",
  "answer": "Machine learning is..."
}
```

## 🧠 Routing Logic

| Task Type | Model | Reason |
|-----------|-------|--------|
| Translation | DeepSeek-V4-Flash | Cost-optimized, fast |
| Summaries | DeepSeek-V4-Flash | No deep reasoning needed |
| Simple questions | Foundry model-router | Managed model selection |
| Live data | GPT-5-mini + retrieved context | Freshness-aware response |
| Planning, analysis, math, and code | Foundry model-router | Managed model selection |
| Explicit deep/pro request | GPT-5-Pro | High-effort reasoning with longer latency |
| Ambiguous or low-confidence classification | Foundry model-router | Managed model selection with GPT-5-mini fallback |

## 🔐 Security

- ✅ No API keys in code
- ✅ Environment variables for credentials
- ✅ GitHub Secrets for deployment
- ✅ CORS configured for Static Web App
- ✅ HTTPS enforced
- ✅ Managed Identity for Azure OpenAI and Azure AI Search in production

## 🛠️ Environment Variables

**Backend (.env):**
```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
USE_MANAGED_IDENTITY=false
DEEPSEEK_MODEL=DeepSeek-V4-Flash
ROUTER_MODEL=gpt-5.4-mini
REASONING_MODEL=gpt-5-pro-reasoning
FOUNDRY_ROUTER_ENDPOINT=https://your-router-resource.cognitiveservices.azure.com/
FOUNDRY_ROUTER_MODEL=model-router
AUTH_CLIENT_ID=ead1d8be-064b-4e75-af9b-66ab0c28a954
AUTH_REQUIRED=false
FOUNDRY_PROJECT_ENDPOINT=https://your-foundry-resource.services.ai.azure.com/api/projects/your-project
FOUNDRY_CONVERSATIONS_ENABLED=true
MEMORY_STORE_ENABLED=false
MEMORY_STORE_NAME=ms-tech-demo-memory
MEMORY_STORE_CHAT_MODEL=gpt-5.4-mini
MEMORY_STORE_EMBEDDING_MODEL=text-embedding-3-small
FRONTEND_URL=https://orange-hill-0db554803.7.azurestaticapps.net
```

`FOUNDRY_PROJECT_ENDPOINT` enables the preview Foundry Memory Store integration. Leave it unset until the target project returns persisted memories rather than preview placeholder content.

**Frontend (.env.local):**
```
VITE_API_URL=https://mstech-demo-router-api.azurewebsites.net
VITE_ENTRA_CLIENT_ID=ead1d8be-064b-4e75-af9b-66ab0c28a954
VITE_ENTRA_API_SCOPE=api://ead1d8be-064b-4e75-af9b-66ab0c28a954/access_as_user
```

## 🗂️ Project Structure

```
ms-tech-demo/
├── frontend/                      # React + Vite UI
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── services/             # API service
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── vite.config.js
│   └── package.json
├── backend/                       # Python FastAPI
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── router/              # API routes
│   │   ├── router_logic.py      # Routing logic
│   │   ├── models.py            # Pydantic models
│   │   └── config.py            # Configuration
│   ├── requirements.txt
│   └── .env.example
├── infra/                         # Infrastructure
│   └── main.bicep               # Azure resources
├── .github/workflows/            # CI/CD pipelines
│   ├── deploy-frontend.yml
│   └── deploy-backend.yml
└── README.md
```

## 🔄 CI/CD Workflows

### Frontend Deployment
- Trigger: Push to `main` with changes in `frontend/`
- Steps:
  1. Setup Node.js
  2. Install dependencies
  3. Build with Vite
  4. Deploy to Static Web App

### Backend Deployment
- Trigger: Push to `main` with changes in `backend/`
- Steps:
  1. Setup Python 3.12
  2. Install requirements
  3. Run tests
  4. Deploy to App Service
  5. Set environment variables

## 🚀 Future Enhancements

- [ ] Microphone input (Web Audio API)
- [ ] Image upload with vision models
- [ ] Persistent chat memory (CosmosDB)
- [ ] RAG with Azure Search
- [ ] Semantic Kernel integration
- [ ] Advanced model telemetry
- [ ] Response streaming

## 📞 Support

For issues or questions, check:
- Azure OpenAI documentation: https://learn.microsoft.com/azure/ai-services/openai/
- FastAPI docs: https://fastapi.tiangolo.com/
- React docs: https://react.dev/

## 📄 License

MIT

---

**Demo by:** MS Tech Summit | **Models:** Azure AI Foundry | **Infrastructure:** Azure
