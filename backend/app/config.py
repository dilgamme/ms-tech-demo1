from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_KEY: str
    
    # Model names (deployment names in Azure)
    DEEPSEEK_MODEL: str = "DeepSeek-V4-Flash"
    ROUTER_MODEL: str = "gpt-5.4-mini"
    REASONING_MODEL: str = "gpt-5-pro-reasoning"
    
    # Frontend URL for CORS
    FRONTEND_URL: Optional[str] = None
    
    # API settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
