from functools import lru_cache

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from app.config import settings

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"
SEARCH_SCOPE = "https://search.azure.com/.default"


@lru_cache
def get_azure_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()


def get_openai_api_key():
    if settings.USE_MANAGED_IDENTITY:
        return get_bearer_token_provider(
            get_azure_credential(),
            COGNITIVE_SERVICES_SCOPE
        )
    if not settings.AZURE_OPENAI_KEY:
        raise ValueError("AZURE_OPENAI_KEY is required when managed identity is disabled")
    return settings.AZURE_OPENAI_KEY


def get_search_auth_headers() -> dict[str, str]:
    if settings.USE_MANAGED_IDENTITY:
        token = get_azure_credential().get_token(SEARCH_SCOPE)
        return {"Authorization": f"Bearer {token.token}"}
    if not settings.AZURE_SEARCH_KEY:
        raise ValueError("AZURE_SEARCH_KEY is required when managed identity is disabled")
    return {"api-key": settings.AZURE_SEARCH_KEY}


def get_voice_live_auth_headers() -> dict[str, str]:
    if settings.USE_MANAGED_IDENTITY:
        token = get_azure_credential().get_token(COGNITIVE_SERVICES_SCOPE)
        return {"Authorization": f"Bearer {token.token}"}
    if not settings.VOICE_LIVE_KEY:
        raise ValueError("VOICE_LIVE_KEY is required when managed identity is disabled")
    return {"api-key": settings.VOICE_LIVE_KEY}
