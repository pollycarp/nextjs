"""JWT auth helpers + FastAPI dependency — Phase 6."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Header, HTTPException

from app.core.config import settings

_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def verify_token(token: str) -> str:
    """Decode token and return user_id, or raise HTTPException 401."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """FastAPI dependency — requires a valid Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_token(authorization[7:])


async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """FastAPI dependency — returns user_id if token present, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return verify_token(authorization[7:])
    except HTTPException:
        return None
