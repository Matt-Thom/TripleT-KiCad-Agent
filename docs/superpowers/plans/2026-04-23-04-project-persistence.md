# Project Persistence (SQLite) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a `Project` concept — persisted in SQLite — that bundles a BOM, generated files, and chat history. Migrate the in-memory `BOMContext` to server-backed state so a browser refresh no longer wipes user work.

**Architecture:** SQLModel (SQLAlchemy + Pydantic) over SQLite at `./data/triplet.db`. Three tables: `project`, `bom_item`, `message`. A single "default" project auto-created on first run to preserve current single-page UX; multi-project UI is a future plan. Frontend `BOMContext` becomes a thin cache over `/api/projects/{id}/bom` endpoints.

**Tech Stack:** `sqlmodel>=0.0.22`, `aiosqlite>=0.20` for async SQLAlchemy, `alembic>=1.13` (optional — deferred; MVP uses `SQLModel.metadata.create_all`), `pytest`.

**Prerequisite:** Plans 01–03 landed.

**Branch:** `feat/project-persistence` off `dev`.

---

## File Structure

- Create: `backend/db.py` — engine, session dependency, `init_db()`.
- Create: `backend/models/project.py` — `Project`, `BomItem`, `Message` SQLModel classes.
- Create: `backend/routers/projects.py` — REST endpoints for projects, BOM, messages.
- Modify: `backend/main.py` — include the router, call `init_db()` on startup.
- Modify: `pyproject.toml` — add deps.
- Modify: `.gitignore` — add `data/`.
- Create: `backend/tests/test_projects.py`
- Modify: `frontend/src/context/BOMContext.tsx` — fetch + mutate through API.
- Modify: `frontend/src/components/BOMPage.tsx` — handle async state.

---

## Task 1: Dependencies + db module — failing test

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `backend/tests/test_projects.py`

- [ ] **Step 1: Add deps**

Append to `dependencies` in `pyproject.toml`:

```
    "sqlmodel>=0.0.22",
    "aiosqlite>=0.20.0",
```

Then:

```bash
uv sync
```

- [ ] **Step 2: Ignore data directory**

Append to `.gitignore`:

```
data/
```

- [ ] **Step 3: Failing test for init_db**

Create `backend/tests/test_projects.py`:

```python
import asyncio
from pathlib import Path

import pytest

from backend.db import init_db, get_session, get_engine


@pytest.mark.asyncio
async def test_init_db_creates_sqlite_file(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("TRIPLET_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    # Force the singleton engine to rebuild with the new URL
    import backend.db as dbmod
    dbmod._engine = None
    await init_db()
    assert db_path.exists()
```

- [ ] **Step 4: Run, confirm failure**

```bash
uv run pytest backend/tests/test_projects.py -v
```

Expected: import error on `backend.db`.

- [ ] **Step 5: Commit**

```bash
git checkout -b feat/project-persistence
git add pyproject.toml uv.lock .gitignore backend/tests/test_projects.py
git commit -m "test: failing test for init_db"
```

---

## Task 2: `backend/db.py`

**Files:**
- Create: `backend/db.py`

- [ ] **Step 1: Write the module**

```python
"""Async SQLite via SQLModel."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel
from sqlalchemy.orm import sessionmaker

DEFAULT_URL = "sqlite+aiosqlite:///data/triplet.db"
_engine = None
_session_factory = None


def _url() -> str:
    return os.getenv("TRIPLET_DB_URL", DEFAULT_URL)


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        # Ensure parent directory exists for file-based SQLite URLs
        url = _url()
        if url.startswith("sqlite+aiosqlite:///"):
            path = url.removeprefix("sqlite+aiosqlite:///")
            if path and not path.startswith(":memory:"):
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        _engine = create_async_engine(url, echo=False, future=True)
        _session_factory = sessionmaker(
            bind=_engine, class_=AsyncSession, expire_on_commit=False
        )
    return _engine


async def init_db() -> None:
    engine = get_engine()
    # Import all model modules so SQLModel.metadata picks them up
    from backend.models import project  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    get_engine()  # Lazy init
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session
```

- [ ] **Step 2: Run test**

```bash
uv run pytest backend/tests/test_projects.py::test_init_db_creates_sqlite_file -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add backend/db.py
git commit -m "feat(db): async SQLite via SQLModel"
```

---

## Task 3: Models — failing test

**Files:**
- Modify: `backend/tests/test_projects.py`

- [ ] **Step 1: Append tests**

