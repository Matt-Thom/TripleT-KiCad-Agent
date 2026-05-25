---
title: SchematicService — .kicad_sch emission
type: entity
tags: [kicad, schematic, s-expression]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/services/schematic.py, backend/services/symbol_resolver.py, backend/services/procedural_symbol.py, backend/services/kicad_libs.py]
---

Writes KiCad 9 `.kicad_sch` files directly as S-expressions (`version 20250114`). Does **not** use `kicad_sch_api` for the single-component path — that library's library loading is too unreliable for our needs. `kicad_sch_api` is only used inside [[entities/pattern-library]] `apply()` callbacks.

## Two outputs

- `generate_single_component_sch(mpn, supplier_id, *, description, pins)` — one-component schematic. Filename is `{safe_mpn}_{safe_supplier}.kicad_sch` under `generated_schematics/` (`backend/services/schematic.py:51`).
- `apply_pattern(pattern_id, inputs)` — applies a pattern and saves the result. Filename is `{safe_pattern_id}.kicad_sch` (`backend/services/schematic.py:90`).

## Symbol sourcing — three paths

See [[concepts/symbol-resolution]] for the precedence rules. The three resulting branches:

1. **Library reference** (`_render_library_ref`, line 123). Emits an empty `(lib_symbols)` block and a `(symbol (lib_id "lib:name") ...)` placement. KiCad resolves the `lib_id` via the user's `sym-lib-table` at load time.
2. **Procedural symbol from explicit pins** (`_render_procedural`, line 107 + `procedural_symbol.build_procedural_symbol`). Draws a rectangle with pins distributed left/right, typed (power_in, output, etc.), using `PinSpec` entries.
3. **1-pin placeholder** — same code path as (2) with a single `unspecified` pin named `Pin1`, emitted when neither library match nor explicit pins are available.

## SymbolResolver

`backend/services/symbol_resolver.py:23`. Returns a `ResolvedSymbol(kind, library?, name?, pins)`. `kind` is `"library"` or `"procedural"`. The precedence is explicit in `resolve()`:

1. If `pins` is non-empty → procedural (even if a library match exists — explicit pin data is authoritative).
2. Else try `LibraryIndex.search(mpn)`, then `LibraryIndex.search(description)`.
3. Else fall back to the 1-pin placeholder.

## LibraryIndex — sym-lib-table parsing

`backend/services/kicad_libs.py` hand-rolls a regex parser for `sym-lib-table` and the referenced `.kicad_sym` files. Reason: `kicad_sch_api`'s own `_load_library()` is a stub (see commit history) — its internal loader doesn't actually parse library files. The regex approach is brittle to malformed input but sufficient for standard KiCad-generated libraries.

`LibraryIndex.from_table(path)` expands environment variables embedded in library paths (KiCad convention: `${KICAD8_SYMBOL_DIR}/...`) before scanning.

## Escaping

`_escape_sexp` (`backend/services/schematic.py:21`) handles backslashes, double quotes, null bytes, and newlines. The procedural symbol builder has its own identical `_escape` for pin names/numbers. Do not let user-controlled strings reach raw S-expression output — always route through these helpers.

## Output directory

`generated_schematics/` is created on service init (`backend/services/schematic.py:39`). The path is relative to the process CWD; starting the server from elsewhere breaks downloads. The download route (`backend/main.py:101`) uses `os.path.abspath("generated_schematics")` from the same CWD, so they're consistent.
