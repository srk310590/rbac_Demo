"""
Token verification for requests coming from the Vite frontend.

The frontend never talks to this backend without a bearer token issued by
Keycloak. This module verifies that token's signature, issuer, audience and
expiry using Keycloak's published JWKS (JSON Web Key Set), then exposes the
decoded claims (including realm roles) to route handlers via FastAPI's
dependency injection.
"""
import time

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError

from .config import JWKS_URL, KEYCLOAK_AUDIENCE, KEYCLOAK_ISSUER

security = HTTPBearer()

_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600


async def _get_jwks() -> dict:
    """Fetch Keycloak's signing keys, cached for an hour."""
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache is None or (time.time() - _jwks_fetched_at) > _JWKS_TTL_SECONDS:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(JWKS_URL)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_fetched_at = time.time()
    return _jwks_cache


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency: validates the Authorization: Bearer <token> header
    against Keycloak and returns the decoded claims. Raises 401 on any
    failure (missing/expired/invalid-signature/wrong-audience token).
    """
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)
        if key is None:
            # Keys may have rotated; force a refresh once and retry.
            global _jwks_cache
            _jwks_cache = None
            jwks = await _get_jwks()
            key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)
        if key is None:
            raise JWTError("Signing key not found")

        payload = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    all_roles = payload.get("realm_access", {}).get("roles", [])
    ignored = {"offline_access", "uma_authorization"}
    roles = [r for r in all_roles if r not in ignored and not r.startswith("default-")]
    return {
        "sub": payload.get("sub"),
        "username": payload.get("preferred_username"),
        "email": payload.get("email"),
        "roles": roles,
        "raw": payload,
    }
