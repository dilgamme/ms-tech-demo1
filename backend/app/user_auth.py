import re
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException

from app.config import settings

COMMON_JWKS_URL = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
ISSUER_PATTERN = re.compile(
    r"^https://login\.microsoftonline\.com/"
    r"(?P<tenant_id>[0-9a-fA-F-]{36})/v2\.0$"
)


@dataclass(frozen=True)
class UserIdentity:
    tenant_id: str
    subject: str
    display_name: str | None = None

    @property
    def memory_scope(self) -> str:
        return f"entra:{self.tenant_id}:{self.subject}"


@lru_cache
def _get_jwk_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(COMMON_JWKS_URL, cache_keys=True, lifespan=3600)


def get_optional_user_identity(
    authorization: str | None = Header(default=None),
) -> UserIdentity | None:
    if not authorization:
        if settings.AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="Sign in with Microsoft is required")
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    if not settings.AUTH_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Microsoft sign-in is not configured")

    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.AUTH_CLIENT_ID,
            options={"verify_iss": False},
        )
        tenant_id = str(claims.get("tid", ""))
        issuer = str(claims.get("iss", ""))
        issuer_match = ISSUER_PATTERN.fullmatch(issuer)
        if not issuer_match or issuer_match.group("tenant_id").lower() != tenant_id.lower():
            raise ValueError("Token issuer does not match tenant")

        scopes = set(str(claims.get("scp", "")).split())
        if "access_as_user" not in scopes:
            raise ValueError("Token is missing the access_as_user scope")

        subject = str(claims.get("sub", ""))
        if not subject:
            raise ValueError("Token is missing the subject claim")

        return UserIdentity(
            tenant_id=tenant_id,
            subject=subject,
            display_name=claims.get("name") or claims.get("preferred_username"),
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Microsoft access token: {exc}") from exc
