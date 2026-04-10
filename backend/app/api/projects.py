"""Projects API — Phase 6."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
import app.core.database as db

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    title: str
    description: str = ""
    tags: str = ""


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None


@router.get("")
async def list_projects(user_id: str = Depends(get_current_user)):
    return await asyncio.to_thread(db.get_projects, user_id)


@router.post("", status_code=201)
async def create_project(body: ProjectCreate, user_id: str = Depends(get_current_user)):
    return await asyncio.to_thread(db.create_project, user_id, body.title, body.description, body.tags)


@router.put("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, user_id: str = Depends(get_current_user)):
    updates = body.model_dump(exclude_none=True)
    result = await asyncio.to_thread(db.update_project, user_id, project_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, user_id: str = Depends(get_current_user)):
    deleted = await asyncio.to_thread(db.delete_project, user_id, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
