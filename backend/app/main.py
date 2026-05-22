from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.router.api import router as route_prompt_router
from app.router.rag import router as rag_router
from app.router.voice import router as voice_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting app with endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
    yield
    logger.info("Shutting down app")

app = FastAPI(
    title="MS Tech Demo API",
    description="Multi-model AI routing backend",
    version="0.0.1",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default
    "https://orange-hill-0db554803.7.azurestaticapps.net",
    settings.FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(route_prompt_router)
app.include_router(rag_router)
app.include_router(voice_router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mstech-router"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
