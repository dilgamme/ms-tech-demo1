from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException

from app.config import settings

@dataclass(frozen=True)
class UserIdentity:
    tenant_id: str
    subject: str
    display_name: str | None = None

    @property
    def memory_scope(self) -> str:
        return f"entra:{self.tenant_id}:{self.subject}"


@lru_cache
def _get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


def _identity_from_claims(claims: dict) -> UserIdentity:
    issuer = str(claims.get("iss", ""))
    if settings.AUTH_ISSUER and issuer.rstrip("/") != settings.AUTH_ISSUER.rstrip("/"):
        raise ValueError("Token issuer is not trusted")

    policy = str(claims.get("tfp") or claims.get("acr") or "")
    if settings.AUTH_POLICY and policy.lower() != settings.AUTH_POLICY.lower():
        raise ValueError("Token was issued by an unexpected user flow")

    scopes = set(str(claims.get("scp", "")).split())
    if "access_as_user" not in scopes:
        raise ValueError("Token is missing the access_as_user scope")

    subject = str(claims.get("oid") or claims.get("sub") or "")
    if not subject:
        raise ValueError("Token is missing the subject claim")

    emails = claims.get("emails") or []
    display_name = (
        claims.get("name")
        or claims.get("preferred_username")
        or (emails[0] if emails else None)
    )
    tenant_id = settings.AUTH_TENANT_ID or str(claims.get("tid") or "customer")
    return UserIdentity(
        tenant_id=tenant_id,
        subject=subject,
        display_name=display_name,
    )


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
        signing_key = _get_jwk_client(settings.AUTH_JWKS_URL).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.AUTH_CLIENT_ID,
            options={"verify_iss": False},
        )
        return _identity_from_claims(claims)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Microsoft access token: {exc}") from exc
