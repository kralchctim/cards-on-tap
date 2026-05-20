"""
auth.py — Clerk JWT verification for the TAK API
"""

import os
import base64
import sqlite3
import httpx
from functools import lru_cache
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

security = HTTPBearer()


def _clerk_jwks_url() -> str:
    """Derive the Clerk JWKS URL from the publishable key."""
    pk = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    if not pk:
        raise RuntimeError("CLERK_PUBLISHABLE_KEY not set in .env")
    # Strip prefix e.g. "pk_test_" or "pk_live_"
    encoded = "_".join(pk.split("_")[2:])
    # Base64 decode (add padding if needed)
    padded = encoded + "=" * (4 - len(encoded) % 4)
    domain = base64.b64decode(padded).decode().rstrip("$")
    return f"https://{domain}/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Fetch and cache Clerk's public JWKS. Cached for the process lifetime."""
    url = _clerk_jwks_url()
    response = httpx.get(url)
    response.raise_for_status()
    return response.json()


def verify_clerk_token(token: str) -> str:
    """
    Verify a Clerk JWT and return the Clerk user ID (the 'sub' claim).
    Raises HTTPException 401 if invalid.
    """
    try:
        jwks = _get_jwks()
        # Decode header to get key id
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Find the matching key in JWKS
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Token signing key not found")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk tokens don't use aud
        )
        clerk_id: str = payload.get("sub")
        if not clerk_id:
            raise HTTPException(status_code=401, detail="Token missing subject")
        return clerk_id

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency — verifies the Clerk token and returns the
    matching user row from tak.db.

    Usage:
        @app.get("/some/protected/route")
        def my_route(user: dict = Depends(get_current_user)):
            user_id = user["id"]  # the database integer id
    """
    clerk_id = verify_clerk_token(credentials.credentials)

    conn = sqlite3.connect("tak.db")
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE clerk_id = ?", (clerk_id,)
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="User not found — have you created an account?"
        )

    return dict(row)
