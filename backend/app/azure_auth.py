from functools import lru_cache

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from app.config import settings

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"
SEARCH_SCOPE = "https://search.azure.com/.default"
FOUNDRY_SCOPE = "https://ai.azure.com/.default"


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


def get_cognitive_services_auth_headers(api_key: str | None = None) -> dict[str, str]:
    if settings.USE_MANAGED_IDENTITY and not api_key:
        token = get_azure_credential().get_token(COGNITIVE_SERVICES_SCOPE)
        return {"Authorization": f"Bearer {token.token}"}
    key = api_key or settings.AZURE_OPENAI_KEY
    if not key:
        raise ValueError("An Azure OpenAI key is required when managed identity is disabled")
    return {"api-key": key}


def get_search_auth_headers() -> dict[str, str]:
    use_managed_identity = (
        settings.AZURE_SEARCH_USE_MANAGED_IDENTITY
        if settings.AZURE_SEARCH_USE_MANAGED_IDENTITY is not None
        else settings.USE_MANAGED_IDENTITY and not settings.AZURE_SEARCH_KEY
    )
    if use_managed_identity:
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


def get_foundry_auth_headers() -> dict[str, str]:
    token = get_azure_credential().get_token(FOUNDRY_SCOPE)
    return {"Authorization": f"Bearer {token.token}"}
