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
    FOUNDRY_CONVERSATIONS_ENABLED: bool = False
    MEMORY_STORE_NAME: str = "ms-tech-demo-memory"
    MEMORY_STORE_ENABLED: bool = False
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
    VOICE_LIVE_MODEL: str = "gpt-4o"
    VOICE_LIVE_VOICE: str = "en-US-Ava:DragonHDLatestNeural"
    VOICE_LIVE_API_VERSION: str = "2025-10-01"
    VOICE_LIVE_TOKEN_SCOPE: Optional[str] = None

    # Azure AI Translator
    TRANSLATOR_ENABLED: bool = False
    TRANSLATOR_ENDPOINT: Optional[str] = None
    TRANSLATOR_KEY: Optional[str] = None
    TRANSLATOR_REGION: Optional[str] = None
    TRANSLATOR_API_VERSION: str = "3.0"
    TRANSLATOR_TIMEOUT_SECONDS: int = 15

    # Azure AI Search / RAG
    AZURE_SEARCH_ENDPOINT: Optional[str] = None
    AZURE_SEARCH_KEY: Optional[str] = None
    AZURE_SEARCH_USE_MANAGED_IDENTITY: Optional[bool] = None
    AZURE_SEARCH_VECTOR_ENABLED: bool = True
    AZURE_SEARCH_INDEX: str = "rag-1779444354799"
    RAG_TOP_K: int = 5
    RAG_MODEL: Optional[str] = None

    # Image generation and understanding
    IMAGE_OPENAI_ENDPOINT: Optional[str] = None
    IMAGE_OPENAI_KEY: Optional[str] = None
    IMAGE_GENERATION_MODEL: str = "gpt-image-1-mini"
    IMAGE_UNDERSTANDING_MODEL: Optional[str] = None
    IMAGE_GENERATION_SIZE: str = "1024x1024"
    IMAGE_GENERATION_QUALITY: str = "low"
    
    # API settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