```python
@pytest.mark.asyncio
async def test_project_model_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "t.db"
    monkeypatch.setenv("TRIPLET_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import backend.db as dbmod
    dbmod._engine = None
    await init_db()

    from backend.models.project import Project, BomItem
    from sqlmodel import select

    async with get_session() as s:
        proj = Project(name="MyBoard", description="test")
        s.add(proj)
        await s.commit()
        await s.refresh(proj)

        item = BomItem(
            project_id=proj.id,
            mpn="STM32F103C8T6",
            manufacturer="ST",
            supplier="LCSC",
            supplier_part_number="C8734",
            description="ARM MCU",
            quantity=1,
        )
        s.add(item)
        await s.commit()

        result = await s.execute(select(BomItem).where(BomItem.project_id == proj.id))
        items = result.scalars().all()
        assert len(items) == 1
        assert items[0].mpn == "STM32F103C8T6"
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_projects.py -v
```

Expected: import error on `backend.models.project`.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_projects.py
git commit -m "test: failing test for Project/BomItem models"
```

---

## Task 4: Models implementation

**Files:**
- Create: `backend/models/project.py`

- [ ] **Step 1: Write models**

```python
"""Project, BomItem, Message tables."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BomItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    mpn: str
    manufacturer: str = ""
    supplier: str = "LCSC"
    supplier_part_number: str = ""
    description: str = ""
    quantity: int = 1
    added_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    role: str  # "user" | "assistant" | "tool" | "system"
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_projects.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add backend/models/project.py
git commit -m "feat(db): Project, BomItem, Message models"
```

---

## Task 5: Projects router — failing test

**Files:**
- Modify: `backend/tests/test_projects.py`

- [ ] **Step 1: Append API tests**

```python
from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("TRIPLET_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    import backend.db as dbmod
    dbmod._engine = None
    # App startup must run init_db
    from backend.main import app
    return TestClient(app)


def test_default_project_exists_after_startup(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert any(p["name"] == "default" for p in projects)


def test_add_bom_item_roundtrip(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    projects = client.get("/api/projects").json()
    proj_id = projects[0]["id"]

    payload = {
        "mpn": "STM32F103",
        "manufacturer": "ST",
        "supplier": "LCSC",
        "supplier_part_number": "C8734",
        "description": "ARM MCU",
        "quantity": 2,
    }
    resp = client.post(f"/api/projects/{proj_id}/bom", json=payload)
    assert resp.status_code == 200

    resp = client.get(f"/api/projects/{proj_id}/bom")
    bom = resp.json()
    assert len(bom) == 1
    assert bom[0]["mpn"] == "STM32F103"
    assert bom[0]["quantity"] == 2


def test_delete_bom_item(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    proj_id = client.get("/api/projects").json()[0]["id"]

    client.post(f"/api/projects/{proj_id}/bom", json={"mpn": "A", "supplier_part_number": "X"})
    bom = client.get(f"/api/projects/{proj_id}/bom").json()
    item_id = bom[0]["id"]

    resp = client.delete(f"/api/projects/{proj_id}/bom/{item_id}")
    assert resp.status_code == 200
    assert client.get(f"/api/projects/{proj_id}/bom").json() == []
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_projects.py -v
```

Expected: 404s — no router wired yet.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_projects.py
git commit -m "test: failing tests for projects/BOM API"
```

---

## Task 6: Projects router

**Files:**
- Create: `backend/routers/projects.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write router**

```python
"""REST endpoints for projects, BOM items, and chat messages."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from backend.db import get_session
from backend.models.project import BomItem, Message, Project

router = APIRouter()


class BomItemIn(BaseModel):
    mpn: str
    manufacturer: str = ""
    supplier: str = "LCSC"
    supplier_part_number: str = ""
    description: str = ""
    quantity: int = 1


async def ensure_default_project() -> None:
    async with get_session() as s:
        result = await s.execute(select(Project).where(Project.name == "default"))
        existing = result.scalar_one_or_none()
        if existing is None:
            s.add(Project(name="default", description="Default project"))
            await s.commit()


@router.get("/projects")
async def list_projects() -> list[dict]:
    await ensure_default_project()
    async with get_session() as s:
        result = await s.execute(select(Project).order_by(Project.id))
        return [p.model_dump() for p in result.scalars().all()]


@router.post("/projects")
async def create_project(body: dict) -> dict:
    name = body.get("name") or "Untitled"
    description = body.get("description") or ""
    async with get_session() as s:
        p = Project(name=name, description=description)
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p.model_dump()


