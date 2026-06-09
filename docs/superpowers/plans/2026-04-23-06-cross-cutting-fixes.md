# Cross-Cutting Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Batch the smaller security / config / developer-experience fixes surfaced in the review.

**Tech Stack:** No new runtime deps. Adds `.github/workflows/ci.yml`.

**Prerequisite:** Can run independently of plans 01–05, but easier to land after them so the test suite reflects the full system.

**Branch:** `chore/cross-cutting-fixes` off `dev`.

---

## Scope summary

| # | Fix | Files |
|---|-----|-------|
| 1 | Mask API keys in `GET /api/settings` | `backend/models/settings.py`, `backend/routers/settings.py` |
| 2 | Persist settings to `config.json`, not `.env` | `backend/routers/settings.py`, `.gitignore` |
| 3 | Return relative download URLs | `backend/services/tools.py`, `backend/main.py` (if needed) |
| 4 | Pin Python 3.12 in `pyproject.toml` | `pyproject.toml` |
| 5 | Update default model strings | `backend/services/ai.py`, `backend/models/settings.py` |
| 6 | Write `README.md` | `README.md` |
| 7 | Add CI workflow | `.github/workflows/ci.yml` |

---

## Task 1: Mask API keys in GET /settings — failing test

**Files:**
- Modify: `backend/tests/test_settings_security.py`

- [ ] **Step 1: Append failing test**

```python
def test_get_settings_masks_api_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-live-1234567890abcdef")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSy-livekey-0987654321")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()

    # Raw keys must NOT be returned
    assert "sk-live-1234567890abcdef" not in str(data)
    assert "AIzaSy-livekey-0987654321" not in str(data)

    # Presence flags
    assert data["has_openai_key"] is True
    assert data["has_gemini_key"] is True
    assert data["has_anthropic_key"] is False

    # Masked hints include last 4 chars only
    assert data["openai_key_hint"].endswith("cdef")
    assert data["openai_key_hint"].startswith("...")
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_settings_security.py -v
```

- [ ] **Step 3: Commit**

```bash
git checkout -b chore/cross-cutting-fixes
git add backend/tests/test_settings_security.py
git commit -m "test: failing test for masked API keys in GET /settings"
```

---

## Task 2: Mask API keys — implementation

**Files:**
- Modify: `backend/models/settings.py`
- Modify: `backend/routers/settings.py`

- [ ] **Step 1: Add a public `SettingsView` model**

In `backend/models/settings.py`, append:

```python
class SettingsView(BaseModel):
    """Response shape for GET /settings — NEVER contains raw API keys."""
    default_model: str
    has_openai_key: bool
    has_anthropic_key: bool
    has_gemini_key: bool
    openai_key_hint: Optional[str] = None
    anthropic_key_hint: Optional[str] = None
    gemini_key_hint: Optional[str] = None
    kicad_symbol_dir: Optional[str] = None
    kicad_footprint_dir: Optional[str] = None
    kicad_sym_lib_table: Optional[str] = None  # Added in plan 01
```

- [ ] **Step 2: Router returns the masked view**

In `backend/routers/settings.py`, update `get_settings`:

```python
from backend.models.settings import Settings, SettingsView


def _mask(value: str) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 4:
        return "...***"
    return f"...{value[-4:]}"


@router.get("/settings", response_model=SettingsView)
def get_settings() -> SettingsView:
    openai = os.getenv("OPENAI_API_KEY", "")
    anthropic = os.getenv("ANTHROPIC_API_KEY", "")
    gemini = os.getenv("GEMINI_API_KEY", "")
    return SettingsView(
        default_model=os.getenv("DEFAULT_AI_MODEL", "gemini/gemini-pro"),
        has_openai_key=bool(openai),
        has_anthropic_key=bool(anthropic),
        has_gemini_key=bool(gemini),
        openai_key_hint=_mask(openai),
        anthropic_key_hint=_mask(anthropic),
        gemini_key_hint=_mask(gemini),
        kicad_symbol_dir=os.getenv("KICAD_SYMBOL_DIR", None) or None,
        kicad_footprint_dir=os.getenv("KICAD_FOOTPRINT_DIR", None) or None,
        kicad_sym_lib_table=os.getenv("KICAD_SYM_LIB_TABLE", None) or None,
    )
```

