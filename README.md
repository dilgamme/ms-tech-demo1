# MS Tech Demo - Multi-Model AI Routing on Azure

Production-ready demo showcasing enterprise multi-model AI architecture with intelligent routing, cost optimization, and Azure deployment.

## 🎯 Features

- **Hybrid Multi-Model Routing**: Broad deterministic rules plus GPT-5-mini classification for unmatched prompts
- **Azure AI Translator**: Deterministic text translation with language detection and DeepSeek fallback
- **Intent Classification**: GPT-5-mini classifier handles prompts that do not match deterministic routing rules
- **React Frontend**: Modern chat UI with Microsoft Foundry conversation history
- **FastAPI Backend**: High-performance Python backend with CORS support
- **Azure Deployment**: Static Web App + App Service with CI/CD pipelines
- **Voice Live and RAG**: Microphone conversations and Azure AI Search grounding
- **Repository-Grounded Self Knowledge**: Architecture questions automatically use an allowlisted GitHub/Markdown RAG source
- **Foundry Web IQ**: Fresh public-web grounding with cited pages and an existing realtime-provider fallback; see [`WEB_IQ.md`](WEB_IQ.md)
- **Image Attachment Composer**: Stage an uploaded image, add an instruction, preview or remove it, and then send both together; see [`IMAGE_UPLOAD.md`](IMAGE_UPLOAD.md)
- **Microsoft Account Sign-In**: Optional personal Microsoft and organizational Entra login
- **Living Architecture Documentation**: Full deployed flow documented in [`SOLUTION_ARCHITECTURE.md`](SOLUTION_ARCHITECTURE.md)

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
           │ Managed identity + public Azure HTTPS endpoints
           ▼
┌─────────────────────┐
│ Azure AI Foundry    │
├─────────────────────┤
│ • Azure Translator  │ (translation)
│ • DeepSeek-V4       │ (summary/translation fallback)
│ • GPT-5-mini        │ (general answers, classification, realtime)
│ • Web IQ web_search │ (fresh public-web answers)
│ • GPT-5-Pro         │ (explicit deep reasoning)
│ • Conversations API │ (durable chat history)
└─────────────────────┘
```

For the complete deployed architecture, identity model, networking, routing,
conversation persistence, RAG flow, Voice Live flow, settings, and operational
notes, see [`SOLUTION_ARCHITECTURE.md`](SOLUTION_ARCHITECTURE.md).

Questions such as "How are you built?" and "What Azure services do you use?"
are automatically grounded in the indexed repository documentation and selected
source files. Answers include links to the corresponding public GitHub files.

## 📋 Prerequisites

- Azure subscription with resource group `rg-ms-tech-demo1`
- Azure AI Foundry models deployed:
  - `DeepSeek-V4-Flash`
  - `gpt-5.4-mini`
  - `gpt-5-pro-reasoning`
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
  "messages": [],
  "fastMode": true
}

Response:
{
  "modelUsed": "gpt-5.4-mini",
  "reason": "Rule match: general knowledge → GPT-5-mini",
  "answer": "Machine learning is..."
}
```

`fastMode` is retained for API compatibility and defaults to `true`. The web app
always uses optimized generation instructions and output budgets without exposing
a mode switch.

## 🧠 Routing Logic

