"""Analytics API — Phase 6."""

import asyncio

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
import app.core.database as db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
async def get_analytics(user_id: str = Depends(get_current_user)):
    return await asyncio.to_thread(db.get_analytics, user_id)
