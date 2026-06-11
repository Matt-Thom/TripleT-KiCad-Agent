"""REST endpoints for projects, their BOM, and chat message history."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db import get_session
from backend.models.project import BomItem, Message, Project, BlockDiagram, SchematicIR, utcnow
from backend.models.schematic_ir import BlockDiagramData, SchematicIRData
from backend.services.erc import erc_service, ErcViolation

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


class BomItemUpdate(BaseModel):
    quantity: int = Field(default=1, ge=1)


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


@router.put(
    "/projects/{project_id}/bom/{item_id}",
    response_model=BomItemOut,
)
async def update_bom_item_quantity(
    project_id: int, item_id: int, payload: BomItemUpdate
) -> BomItemOut:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        item = await session.get(BomItem, item_id)
        if item is None or item.project_id != project_id:
            raise HTTPException(status_code=404, detail="BOM item not found")
        item.quantity = payload.quantity
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return BomItemOut.model_validate(item)


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


@router.get("/projects/{project_id}/block-diagram", response_model=BlockDiagramData)
async def get_block_diagram(project_id: int) -> BlockDiagramData:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        result = await session.execute(
            select(BlockDiagram).where(BlockDiagram.project_id == project_id)
        )
        bd = result.scalars().first()
        if bd is None:
            return BlockDiagramData(blocks=[], connections=[])
        return BlockDiagramData(blocks=bd.blocks, connections=bd.connections)


@router.post("/projects/{project_id}/block-diagram", response_model=BlockDiagramData)
async def save_block_diagram(project_id: int, payload: BlockDiagramData) -> BlockDiagramData:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        result = await session.execute(
            select(BlockDiagram).where(BlockDiagram.project_id == project_id)
        )
        bd = result.scalars().first()
        blocks_dict = [b.model_dump() for b in payload.blocks]
        connections_dict = [c.model_dump() for c in payload.connections]
        if bd is None:
            bd = BlockDiagram(
                project_id=project_id,
                blocks=blocks_dict,
                connections=connections_dict,
            )
            session.add(bd)
        else:
            bd.blocks = blocks_dict
            bd.connections = connections_dict
            bd.updated_at = utcnow()
            session.add(bd)
        await session.commit()
        return BlockDiagramData(blocks=bd.blocks, connections=bd.connections)


@router.get("/projects/{project_id}/schematic-ir", response_model=SchematicIRData)
async def get_schematic_ir(project_id: int) -> SchematicIRData:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        result = await session.execute(
            select(SchematicIR).where(SchematicIR.project_id == project_id)
        )
        sir = result.scalars().first()
        if sir is None:
            return SchematicIRData(components=[], nets=[])
        return SchematicIRData(components=sir.components, nets=sir.nets)


@router.post("/projects/{project_id}/schematic-ir", response_model=SchematicIRData)
async def save_schematic_ir(project_id: int, payload: SchematicIRData) -> SchematicIRData:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        result = await session.execute(
            select(SchematicIR).where(SchematicIR.project_id == project_id)
        )
        sir = result.scalars().first()
        components_dict = [c.model_dump() for c in payload.components]
        nets_dict = [n.model_dump() for n in payload.nets]
        if sir is None:
            sir = SchematicIR(
                project_id=project_id,
                components=components_dict,
                nets=nets_dict,
            )
            session.add(sir)
        else:
            sir.components = components_dict
            sir.nets = nets_dict
            sir.updated_at = utcnow()
            session.add(sir)
        await session.commit()
        return SchematicIRData(components=sir.components, nets=sir.nets)


@router.get("/projects/{project_id}/erc", response_model=List[ErcViolation])
async def get_erc(project_id: int) -> List[ErcViolation]:
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        result = await session.execute(
            select(SchematicIR).where(SchematicIR.project_id == project_id)
        )
        sir = result.scalars().first()
        if sir is None:
            return []
        ir_data = SchematicIRData(components=sir.components, nets=sir.nets)
        return erc_service.check(ir_data)


@router.post("/projects/{project_id}/schematic-ir/compile")
async def compile_schematic_ir(project_id: int, filename: Optional[str] = None):
    from backend.services.schematic import schematic_service
    import os
    async with get_session() as session:
        project = await _get_project_or_404(session, project_id)
        result = await session.execute(
            select(SchematicIR).where(SchematicIR.project_id == project_id)
        )
        sir = result.scalars().first()
        if sir is None or not sir.components:
            raise HTTPException(status_code=400, detail="Cannot compile empty Schematic IR")

        ir_data = SchematicIRData(components=sir.components, nets=sir.nets)
        try:
            files = schematic_service.compile_ir_to_project(
                ir_data, project_name=filename or project.name
            )
            sch_name = os.path.basename(files["schematic"])
            return {
                # Kept for backward compatibility with older clients.
                "download_url": f"/api/download/{sch_name}",
                "filename": sch_name,
                "files": [
                    {
                        "kind": kind,
                        "filename": os.path.basename(path),
                        "download_url": f"/api/download/{os.path.basename(path)}",
                    }
                    for kind, path in files.items()
                ],
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Compilation error: {e}")

