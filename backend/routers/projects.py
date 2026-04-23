"""REST endpoints for projects, their BOM, and chat message history."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db import get_session
from backend.models.project import BomItem, Message, Project

router = APIRouter(tags=["projects"])

DEFAULT_PROJECT_NAME = "Default"


# ---------- Pydantic schemas ----------------------------------------------


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class BomItemIn(BaseModel):
    mpn: str
    manufacturer: str = ""
    description: str = ""
    price: Optional[float] = None
    stock: Optional[int] = None
    supplier: str = "LCSC"
    supplier_part_number: str = ""
    datasheet_url: Optional[str] = None
    attributes: dict = Field(default_factory=dict)
    quantity: int = 1


class BomItemOut(BomItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime


class MessageIn(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    content: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    role: str
    content: str
    created_at: datetime


# ---------- Helpers --------------------------------------------------------


async def _ensure_default_project(session: AsyncSession) -> Project:
    result = await session.execute(
        select(Project).where(Project.name == DEFAULT_PROJECT_NAME)
    )
    project = result.scalars().first()
    if project is None:
        project = Project(name=DEFAULT_PROJECT_NAME)
        session.add(project)
        await session.commit()
        await session.refresh(project)
    return project


async def _get_project_or_404(session: AsyncSession, project_id: int) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ---------- Endpoints ------------------------------------------------------


@router.get("/projects", response_model=List[ProjectOut])
async def list_projects() -> List[ProjectOut]:
    async with get_session() as session:
        await _ensure_default_project(session)
        rows = (
            await session.execute(select(Project).order_by(Project.id))
        ).scalars().all()
        return [ProjectOut.model_validate(p) for p in rows]


@router.post(
    "/projects",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(payload: ProjectCreate) -> ProjectOut:
    async with get_session() as session:
        project = Project(name=payload.name)
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return ProjectOut.model_validate(project)


@router.get("/projects/{project_id}/bom", response_model=List[BomItemOut])
async def list_bom(project_id: int) -> List[BomItemOut]:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        rows = (
            await session.execute(
                select(BomItem)
                .where(BomItem.project_id == project_id)
                .order_by(BomItem.id)
            )
        ).scalars().all()
        return [BomItemOut.model_validate(item) for item in rows]


@router.post(
    "/projects/{project_id}/bom",
    response_model=BomItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_bom_item(project_id: int, payload: BomItemIn) -> BomItemOut:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        item = BomItem(project_id=project_id, **payload.model_dump())
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return BomItemOut.model_validate(item)


@router.delete(
    "/projects/{project_id}/bom/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_bom_item(project_id: int, item_id: int) -> None:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        item = await session.get(BomItem, item_id)
        if item is None or item.project_id != project_id:
            raise HTTPException(status_code=404, detail="BOM item not found")
        await session.delete(item)
        await session.commit()
        return None


@router.get("/projects/{project_id}/messages", response_model=List[MessageOut])
async def list_messages(project_id: int) -> List[MessageOut]:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        rows = (
            await session.execute(
                select(Message)
                .where(Message.project_id == project_id)
                .order_by(Message.id)
            )
        ).scalars().all()
        return [MessageOut.model_validate(m) for m in rows]


@router.post(
    "/projects/{project_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(project_id: int, payload: MessageIn) -> MessageOut:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        message = Message(
            project_id=project_id, role=payload.role, content=payload.content
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return MessageOut.model_validate(message)
