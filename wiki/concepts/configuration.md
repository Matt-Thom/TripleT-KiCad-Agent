---
title: Configuration — .env and the Settings Page
type: concept
tags: [config, env, settings]
created: 2026-04-24
updated: 2026-04-24
related_files: [.env.example, backend/routers/settings.py, backend/models/settings.py, frontend/src/components/SettingsPage.tsx]
---

All configuration is environment variables. There are two interfaces to the same storage: a `.env` file on disk, and a `/api/settings` UI. Both resolve via `os.environ` at runtime.

## Variables

### AI provider + loop

| Variable | Source | Consumer |
|---|---|---|
| `OPENAI_API_KEY` | `.env` / Settings | LiteLLM (OpenAI models) |
| `ANTHROPIC_API_KEY` | `.env` / Settings | LiteLLM (Claude models) |
| `GEMINI_API_KEY` | `.env` / Settings | LiteLLM (Gemini models) |
| `DEFAULT_AI_MODEL` | `.env` / Settings | [[entities/ai-service]], [[entities/pinout-extractor]] |
| `AI_MAX_TOOL_TURNS` | `.env` only | [[entities/ai-service]] |

Model strings follow LiteLLM conventions: `gpt-4o`, `anthropic/claude-sonnet-4-6`, `gemini/gemini-3-pro`, etc.

### KiCad library paths

| Variable | Consumer |
|---|---|
| `KICAD_SYM_LIB_TABLE` | `SchematicService` → `LibraryIndex.from_table()` — enables library symbol reuse. Absolute path. |
| `KICAD_SYMBOL_DIR` | Plumbed through the Settings model; not currently read by any service directly. |
| `KICAD_FOOTPRINT_DIR` | Same — persisted but unused today. |

### Not in `.env.example`

The file only lists AI keys and the two `AI_*` vars. The KiCad paths are exposed only via the Settings UI and are written to `.env` when the user saves them. If starting fresh from `.env.example`, the Settings page is the easier entry point.

## Write path

`POST /api/settings` (`backend/routers/settings.py`):

1. Update `os.environ` with the submitted values for the **running process**.
2. Rewrite `.env` so next startup picks the same values.

Step 1 is what makes changes take effect without a restart. Step 2 is what makes them survive one.

## Read path

Each service reads `os.environ.get("...")` when it needs a value. There is no central config object cached at import time — deliberate, so changes via the Settings page propagate without restart. Exception: `AIService` captures `DEFAULT_AI_MODEL` and `AI_MAX_TOOL_TURNS` at `__init__` because a module-level singleton (`ai_service`) is instantiated once at import. If you change these values via the Settings page, restart the backend to pick them up.

## If you add a new variable

1. Add it to `backend/models/settings.py` so it round-trips through the Settings router.
2. Decide: cache at service init (like `AI_MAX_TOOL_TURNS`) or read per-call (like `KICAD_SYM_LIB_TABLE`). Cache only if hot-path performance matters and you don't care about live reloading.
3. Document in [[overview]] and this page.
4. Add a representative entry to `.env.example` unless it's a secret default.
