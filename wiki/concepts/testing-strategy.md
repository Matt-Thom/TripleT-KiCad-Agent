---
title: Testing Strategy
type: concept
tags: [tdd, pytest, testing]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/tests/, pyproject.toml]
---

All backend work on this project follows strict TDD. Frontend has no test harness today.

## Red/green commit discipline

Every feature lands as at least two commits:

1. `test: failing tests for <feature>` — tests only, verified to fail for the intended reason.
2. `feat(<scope>): <feature>` — implementation that turns them green.

Fixes and review iterations can bundle adjustments into a single commit, but the test-before-code shape is preserved. The commit history for Phase 2.5 (pattern library) and Phase 3 (datasheet + pinout) demonstrates this pattern.

## Layout

- `backend/tests/` — one `test_<module>.py` per production module, plus a few cross-cutting files (`test_security.py`, `test_injection.py`, `test_error_handling.py`).
- `backend/tests/fixtures/` — check-in fixtures (currently a `sym-lib-table` + one `.kicad_sym` for library resolver tests).
- `pyproject.toml` sets `pythonpath = ["."]` so `backend.*` imports resolve from the repo root.

## Running

```
uv run pytest backend/tests/
```

No CI yet — this runs locally. 67 tests pass as of 2026-04-24.

## Conventions

- **Hermetic fixtures.** `test_datasheet.py` builds minimal PDF bytes at runtime rather than checking in a binary — easier to reason about, no `git lfs` risk, dependency-free. Extend this pattern when possible.
- **Mock at boundaries, not internals.** For HTTP calls: mock `httpx.AsyncClient`. For LLM calls: mock `completion` on the *importing module* (e.g. `backend.services.pinout.completion`) so `monkeypatch.setattr` works cleanly.
- **Test the dispatcher, not just the service.** When adding a new tool, include a `test_tools.py`-style test that verifies tool registration (schema shape) and `execute_tool()` dispatch — not just the underlying service function. See `backend/tests/test_pinout.py` for the template.
- **Drop, don't explode, on bad data.** Several modules (pinout parsing, `_coerce_pins`) drop malformed entries and only raise when *all* entries fail. Test both the drop path and the all-fail path.

## Known gaps

- No frontend tests. React components are exercised only by manual use.
- No integration tests that spin up the real server.
- No coverage reporting configured.
