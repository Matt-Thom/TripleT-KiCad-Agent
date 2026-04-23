# Supplier Expansion (DigiKey) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add DigiKey as a second component source behind the unified `Part` model, so the agent is not dependent on the unofficial `jlcsearch` endpoint, and can return results deduplicated across suppliers.

**Architecture:** A `SupplierAdapter` protocol with two implementations: the existing LCSC and a new DigiKey adapter (OAuth2 Client Credentials). A `PartSearchService` fan-outs to all enabled adapters in parallel and merges by `(manufacturer, mpn)` with per-supplier sub-records. The existing `/api/search/lcsc` endpoint stays for backward compat; a new `/api/search` endpoint returns the unified result. The AI `search_lcsc` tool is renamed to `search_parts` (with a backwards-compat alias).

**Tech Stack:** `httpx` (existing), `tenacity>=8.5` (new, retry), `pytest`, `pytest-asyncio`.

**Prerequisite:** Plans 01–04 landed.

**Branch:** `feat/supplier-expansion` off `dev`.

---

## File Structure

- Create: `backend/services/suppliers/__init__.py`
- Create: `backend/services/suppliers/base.py` — `SupplierAdapter` protocol + `SupplierCredentials`.
- Modify: `backend/services/lcsc.py` — conform to the new protocol.
- Create: `backend/services/suppliers/digikey.py`
- Create: `backend/services/part_search.py` — orchestrator with merge/dedup.
- Modify: `backend/main.py` — new `/api/search` endpoint.
- Modify: `backend/services/tools.py` — `search_parts` tool (alias `search_lcsc`).
- Modify: `backend/models/settings.py` — DigiKey client id/secret fields.
- Modify: `backend/routers/settings.py` — plumb DigiKey creds.
- Create: `backend/tests/test_supplier_digikey.py`
- Create: `backend/tests/test_part_search_service.py`
- Modify: `pyproject.toml` — add `tenacity`.

---

## Task 1: Supplier adapter protocol — failing test

**Files:**
- Create: `backend/tests/test_part_search_service.py`

- [ ] **Step 1: Write failing test**

```python
import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.services.suppliers.base import SupplierAdapter, SupplierCredentials
from backend.services.part_search import PartSearchService
from backend.services.lcsc import Part


class _Stub(SupplierAdapter):
    name = "Stub"

    def __init__(self, parts: list[Part]) -> None:
        self._parts = parts

    async def is_configured(self) -> bool:
        return True

    async def search(self, query: str, limit: int = 10) -> list[Part]:
        return self._parts


@pytest.mark.asyncio
async def test_part_search_merges_results_by_mpn():
    a = _Stub([
        Part(mpn="STM32F103C8T6", manufacturer="ST", description="ARM MCU",
             supplier="LCSC", supplier_part_number="C8734", price=2.0, stock=100),
    ])
    b = _Stub([
        Part(mpn="STM32F103C8T6", manufacturer="ST", description="ARM MCU",
             supplier="DigiKey", supplier_part_number="497-STM32", price=3.5, stock=200),
    ])
    svc = PartSearchService(adapters=[a, b])
    results = await svc.search("STM32")
    assert len(results) == 1
    part = results[0]
    # Primary supplier is whichever has stock first returned, but alt_suppliers lists the other
    suppliers = {part.supplier} | {alt.supplier for alt in part.alt_suppliers}
    assert suppliers == {"LCSC", "DigiKey"}


@pytest.mark.asyncio
async def test_part_search_skips_unconfigured_adapters():
    class Unconfigured(_Stub):
        async def is_configured(self) -> bool:
            return False

    lcsc = _Stub([Part(mpn="R", manufacturer="X", description="r",
                       supplier="LCSC", supplier_part_number="C1")])
    dk = Unconfigured([])
    svc = PartSearchService(adapters=[lcsc, dk])
    results = await svc.search("R")
    assert len(results) == 1
    assert results[0].supplier == "LCSC"
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_part_search_service.py -v
```

Expected: import errors.

- [ ] **Step 3: Commit**

```bash
git checkout -b feat/supplier-expansion
git add backend/tests/test_part_search_service.py
git commit -m "test: failing tests for PartSearchService merge behaviour"
```

---

## Task 2: Protocol + unified Part model

**Files:**
- Create: `backend/services/suppliers/__init__.py` (empty)
- Create: `backend/services/suppliers/base.py`
- Modify: `backend/services/lcsc.py` — add `alt_suppliers` field and protocol conformance.