| Task Type | Model | Reason |
|-----------|-------|--------|
| Translation | DeepSeek-V4-Flash | Cost-optimized, fast |
| Summaries | DeepSeek-V4-Flash | No deep reasoning needed |
| Simple questions, writing, extraction, and conversation | GPT-5-mini | Fast general-purpose route |
| Live data | GPT-5-mini + retrieved context | Freshness-aware response |
| Planning, analysis, math, and code | GPT-5-mini | Deterministic complexity rules |
| Explicit deep/pro request | GPT-5-Pro | High-effort reasoning with longer latency |
| Ambiguous or low-confidence classification | GPT-5-mini | GPT-5-mini classifier and safe default |

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
REASONING_ENDPOINT=https://your-responses-capable-resource.cognitiveservices.azure.com/
WEB_IQ_ENABLED=false
WEB_IQ_ENDPOINT=https://your-responses-api-region.cognitiveservices.azure.com/
WEB_IQ_MODEL=gpt-5.4-mini
WEB_IQ_SEARCH_CONTEXT_SIZE=medium
AUTH_CLIENT_ID=ee9c8967-93a4-49a2-ace1-142ad566f27d
AUTH_JWKS_URL=https://dlgmb2c.b2clogin.com/dlgmb2c.onmicrosoft.com/discovery/v2.0/keys?p=B2C_1_SUSI
AUTH_ISSUER=https://dlgmb2c.b2clogin.com/e7487735-3dc4-4534-9748-f0d4e91c44ca/v2.0/
AUTH_POLICY=B2C_1_SUSI
AUTH_TENANT_ID=e7487735-3dc4-4534-9748-f0d4e91c44ca
AUTH_REQUIRED=false
FOUNDRY_PROJECT_ENDPOINT=https://your-foundry-resource.services.ai.azure.com/api/projects/your-project
FOUNDRY_CONVERSATIONS_ENABLED=true
MEMORY_STORE_ENABLED=false
MEMORY_STORE_NAME=ms-tech-demo-memory
MEMORY_STORE_CHAT_MODEL=gpt-5.4-mini
MEMORY_STORE_EMBEDDING_MODEL=text-embedding-3-small
VOICE_LIVE_ENDPOINT=https://your-foundry-resource.services.ai.azure.com/
VOICE_LIVE_MODEL=gpt-4o
VOICE_LIVE_API_VERSION=2025-10-01
TRANSLATOR_ENABLED=true
TRANSLATOR_ENDPOINT=https://your-foundry-resource.cognitiveservices.azure.com/
TRANSLATOR_REGION=westeurope
TRANSLATOR_API_VERSION=3.0
IMAGE_OPENAI_ENDPOINT=https://your-image-resource.cognitiveservices.azure.com/
IMAGE_GENERATION_MODEL=gpt-image-1-mini
FRONTEND_URL=https://orange-hill-0db554803.7.azurestaticapps.net
```

`FOUNDRY_PROJECT_ENDPOINT` enables project APIs such as Foundry Conversations.
Use `MEMORY_STORE_ENABLED=false` until the target project returns persisted memories
rather than preview placeholder content.
`VOICE_LIVE_ENDPOINT` should use the Foundry resource host for Voice Live sessions.
`TRANSLATOR_ENDPOINT` uses the Azure AI Services custom domain. During the
temporary cost-saving period, production traffic reaches it over the public Azure
HTTPS endpoint using managed identity or the configured service credential.
`WEB_IQ_ENDPOINT` must be in an Azure region that supports the Responses API.
See [`WEB_IQ.md`](WEB_IQ.md) for the current activation status, privacy boundary,
cost behavior, and citation flow.

**Frontend (.env.local):**
```
VITE_API_URL=https://mstech-demo-router-api.azurewebsites.net
VITE_ENTRA_CLIENT_ID=ee9c8967-93a4-49a2-ace1-142ad566f27d
VITE_ENTRA_AUTHORITY=https://dlgmb2c.b2clogin.com/dlgmb2c.onmicrosoft.com/B2C_1_SUSI
VITE_ENTRA_KNOWN_AUTHORITY=dlgmb2c.b2clogin.com
VITE_ENTRA_API_SCOPE=https://dlgmb2c.onmicrosoft.com/ee9c8967-93a4-49a2-ace1-142ad566f27d/access_as_user
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
│   │   ├── web_iq_service.py    # Web search and citation extraction
│   │   ├── models.py            # Pydantic models
│   │   └── config.py            # Configuration
│   ├── requirements.txt
│   └── .env.example
├── infra/                         # Infrastructure
│   └── main.bicep               # Azure resources
├── .github/workflows/            # CI/CD pipelines
│   ├── deploy-frontend.yml
│   └── deploy-backend.yml
├── WEB_IQ.md                     # Web IQ implementation and operations
├── IMAGE_UPLOAD.md                # Image attachment composer behavior
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

- [x] Microphone input (Web Audio API)
- [ ] Image upload with vision models
- [x] Persistent server-side chat conversations (Foundry Conversations API)
- [x] RAG with Azure Search
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