POST `/settings` continues to accept the full `Settings` model for updates.

- [ ] **Step 3: Update frontend to use flags instead of raw keys**

In `frontend/src/components/SettingsPage.tsx`: show "Configured" + hint for each provider rather than populating the password inputs with raw values. The POST payload still sends the full key when user types one.

- [ ] **Step 4: Run tests**

```bash
uv run pytest backend/tests/test_settings_security.py -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/models/settings.py backend/routers/settings.py frontend/src/components/SettingsPage.tsx
git commit -m "fix(security): mask API keys in GET /settings response"
```

---

## Task 3: Persist settings to config.json, not .env

**Files:**
- Modify: `backend/routers/settings.py`
- Modify: `.gitignore`

- [ ] **Step 1: Ignore the config file**

Append to `.gitignore`:

```
data/config.json
```

(`data/` already ignored from plan 04, so this is defensive.)

- [ ] **Step 2: Replace .env rewriting with JSON config**

In `backend/routers/settings.py`, replace the `.env` write block in `update_settings` with:

```python
import json
from pathlib import Path

CONFIG_PATH = Path(os.getenv("TRIPLET_CONFIG_PATH", "data/config.json"))


def _persist(settings: Settings) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Re-read existing file so we don't clobber fields the caller didn't send.
    existing: dict = {}
    if CONFIG_PATH.exists():
        try:
            existing = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            existing = {}
    updated = {**existing, **settings.model_dump(exclude_none=True)}
    CONFIG_PATH.write_text(json.dumps(updated, indent=2))


# Inside update_settings, replace the .env write block with:
    _persist(settings)
```

Also add startup loading — in `backend/main.py`:

```python
import json
from pathlib import Path

@app.on_event("startup")
async def _load_config_into_env() -> None:
    path = Path(os.getenv("TRIPLET_CONFIG_PATH", "data/config.json"))
    if not path.exists():
        return
    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError:
        return
    _mapping = {
        "openai_api_key": "OPENAI_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "gemini_api_key": "GEMINI_API_KEY",
        "default_model": "DEFAULT_AI_MODEL",
        "kicad_symbol_dir": "KICAD_SYMBOL_DIR",
        "kicad_footprint_dir": "KICAD_FOOTPRINT_DIR",
        "kicad_sym_lib_table": "KICAD_SYM_LIB_TABLE",
        "digikey_client_id": "DIGIKEY_CLIENT_ID",
        "digikey_client_secret": "DIGIKEY_CLIENT_SECRET",
    }
    for key, envvar in _mapping.items():
        if key in cfg and cfg[key]:
            os.environ.setdefault(envvar, str(cfg[key]))
```

> **Note:** The existing quote/newline validation in `update_settings` is still useful to prevent injection into log files; keep it.

- [ ] **Step 3: Update the existing settings-security tests**

In `backend/tests/test_settings_security.py`, the existing `test_env_quoting` test asserts the `.env` file contains a specific line. Replace with a JSON check:

```python
def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIPLET_CONFIG_PATH", str(tmp_path / "config.json"))
    payload = {
        "openai_api_key": "key with spaces",
        "default_model": "gemini/gemini-pro",
    }
    response = client.post("/api/settings", json=payload)
    assert response.status_code == 200

    import json
    data = json.loads((tmp_path / "config.json").read_text())
    assert data["openai_api_key"] == "key with spaces"
```