@router.get("/projects/{project_id}/bom")
async def list_bom(project_id: int) -> list[dict]:
    async with get_session() as s:
        result = await s.execute(select(BomItem).where(BomItem.project_id == project_id))
        return [i.model_dump() for i in result.scalars().all()]


@router.post("/projects/{project_id}/bom")
async def add_bom_item(project_id: int, item: BomItemIn) -> dict:
    async with get_session() as s:
        proj = await s.get(Project, project_id)
        if proj is None:
            raise HTTPException(status_code=404, detail="Project not found")
        bom = BomItem(project_id=project_id, **item.model_dump())
        s.add(bom)
        await s.commit()
        await s.refresh(bom)
        return bom.model_dump()


@router.delete("/projects/{project_id}/bom/{item_id}")
async def delete_bom_item(project_id: int, item_id: int) -> dict:
    async with get_session() as s:
        item = await s.get(BomItem, item_id)
        if item is None or item.project_id != project_id:
            raise HTTPException(status_code=404, detail="BOM item not found")
        await s.delete(item)
        await s.commit()
        return {"deleted": item_id}


@router.get("/projects/{project_id}/messages")
async def list_messages(project_id: int) -> list[dict]:
    async with get_session() as s:
        result = await s.execute(
            select(Message).where(Message.project_id == project_id).order_by(Message.id)
        )
        return [m.model_dump() for m in result.scalars().all()]


@router.post("/projects/{project_id}/messages")
async def add_message(project_id: int, body: dict) -> dict:
    async with get_session() as s:
        proj = await s.get(Project, project_id)
        if proj is None:
            raise HTTPException(status_code=404, detail="Project not found")
        msg = Message(project_id=project_id, role=body.get("role", "user"), content=body.get("content", ""))
        s.add(msg)
        await s.commit()
        await s.refresh(msg)
        return msg.model_dump()
```

- [ ] **Step 2: Wire into main.py**

In `backend/main.py`, after existing `app.include_router(settings.router, prefix="/api")`:

```python
from backend.routers import projects as projects_router
from backend.db import init_db


@app.on_event("startup")
async def _startup() -> None:
    await init_db()


app.include_router(projects_router.router, prefix="/api")
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest backend -v
```

Expected: all pass including the new API tests.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/projects.py backend/main.py
git commit -m "feat(api): projects + BOM + messages endpoints"
```

---

## Task 7: Frontend — Part type alignment

**Files:**
- Modify: `frontend/src/types/Part.ts`

- [ ] **Step 1: Confirm `Part` matches the backend BomItemIn shape**

Read `frontend/src/types/Part.ts`. If `Part` already has `mpn`, `manufacturer`, `description`, `supplier`, `supplier_part_number` fields, no change. Otherwise, align it:

```ts
export interface Part {
  mpn: string;
  manufacturer: string;
  description: string;
  price?: number;
  stock?: number;
  supplier: string;
  supplier_part_number: string;
  datasheet_url?: string | null;
  attributes?: Record<string, unknown>;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/Part.ts
git commit -m "chore(frontend): align Part type with backend"
```

---

## Task 8: BOMContext backed by API

**Files:**
- Modify: `frontend/src/context/BOMContext.tsx`

- [ ] **Step 1: Rewrite**

```tsx
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import axios from 'axios';
import type { Part } from '../types/Part';

interface BomRecord extends Part {
  id: number;
  quantity: number;
}

interface BOMContextType {
  items: BomRecord[];
  projectId: number | null;
  addToBOM: (part: Part) => Promise<void>;
  removeFromBOM: (id: number) => Promise<void>;
  refresh: () => Promise<void>;
}

const BOMContext = createContext<BOMContextType | undefined>(undefined);

const API = (path: string) => `http://localhost:8000${path}`;

