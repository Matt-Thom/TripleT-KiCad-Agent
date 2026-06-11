"""Project persistence models.

A ``Project`` bundles a BOM (``BomItem``) and a chat history (``Message``).
The first-run UX creates a single "default" project so the single-page UI keeps
working until multi-project support lands.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite-friendly, replaces deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class BomItem(SQLModel, table=True):
    __tablename__ = "bom_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True, nullable=False)

    mpn: str = Field(index=True)
    manufacturer: str = ""
    description: str = ""
    price: Optional[float] = None
    stock: Optional[int] = None
    supplier: str = "LCSC"
    supplier_part_number: str = ""
    datasheet_url: Optional[str] = None
    attributes: dict = Field(default_factory=dict, sa_column=Column(JSON))
    quantity: int = 1

    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class Message(SQLModel, table=True):
    __tablename__ = "message"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True, nullable=False)

    role: str
    content: str
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


class BlockDiagram(SQLModel, table=True):
    __tablename__ = "block_diagram"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", unique=True, index=True, nullable=False)

    blocks: list = Field(default_factory=list, sa_column=Column(JSON))
    connections: list = Field(default_factory=list, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class SchematicIR(SQLModel, table=True):
    __tablename__ = "schematic_ir"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", unique=True, index=True, nullable=False)

    components: list = Field(default_factory=list, sa_column=Column(JSON))
    nets: list = Field(default_factory=list, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)