- [ ] **Step 1: Empty package marker**

```bash
: > backend/services/suppliers/__init__.py
```

- [ ] **Step 2: Write `base.py`**

```python
"""Supplier adapter protocol + credentials helper."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SupplierCredentials:
    client_id: str = ""
    client_secret: str = ""


@runtime_checkable
class SupplierAdapter(Protocol):
    name: str

    async def is_configured(self) -> bool:
        """True if this adapter has everything it needs to hit the remote API."""
        ...

    async def search(self, query: str, limit: int = 10) -> list:
        """Return a list of Part records matching the query."""
        ...
```

- [ ] **Step 3: Extend `Part` to carry alt suppliers**

In `backend/services/lcsc.py`, extend the model:

```python
class AltSupplier(BaseModel):
    supplier: str
    supplier_part_number: str
    price: float = 0.0
    stock: int = 0


class Part(BaseModel):
    mpn: str = Field(..., description="Manufacturer Part Number")
    manufacturer: str = Field("Unknown")
    description: str = Field("")
    price: float = 0.0
    stock: int = 0
    supplier_part_number: str = Field(...)
    supplier: str = Field("LCSC")
    datasheet_url: Optional[str] = None
    attributes: dict = Field(default_factory=dict)
    alt_suppliers: list[AltSupplier] = Field(default_factory=list)
```

- [ ] **Step 4: Make `LCSCService` conform to `SupplierAdapter`**

Update the class:

```python
class LCSCService:
    BASE_URL = "https://jlcsearch.tscircuit.com/api/search"
    name = "LCSC"

    async def is_configured(self) -> bool:
        return True  # Unauthenticated endpoint

    async def search(self, query: str, limit: int = 10) -> list[Part]:
        ...  # existing body
```

- [ ] **Step 5: Run existing LCSC tests**

```bash
uv run pytest backend/tests/test_search.py -v
```

Expected: still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services/suppliers/ backend/services/lcsc.py
git commit -m "feat(suppliers): SupplierAdapter protocol + alt_suppliers on Part"
```

---

## Task 3: `PartSearchService`

**Files:**
- Create: `backend/services/part_search.py`

- [ ] **Step 1: Implement**

```python
"""Fan-out part search over all configured SupplierAdapters, merging by MPN."""
from __future__ import annotations

import asyncio

from backend.services.lcsc import AltSupplier, Part
from backend.services.suppliers.base import SupplierAdapter


class PartSearchService:
    def __init__(self, adapters: list[SupplierAdapter]) -> None:
        self._adapters = adapters

    async def search(self, query: str, limit: int = 10) -> list[Part]:
        active = [a for a in self._adapters if await a.is_configured()]
        raw: list[list[Part]] = await asyncio.gather(
            *(a.search(query, limit=limit) for a in active),
            return_exceptions=False,
        )
        flat: list[Part] = [p for batch in raw for p in batch]

        # Merge by (manufacturer lowercased, mpn lowercased)
        merged: dict[tuple[str, str], Part] = {}
        for part in flat:
            key = (part.manufacturer.lower(), part.mpn.lower())
            if key not in merged:
                merged[key] = part
                continue
            existing = merged[key]
            # Only add as alt if the supplier differs
            if part.supplier != existing.supplier and not any(
                alt.supplier == part.supplier for alt in existing.alt_suppliers
            ):
                existing.alt_suppliers.append(
                    AltSupplier(
                        supplier=part.supplier,
                        supplier_part_number=part.supplier_part_number,
                        price=part.price,
                        stock=part.stock,
                    )
                )
        return list(merged.values())
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_part_search_service.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add backend/services/part_search.py
git commit -m "feat(suppliers): PartSearchService with fan-out merge"
```

---

## Task 4: DigiKey adapter — failing test

**Files:**
- Modify: `pyproject.toml` — add `"tenacity>=8.5.0",`
- Create: `backend/tests/test_supplier_digikey.py`

- [ ] **Step 1: Add tenacity**

```bash
uv sync
```

- [ ] **Step 2: Failing tests**

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.suppliers.digikey import DigiKeyAdapter
from backend.services.suppliers.base import SupplierCredentials


@pytest.mark.asyncio
async def test_digikey_is_configured_true_when_creds_present(monkeypatch):
    monkeypatch.setenv("DIGIKEY_CLIENT_ID", "id")
    monkeypatch.setenv("DIGIKEY_CLIENT_SECRET", "secret")
    dk = DigiKeyAdapter()
    assert await dk.is_configured()


@pytest.mark.asyncio
async def test_digikey_is_configured_false_when_missing(monkeypatch):
    monkeypatch.delenv("DIGIKEY_CLIENT_ID", raising=False)
    monkeypatch.delenv("DIGIKEY_CLIENT_SECRET", raising=False)
    dk = DigiKeyAdapter()
    assert not await dk.is_configured()


@pytest.mark.asyncio
async def test_digikey_search_maps_response_to_part(monkeypatch):
    monkeypatch.setenv("DIGIKEY_CLIENT_ID", "id")
    monkeypatch.setenv("DIGIKEY_CLIENT_SECRET", "secret")
    dk = DigiKeyAdapter()

    # Stub the token call and the search call
    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json.return_value = {"access_token": "tok", "expires_in": 3600}
    token_resp.raise_for_status.return_value = None

    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.json.return_value = {
        "Products": [
            {
                "ManufacturerPartNumber": "STM32F103C8T6",
                "Manufacturer": {"Name": "STMicroelectronics"},
                "ProductDescription": "ARM Cortex-M3 MCU",
                "UnitPrice": 3.50,
                "QuantityAvailable": 200,
                "DigiKeyPartNumber": "497-10218-ND",
                "DatasheetUrl": "https://example.com/ds.pdf",
            }
        ]
    }
    search_resp.raise_for_status.return_value = None

    client_mock = AsyncMock()
    client_mock.__aenter__.return_value = client_mock
    client_mock.__aexit__.return_value = None
    client_mock.post.return_value = token_resp
    client_mock.get.return_value = search_resp

    with patch("httpx.AsyncClient", return_value=client_mock):
        results = await dk.search("STM32F103", limit=1)

    assert len(results) == 1
    part = results[0]
    assert part.mpn == "STM32F103C8T6"
    assert part.manufacturer == "STMicroelectronics"
    assert part.supplier == "DigiKey"
    assert part.supplier_part_number == "497-10218-ND"
    assert part.price == 3.50
    assert part.stock == 200
```