export const BOMProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<BomRecord[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      const { data } = await axios.get(API('/api/projects'));
      const def = data.find((p: { name: string }) => p.name === 'default') ?? data[0];
      if (def) {
        setProjectId(def.id);
        const { data: bom } = await axios.get(API(`/api/projects/${def.id}/bom`));
        setItems(bom);
      }
    })().catch((err) => console.error('Failed to load default project', err));
  }, []);

  const refresh = async () => {
    if (projectId == null) return;
    const { data } = await axios.get(API(`/api/projects/${projectId}/bom`));
    setItems(data);
  };

  const addToBOM = async (part: Part) => {
    if (projectId == null) return;
    if (items.some((i) => i.mpn === part.mpn)) return; // client-side dedup
    await axios.post(API(`/api/projects/${projectId}/bom`), {
      mpn: part.mpn,
      manufacturer: part.manufacturer,
      supplier: part.supplier,
      supplier_part_number: part.supplier_part_number,
      description: part.description,
      quantity: 1,
    });
    await refresh();
  };

  const removeFromBOM = async (id: number) => {
    if (projectId == null) return;
    await axios.delete(API(`/api/projects/${projectId}/bom/${id}`));
    await refresh();
  };

  return (
    <BOMContext.Provider value={{ items, projectId, addToBOM, removeFromBOM, refresh }}>
      {children}
    </BOMContext.Provider>
  );
};

export const useBOM = () => {
  const ctx = useContext(BOMContext);
  if (!ctx) throw new Error('useBOM must be used within a BOMProvider');
  return ctx;
};
```

- [ ] **Step 2: Update callers that delete by mpn**

Search for `removeFromBOM(` callers:

```bash
grep -rn "removeFromBOM(" frontend/src
```

Update each callsite to pass the numeric `id` instead of `mpn`. In `BOMPage.tsx` the component iterating items has access to `item.id`.

- [ ] **Step 3: Manual verification**

```bash
uv run uvicorn backend.main:app --reload
# In a second shell:
cd frontend && npm run dev
```

1. Open the app. Search a part, Add to BOM. Refresh the page — BOM should survive.
2. Delete a BOM item — it disappears and stays gone after refresh.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/context/BOMContext.tsx frontend/src/components/BOMPage.tsx
git commit -m "feat(frontend): BOM backed by /api/projects/{id}/bom"
```

---

## Task 9: Persist chat messages (optional this phase)

**Files:**
- Modify: `backend/main.py` — the `/api/chat` handler

- [ ] **Step 1: Insert message persistence**

At the top of the `/api/chat` handler, default to the `default` project, write the user turn and the assistant reply:

```python
from backend.routers.projects import ensure_default_project
from backend.models.project import Message
from backend.db import get_session
from sqlmodel import select
from backend.models.project import Project


async def _default_project_id() -> int:
    await ensure_default_project()
    async with get_session() as s:
        result = await s.execute(select(Project).where(Project.name == "default"))
        proj = result.scalar_one()
        return proj.id
```

In the `chat` handler, before returning:

```python
project_id = await _default_project_id()
async with get_session() as s:
    # Persist the most recent user message and the assistant reply.
    last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    if last_user:
        s.add(Message(project_id=project_id, role="user", content=str(last_user.get("content", ""))))
    s.add(Message(project_id=project_id, role="assistant", content=response_text))
    await s.commit()
```

- [ ] **Step 2: Add a smoke test**

Append to `backend/tests/test_projects.py`:

```python
def test_chat_persists_messages(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    from unittest.mock import patch

    async def fake_get_response(messages):
        return "sure, here you go"

    with patch("backend.services.ai.ai_service.get_response", side_effect=fake_get_response):
        resp = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code == 200

    proj_id = client.get("/api/projects").json()[0]["id"]
    msgs = client.get(f"/api/projects/{proj_id}/messages").json()
    roles = [m["role"] for m in msgs]
    assert "user" in roles and "assistant" in roles
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest backend -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/main.py backend/tests/test_projects.py
git commit -m "feat(chat): persist user + assistant messages to default project"
```

---

## Task 10: Docs and PR

**Files:**
- Modify: `PLANNING.md`

- [ ] **Step 1: Update**

Add a line noting Project persistence landed. Also mention: single default project for now; multi-project UI deferred.

- [ ] **Step 2: Commit and open PR**

```bash
git add PLANNING.md
git commit -m "docs: record project persistence MVP"
git push -u origin feat/project-persistence
gh pr create --base dev --title "feat: project persistence (SQLite)" --body "$(cat <<'EOF'
## Summary
- SQLite via SQLModel; schema auto-created at startup.
- Project / BomItem / Message tables + CRUD router.
- Default project seeded on first run. BOMContext now API-backed.
- Chat messages persisted to the default project.

## Test plan
- [x] `uv run pytest backend -v` — all green.
- [ ] Manual: add part to BOM, refresh page, BOM survives.
- [ ] Manual: delete item, reload, stays deleted.
EOF
)"
```
