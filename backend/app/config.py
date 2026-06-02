from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_KEY: Optional[str] = None
    USE_MANAGED_IDENTITY: bool = False
    
    # Model names (deployment names in Azure)
    DEEPSEEK_MODEL: str = "DeepSeek-V4-Flash"
    ROUTER_MODEL: str = "gpt-5.4-mini"
    REASONING_MODEL: str = "gpt-5-pro-reasoning"
    FOUNDRY_ROUTER_ENDPOINT: Optional[str] = None
    FOUNDRY_ROUTER_MODEL: str = "model-router"

    # Microsoft Foundry Memory Store API
    FOUNDRY_PROJECT_ENDPOINT: Optional[str] = None
    MEMORY_STORE_NAME: str = "ms-tech-demo-memory"
    MEMORY_STORE_CHAT_MODEL: str = "gpt-5.4-mini"
    MEMORY_STORE_EMBEDDING_MODEL: str = "text-embedding-3-small"
    MEMORY_STORE_API_VERSION: str = "2025-11-15-preview"
    MEMORY_STORE_MAX_MEMORIES: int = 5

    # Microsoft identity platform authentication
    AUTH_CLIENT_ID: Optional[str] = None
    AUTH_REQUIRED: bool = False
    
    # Frontend URL for CORS
    FRONTEND_URL: Optional[str] = None

    # Azure Voice Live
    VOICE_LIVE_ENDPOINT: Optional[str] = None
    VOICE_LIVE_KEY: Optional[str] = None
    VOICE_LIVE_MODEL: str = "gpt-realtime"
    VOICE_LIVE_VOICE: str = "en-US-Ava:DragonHDLatestNeural"
    VOICE_LIVE_API_VERSION: str = "2025-10-01"

    # Azure AI Search / RAG
    AZURE_SEARCH_ENDPOINT: Optional[str] = None
    AZURE_SEARCH_KEY: Optional[str] = None
    AZURE_SEARCH_INDEX: str = "rag-1779444354799"
    RAG_TOP_K: int = 5
    RAG_MODEL: Optional[str] = None
    
    # API settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