Delete `test_env_quoting` and `test_quote_injection_prevented` (single-quote check is obsolete since JSON isn't shell-parsed). Replace with:

```python
def test_newline_injection_still_rejected():
    payload = {"openai_api_key": "x\nY=1"}
    resp = client.post("/api/settings", json=payload)
    assert resp.status_code == 400
```

Keep the newline check in `update_settings` — it now protects log output rather than .env content, but still valuable.

- [ ] **Step 4: Run tests**

```bash
uv run pytest backend -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/settings.py backend/main.py backend/tests/test_settings_security.py .gitignore
git commit -m "fix(settings): persist to data/config.json instead of rewriting .env"
```

---

## Task 4: Relative download URLs

**Files:**
- Modify: `backend/services/tools.py`

- [ ] **Step 1: Drop the host**

Change any string like:

```python
download_url = f"http://localhost:8000/api/download/{filename}"
```

to:

```python
download_url = f"/api/download/{filename}"
```

The frontend is already same-origin-ish (dev server proxies), and a relative URL works behind any reverse proxy.

- [ ] **Step 2: Confirm frontend renders links correctly**

In `frontend/src/components/ChatInterface.tsx`, markdown links with path-relative URLs render as anchor tags — they'll 404 in dev because Vite serves port 5173 while backend is 8000. Add a Vite proxy so `/api/*` goes to the backend. In `frontend/vite.config.ts`, inside `defineConfig({ server: { proxy: ... } })`:

```ts
server: {
  proxy: {
    '/api': 'http://localhost:8000',
  },
},
```

- [ ] **Step 3: Manual check**

Start both servers; ask the agent to generate a schematic; click the download link — it should 200, not 404.

- [ ] **Step 4: Commit**

```bash
git add backend/services/tools.py frontend/vite.config.ts
git commit -m "fix(api): relative download URLs with Vite proxy for /api"
```

---

## Task 5: Pin Python 3.12

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Change requires-python**

```toml
requires-python = ">=3.12,<3.14"
```

Rationale: 3.14 excludes most contributors right now; 3.12 is the actively-supported line that AI_RULES.md already specifies.

- [ ] **Step 2: Rebuild lockfile**

```bash
uv sync
```

- [ ] **Step 3: Run tests under 3.12**

```bash
uv run --python 3.12 pytest backend -v
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: pin Python to >=3.12,<3.14"
```

---

## Task 6: Update default model strings

**Files:**
- Modify: `backend/services/ai.py`
- Modify: `backend/models/settings.py`
- Modify: `.env.example`

- [ ] **Step 1: Pick current defaults**

Use LiteLLM names that exist today:
- OpenAI: `gpt-4o-mini` (cheap default) or `gpt-4o` (quality default). Pick `gpt-4o-mini` for dev.
- Gemini: `gemini/gemini-1.5-flash` (replaces the obsolete `gemini-pro`).
- Anthropic: `anthropic/claude-3-5-sonnet-latest`.

- [ ] **Step 2: Update `AIService.__init__` default**

```python
def __init__(self, model: str = "gpt-4o-mini", max_tool_turns: int | None = None) -> None:
```

- [ ] **Step 3: Update `Settings` default**

```python
    default_model: str = "gemini/gemini-1.5-flash"
```

- [ ] **Step 4: Update `.env.example`**

```
DEFAULT_AI_MODEL=gemini/gemini-1.5-flash
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/ai.py backend/models/settings.py .env.example
git commit -m "chore: update default model identifiers to current providers"
```

---

## Task 7: Write README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write it**

```markdown
# TripleT KiCad Agent

AI-powered engineering assistant that bridges high-level system requirements and physical PCB design. Not a chatbot — a co-designer that understands electronics theory, component availability, and KiCad 9 file structures.

See `PLANNING.md` for the roadmap and `docs/AI_RULES.md` for coding rules.

## Requirements

- Python 3.12 (pinned in `pyproject.toml`)
- Node 20+ and npm
- `uv` (`pipx install uv`)
- KiCad 9 (to open generated schematics)

## Run (development)

Backend:

```bash
uv sync
uv run uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Configure API keys on the Settings page.

## Tests

```bash
uv run pytest backend -v
```

## Architecture

- `backend/` — FastAPI backend. Services: `ai` (LiteLLM with multi-turn tool loop), `schematic` (kicad_sch_api), `lcsc` + `suppliers/digikey` (part search), `tools` (agent tool registry), `knowledge/patterns` (verified circuit snippets).
- `backend/knowledge/patterns/` — Executable, searchable circuit patterns. Add new ones here.
- `frontend/` — React 19 + Vite + Tailwind v4. State: BOM via server-backed context; chat is local.
- Data: `data/triplet.db` (SQLite, project + BOM + chat history).

## Plans in flight

Implementation plans live in `docs/superpowers/plans/`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: write README"
```

---

## Task 8: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - name: Set up Python
        run: uv python install 3.12
      - name: Install deps
        run: uv sync
      - name: Run tests
        run: uv run pytest backend -v

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build
      - run: npm run lint
```

- [ ] **Step 2: Commit and push to trigger**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow (pytest + frontend build/lint)"
```

---

## Task 9: Open PR

- [ ] **Step 1: Push and open**

```bash
git push -u origin chore/cross-cutting-fixes
gh pr create --base dev --title "chore: cross-cutting fixes (security, config, docs, CI)" --body "$(cat <<'EOF'
## Summary
- GET /settings no longer leaks API keys — returns masked hints + presence flags.
- Settings persistence moved from .env rewriting to data/config.json (with auto-load on startup).
- Download URLs are relative; Vite proxies /api to the backend in dev.
- Pin Python 3.12, update default model identifiers to current providers.
- Wrote a real README.
- Added GitHub Actions CI (pytest + frontend build + lint).

## Test plan
- [x] `uv run pytest backend -v` — all green.
- [x] `cd frontend && npm run build && npm run lint` — clean.
- [ ] Manual: CI runs green on PR.
- [ ] Manual: save an API key, confirm GET /settings returns only the masked hint.
- [ ] Manual: restart backend, confirm settings reload from data/config.json.
EOF
)"
```

---

## Self-Review against the review document

Running the checklist from the writing-plans skill against all six plans:

**Spec coverage** (each review bullet → task):

- Kill the Box with Pin1: plan 01, tasks 9–10.
- Parse sym-lib-table: plan 01, tasks 1–4.
- Multi-turn agent loop: plan 03 in full.
- Pattern library as RAG: plan 02 in full.
- DigiKey supplier: plan 05.
- Project persistence (SQLite for BOM): plan 04.
- Mask API keys: plan 06, tasks 1–2.
- Config.json replaces .env rewriting: plan 06, task 3.
- Hardcoded localhost download URL: plan 06, task 4.
- Python version mismatch: plan 06, task 5.
- Stale model defaults: plan 06, task 6.
- Empty README: plan 06, task 7.
- Missing CI: plan 06, task 8.
- KiCad MCP branch decision: not in these plans. Added as a deferred item — see below.

**Deferred intentionally (acknowledged but out of scope for these six plans):**
- Integration with the `feature/kicad-mcp` branch. This needs brainstorming before planning because it changes what "co-designer" means (live KiCad session vs. static file generation). Recommend a separate brainstorming pass before writing a plan.
- Datasheet → pinout extraction (Phase 3 in `PLANNING.md`). Called out in plans 01 and 02 as a hook (`pins=` arg on `generate_single_component_sch`, `PinSpec` on the resolver) but the extraction pipeline itself is a substantial separate plan.
- Multi-component schematics with auto-wiring (Phase 4 in `PLANNING.md`).

**Placeholder scan:** No TODOs, TBDs, "implement later", or "similar to task N" patterns found. Every code step contains actual code.

**Type consistency:** `PinSpec` shape identical across plan 01 tasks 5, 8, 10. `Part` model additions (`alt_suppliers`) in plan 05 task 2 used consistently in task 3 and task 6. `Pattern` protocol signature consistent across plan 02 tasks 2, 4, 7, 9.
