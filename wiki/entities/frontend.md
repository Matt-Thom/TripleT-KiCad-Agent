---
title: Frontend
type: entity
tags: [react, vite, tailwind, typescript]
created: 2026-04-24
updated: 2026-04-24
related_files: [frontend/src/App.tsx, frontend/src/components/, frontend/src/context/BOMContext.tsx, frontend/vite.config.ts]
---

React 19 SPA in `frontend/`. Single-page, tab-switched layout (no router).

## Stack details

- **Build**: `rolldown-vite@7.2.5` aliased as `vite` via `package.json` overrides.
- **Language**: TypeScript 5.9 strict; `noUnusedLocals`, `noUnusedParameters`, ES2022 target.
- **Styling**: Tailwind v4 via `@tailwindcss/vite`. All styling is inline utility classes.
- **HTTP**: `axios`. All components hardcode `http://localhost:8000` as the backend base URL. `vite.config.ts` does *not* configure a proxy.
- **State**: one `BOMContext` (`frontend/src/context/BOMContext.tsx`). No Redux/Zustand/etc.

## Components

| File | Role |
|---|---|
| `main.tsx` | Entry; wraps `<App>` in `<BOMProvider>` + `<StrictMode>`. |
| `App.tsx` | `MainLayout` — tab switch (home / bom / settings), BOM-count badge on the cart icon. |
| `components/ChatInterface.tsx` | Chat UI. `POST /api/chat` with full message history. If BOM has items, injects a synthetic `system` message right before the last user turn summarising the BOM (mpn + description). Renders replies as Markdown. |
| `components/PartSearch.tsx` | `GET /api/search/lcsc?q=`. Per-result "Generate Schematic" (blob download) + "Add to BOM" (optimistically disabled after add). |
| `components/BOMPage.tsx` | Table view, per-row delete, client-side CSV export. **In-memory only** — reload wipes it. |
| `components/SettingsPage.tsx` | Bound to `GET`/`POST /api/settings`. Exposes API keys, default model, and KiCad library paths. |
| `context/BOMContext.tsx` | `items`, `addToBOM`, `removeFromBOM`. No persistence today. |
| `types/Part.ts` | Mirrors backend `Part` shape. |

## Running

```bash
cd frontend
npm install
npm run dev
```

Backend must be running on `:8000` independently.

## Known issues

- `ChatInterface.tsx` has a pre-existing untyped `catch (error: any)` at ~line 87 that trips strict type checking. Noted in README. Not addressed because it predates the recent feature branches.
- BOM is in-memory. PR #13 (draft) wires it to SQLite on the backend; frontend context also gets replaced with an API-backed version there.
- No test harness — no Jest/Vitest, no `@testing-library/react`.
