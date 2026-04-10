"""Conversations API — Phase 6."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user
import app.core.database as db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    project_id: Optional[str] = None
    title: str = "New Conversation"


class MessageCreate(BaseModel):
    role: str
    content: str


@router.get("")
async def list_conversations(user_id: str = Depends(get_current_user)):
    return await asyncio.to_thread(db.get_conversations, user_id)


@router.post("", status_code=201)
async def create_conversation(body: ConversationCreate, user_id: str = Depends(get_current_user)):
    return await asyncio.to_thread(db.create_conversation, user_id, body.project_id, body.title)


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str, user_id: str = Depends(get_current_user)):
    return await asyncio.to_thread(db.get_messages, conversation_id)


@router.post("/{conversation_id}/messages", status_code=201)
async def add_message(conversation_id: str, body: MessageCreate, user_id: str = Depends(get_current_user)):
    return await asyncio.to_thread(db.save_message, conversation_id, body.role, body.content)