- [ ] **Step 3: Run, confirm failure**

```bash
uv run pytest backend/tests/test_supplier_digikey.py -v
```

Expected: import error.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock backend/tests/test_supplier_digikey.py
git commit -m "test: failing tests for DigiKey adapter"
```

---

## Task 5: DigiKey adapter — implementation

**Files:**
- Create: `backend/services/suppliers/digikey.py`

- [ ] **Step 1: Implement**

```python
"""DigiKey supplier adapter (OAuth2 Client Credentials)."""
from __future__ import annotations

import os
import time
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.services.lcsc import Part


TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
SEARCH_URL = "https://api.digikey.com/Search/v3/Products/Keyword"


class DigiKeyAdapter:
    name = "DigiKey"

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    @staticmethod
    def _creds() -> tuple[str, str]:
        return os.getenv("DIGIKEY_CLIENT_ID", ""), os.getenv("DIGIKEY_CLIENT_SECRET", "")

    async def is_configured(self) -> bool:
        cid, secret = self._creds()
        return bool(cid and secret)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        cid, secret = self._creds()
        resp = await client.post(
            TOKEN_URL,
            data={"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._token

    async def search(self, query: str, limit: int = 10) -> list[Part]:
        cid, _ = self._creds()
        async with httpx.AsyncClient(timeout=10.0) as client:
            token = await self._ensure_token(client)
            resp = await client.get(
                SEARCH_URL,
                params={"keywords": query, "recordCount": limit},
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-DIGIKEY-Client-Id": cid,
                    "X-DIGIKEY-Locale-Site": "US",
                    "X-DIGIKEY-Locale-Language": "en",
                    "X-DIGIKEY-Locale-Currency": "USD",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[Part] = []
        for product in data.get("Products", [])[:limit]:
            manufacturer = (product.get("Manufacturer") or {}).get("Name", "Unknown")
            results.append(
                Part(
                    mpn=product.get("ManufacturerPartNumber", ""),
                    manufacturer=manufacturer,
                    description=product.get("ProductDescription", ""),
                    price=float(product.get("UnitPrice", 0.0) or 0.0),
                    stock=int(product.get("QuantityAvailable", 0) or 0),
                    supplier_part_number=product.get("DigiKeyPartNumber", ""),
                    supplier="DigiKey",
                    datasheet_url=product.get("DatasheetUrl"),
                )
            )
        return results
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_supplier_digikey.py -v
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add backend/services/suppliers/digikey.py
git commit -m "feat(suppliers): DigiKey adapter (OAuth2 client credentials)"
```

---

## Task 6: Unified `/api/search` endpoint + tool

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/services/tools.py`

- [ ] **Step 1: Wire the endpoint**

In `backend/main.py`, near the existing search handler:

```python
from backend.services.part_search import PartSearchService
from backend.services.lcsc import lcsc_service
from backend.services.suppliers.digikey import DigiKeyAdapter

_part_search = PartSearchService(adapters=[lcsc_service, DigiKeyAdapter()])


@app.get("/api/search", response_model=List[Part])
async def search_parts(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    return await _part_search.search(q)
```

- [ ] **Step 2: Update tools.py**

Rename the AI tool. Keep the old name as an alias so in-flight chats don't break mid-session.

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_parts",
            "description": (
                "Search for electronic components across all configured suppliers (LCSC, DigiKey). "
                "Returns unified results with alternate-supplier pricing where available. "
                "Call per component — do not merge multiple parts into one query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Single component search term."}
                },
                "required": ["query"]
            }
        }
    },
    # ... keep existing generate_schematic, lookup_pattern, apply_pattern tools unchanged
]


async def execute_tool(name: str, args: dict):
    # Alias for backwards compatibility
    if name == "search_lcsc":
        name = "search_parts"

    if name == "search_parts":
        from backend.services.part_search import PartSearchService
        from backend.services.lcsc import lcsc_service
        from backend.services.suppliers.digikey import DigiKeyAdapter
        svc = PartSearchService(adapters=[lcsc_service, DigiKeyAdapter()])
        try:
            results = await svc.search(args["query"])
            if not results:
                return f"No results found for '{args['query']}'."
            return str([p.model_dump() for p in results[:3]])
        except Exception as e:
            return f"Error searching for '{args['query']}': {e}"

    # ... rest unchanged
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest backend -v
```

Expected: all pass. The legacy `/api/search/lcsc` tests still pass because that endpoint is unchanged.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py backend/services/tools.py
git commit -m "feat(api): /api/search unified endpoint + search_parts tool"
```

---

## Task 7: Settings plumbing for DigiKey creds

**Files:**
- Modify: `backend/models/settings.py`
- Modify: `backend/routers/settings.py`
- Modify: `frontend/src/components/SettingsPage.tsx`

- [ ] **Step 1: Settings model**

Add to `Settings`:

```python
    digikey_client_id: Optional[str] = None
    digikey_client_secret: Optional[str] = None
```

- [ ] **Step 2: Router**

In `load_settings()`, add:

```python
        digikey_client_id=os.getenv("DIGIKEY_CLIENT_ID", ""),
        digikey_client_secret=os.getenv("DIGIKEY_CLIENT_SECRET", ""),
```

In `update_settings`, plumb them through to `os.environ` and into the `.env` write block.

- [ ] **Step 3: Frontend**

Add two labeled password inputs for the DigiKey fields in `SettingsPage.tsx`, matching the style of the existing API-key inputs.

- [ ] **Step 4: Run tests**

```bash
uv run pytest backend/tests/test_settings_security.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/models/settings.py backend/routers/settings.py frontend/src/components/SettingsPage.tsx
git commit -m "feat(settings): DigiKey client id/secret"
```

---

## Task 8: Docs and PR

**Files:**
- Modify: `docs/PART_SEARCH_STRATEGY.md`
- Modify: `PLANNING.md`

- [ ] **Step 1: Update Part-Search Strategy**

Flip DigiKey to `[x] Implemented`, note the unified `/api/search` endpoint and `search_parts` tool.

- [ ] **Step 2: Commit + PR**

```bash
git add docs/PART_SEARCH_STRATEGY.md PLANNING.md
git commit -m "docs: DigiKey supplier shipped"
git push -u origin feat/supplier-expansion
gh pr create --base dev --title "feat: DigiKey adapter + unified /api/search" --body "$(cat <<'EOF'
## Summary
- SupplierAdapter protocol with LCSC and DigiKey implementations.
- PartSearchService fan-out + merge by (manufacturer, MPN).
- New /api/search endpoint returns unified Part records.
- Agent tool renamed search_lcsc → search_parts (alias kept for compat).
- Settings UI exposes DigiKey client id/secret.

## Test plan
- [x] `uv run pytest backend -v` — all green.
- [ ] Manual (requires DigiKey credentials): search "STM32F103" — results show both LCSC and DigiKey pricing on the same part.
- [ ] Manual without DigiKey credentials: search still works with LCSC only.
EOF
)"
```
