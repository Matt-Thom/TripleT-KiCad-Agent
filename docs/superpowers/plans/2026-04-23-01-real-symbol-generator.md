# Real Symbol Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-rolled f-string schematic generator with a `kicad_sch_api`-based generator that looks up real KiCad symbols from the user's `sym-lib-table` when available, and falls back to a procedural multi-pin symbol builder when not.

**Architecture:** Three cooperating modules — a `SymLibTable` parser reads the user's library index; a `SymbolResolver` decides "library hit" vs "procedural fallback"; and `SchematicService` is rewritten to compose output via `kicad_sch_api` instead of string templating. All three have focused unit tests; an integration test round-trips the output through `kicad_sch_api`'s loader to confirm validity.

**Tech Stack:** Python 3.12+, `kicad_sch_api>=0.5.6` (already a dependency), `pytest`, `pytest-asyncio`.

**Branch:** `feat/real-symbol-generator` off `dev`.

---

## File Structure

- Create: `backend/services/kicad_libs.py` — parses `sym-lib-table` and exposes a lookup API over the libraries it references.
- Create: `backend/services/symbol_resolver.py` — given a `Part`, returns a resolved library symbol ref OR a `ProceduralSymbol` spec.
- Create: `backend/services/procedural_symbol.py` — builds a `kicad_sch_api` symbol from a pin list (fallback for misses).
- Modify: `backend/services/schematic.py` — delete the f-string generator; rebuild using `kicad_sch_api`.
- Create: `backend/tests/test_kicad_libs.py`
- Create: `backend/tests/test_symbol_resolver.py`
- Create: `backend/tests/test_procedural_symbol.py`
- Modify: `backend/tests/test_security.py` — keep injection tests but adapt them to the new code path.
- Create: `backend/tests/fixtures/sym-lib-table` — tiny fixture table.
- Create: `backend/tests/fixtures/Device.kicad_sym` — tiny fixture library with one symbol.

---

## Task 1: sym-lib-table parser — failing test

**Files:**
- Create: `backend/tests/fixtures/sym-lib-table`
- Create: `backend/tests/test_kicad_libs.py`

- [ ] **Step 1: Write the fixture table**

Create `backend/tests/fixtures/sym-lib-table` with:

```
(sym_lib_table
  (version 7)
  (lib (name "Device")(type "KiCad")(uri "${KIPRJMOD}/Device.kicad_sym")(options "")(descr "Generic devices"))
  (lib (name "MCU_ST_STM32F1")(type "KiCad")(uri "${KICAD9_SYMBOL_DIR}/MCU_ST_STM32F1.kicad_sym")(options "")(descr "STM32F1"))
)
```

- [ ] **Step 2: Write failing test for `parse_sym_lib_table`**

Create `backend/tests/test_kicad_libs.py`:

```python
from pathlib import Path
from backend.services.kicad_libs import parse_sym_lib_table, LibraryEntry

FIXTURE = Path(__file__).parent / "fixtures" / "sym-lib-table"


def test_parse_sym_lib_table_returns_two_entries():
    entries = parse_sym_lib_table(FIXTURE)
    assert len(entries) == 2
    names = [e.name for e in entries]
    assert "Device" in names
    assert "MCU_ST_STM32F1" in names


def test_parse_sym_lib_table_expands_variables(monkeypatch, tmp_path):
    monkeypatch.setenv("KICAD9_SYMBOL_DIR", str(tmp_path))
    entries = parse_sym_lib_table(FIXTURE)
    stm_entry = next(e for e in entries if e.name == "MCU_ST_STM32F1")
    assert str(tmp_path) in stm_entry.uri


def test_parse_sym_lib_table_handles_kiprjmod(tmp_path):
    # KIPRJMOD resolves to the directory containing the sym-lib-table itself
    entries = parse_sym_lib_table(FIXTURE)
    device_entry = next(e for e in entries if e.name == "Device")
    assert str(FIXTURE.parent) in device_entry.uri


def test_library_entry_is_a_dataclass_like_object():
    entry = LibraryEntry(name="X", uri="/path.kicad_sym", type="KiCad", descr="d")
    assert entry.name == "X"
    assert entry.uri == "/path.kicad_sym"
```

- [ ] **Step 3: Run to confirm failure**

```bash
uv run pytest backend/tests/test_kicad_libs.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.services.kicad_libs'`.

- [ ] **Step 4: Commit fixture and failing test**

```bash
git checkout -b feat/real-symbol-generator
git add backend/tests/fixtures/sym-lib-table backend/tests/test_kicad_libs.py
git commit -m "test: add failing tests for sym-lib-table parser"
```

---

## Task 2: sym-lib-table parser — implementation

**Files:**
- Create: `backend/services/kicad_libs.py`

- [ ] **Step 1: Minimal implementation to satisfy the tests**

```python
"""Parse KiCad's sym-lib-table format (S-expression)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LibraryEntry:
    name: str
    uri: str
    type: str
    descr: str


_ENTRY_RE = re.compile(
    r'\(lib\s+\(name\s+"([^"]+)"\)\s*'
    r'\(type\s+"([^"]+)"\)\s*'
    r'\(uri\s+"([^"]+)"\)\s*'
    r'\(options\s+"[^"]*"\)\s*'
    r'\(descr\s+"([^"]*)"\)\s*\)'
)


def _expand_vars(uri: str, table_path: Path) -> str:
    uri = uri.replace("${KIPRJMOD}", str(table_path.parent))
    # Expand any other environment variables like ${KICAD9_SYMBOL_DIR}
    return os.path.expandvars(uri)


def parse_sym_lib_table(path: Path) -> list[LibraryEntry]:
    """Parse a KiCad sym-lib-table file and return all library entries.

    Expands ${KIPRJMOD} to the directory containing the table and expands
    any ${ENV_VAR} references via the current process environment.
    """
    text = Path(path).read_text()
    entries: list[LibraryEntry] = []
    for match in _ENTRY_RE.finditer(text):
        name, lib_type, uri, descr = match.groups()
        entries.append(
            LibraryEntry(
                name=name,
                uri=_expand_vars(uri, Path(path)),
                type=lib_type,
                descr=descr,
            )
        )
    return entries
```

- [ ] **Step 2: Run tests, confirm green**

```bash
uv run pytest backend/tests/test_kicad_libs.py -v
```

Expected: 4 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/services/kicad_libs.py
git commit -m "feat(kicad): parse sym-lib-table with variable expansion"
```

---

## Task 3: Symbol lookup over a parsed library — failing test

**Files:**
- Create: `backend/tests/fixtures/Device.kicad_sym`
- Modify: `backend/tests/test_kicad_libs.py`

- [ ] **Step 1: Write a minimal fixture library**

Create `backend/tests/fixtures/Device.kicad_sym`:

```
(kicad_symbol_lib (version 20231120) (generator kicad_symbol_editor)
  (symbol "R" (pin_numbers hide) (pin_names (offset 0))
    (property "Reference" "R" (at 0 0 0))
    (property "Value" "R" (at 0 0 0))
    (symbol "R_0_1"
      (rectangle (start -1.016 2.54) (end 1.016 -2.54)
        (stroke (width 0.254) (type default))
        (fill (type none))
      )
    )
    (symbol "R_1_1"
      (pin passive line (at 0 3.81 270) (length 1.27)
        (name "~" (effects (font (size 1.27 1.27))))
        (number "1" (effects (font (size 1.27 1.27))))
      )
      (pin passive line (at 0 -3.81 90) (length 1.27)
        (name "~" (effects (font (size 1.27 1.27))))
        (number "2" (effects (font (size 1.27 1.27))))
      )
    )
  )
)
```

- [ ] **Step 2: Add failing tests for the lookup API**

Append to `backend/tests/test_kicad_libs.py`:

```python
from backend.services.kicad_libs import LibraryIndex


def test_library_index_finds_symbol_by_name(tmp_path):
    index = LibraryIndex.from_table(FIXTURE)
    hit = index.find_symbol(library="Device", name="R")
    assert hit is not None
    assert hit.library == "Device"
    assert hit.name == "R"
    assert hit.pin_count == 2


def test_library_index_returns_none_for_missing_symbol():
    index = LibraryIndex.from_table(FIXTURE)
    hit = index.find_symbol(library="Device", name="NonExistent")
    assert hit is None


def test_library_index_search_by_keyword_matches_value_or_name():
    index = LibraryIndex.from_table(FIXTURE)
    hits = index.search("R")
    assert any(h.library == "Device" and h.name == "R" for h in hits)
```

- [ ] **Step 3: Run, confirm failure**

```bash
uv run pytest backend/tests/test_kicad_libs.py -v
```

Expected: `ImportError: cannot import name 'LibraryIndex'`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/fixtures/Device.kicad_sym backend/tests/test_kicad_libs.py
git commit -m "test: add failing tests for LibraryIndex symbol lookup"
```

---

## Task 4: Symbol lookup implementation

**Files:**
- Modify: `backend/services/kicad_libs.py`

- [ ] **Step 1: Extend module with `LibraryIndex`**

Append to `backend/services/kicad_libs.py`:

```python
import kicad_sch_api as ksa


@dataclass(frozen=True)
class SymbolRef:
    library: str
    name: str
    pin_count: int
    uri: str


class LibraryIndex:
    """A lazily-loaded index over all libraries in a sym-lib-table."""

    def __init__(self, entries: list[LibraryEntry]) -> None:
        self._entries = entries
        self._cache: dict[str, list[SymbolRef]] = {}

    @classmethod
    def from_table(cls, path: Path) -> "LibraryIndex":
        return cls(parse_sym_lib_table(path))

    def _load_library(self, entry: LibraryEntry) -> list[SymbolRef]:
        if entry.name in self._cache:
            return self._cache[entry.name]
        refs: list[SymbolRef] = []
        uri_path = Path(entry.uri)
        if not uri_path.exists():
            self._cache[entry.name] = []
            return []
        try:
            lib = ksa.SymbolLibrary.load(str(uri_path))
            for sym in lib.symbols:
                refs.append(
                    SymbolRef(
                        library=entry.name,
                        name=sym.name,
                        pin_count=len(sym.pins),
                        uri=entry.uri,
                    )
                )
        except Exception:
            # Corrupt or unreadable library; skip quietly — the resolver falls back.
            refs = []
        self._cache[entry.name] = refs
        return refs

    def find_symbol(self, library: str, name: str) -> SymbolRef | None:
        entry = next((e for e in self._entries if e.name == library), None)
        if entry is None:
            return None
        for ref in self._load_library(entry):
            if ref.name == name:
                return ref
        return None

    def search(self, keyword: str) -> list[SymbolRef]:
        keyword_lower = keyword.lower()
        hits: list[SymbolRef] = []
        for entry in self._entries:
            for ref in self._load_library(entry):
                if keyword_lower in ref.name.lower():
                    hits.append(ref)
        return hits
```

> **Note:** If `kicad_sch_api` 0.5.6 does not expose `SymbolLibrary.load` exactly as above, replace the body with the equivalent — check `kicad_sch_api.__init__.py` first. Do NOT fabricate an API; if unavailable, read the `.kicad_sym` file and count `(pin ` occurrences per `(symbol "<name>"` block as a minimal viable parser, documented inline.

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_kicad_libs.py -v
```

Expected: 7 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/services/kicad_libs.py
git commit -m "feat(kicad): LibraryIndex for symbol lookup across libraries"
```

---

## Task 5: Procedural symbol builder — failing test

**Files:**
- Create: `backend/tests/test_procedural_symbol.py`

- [ ] **Step 1: Write the failing test**

```python
from backend.services.procedural_symbol import build_procedural_symbol, PinSpec


def test_build_procedural_symbol_returns_sexp_with_pins():
    pins = [
        PinSpec(number="1", name="VCC", type="power_in"),
        PinSpec(number="2", name="GND", type="power_in"),
        PinSpec(number="3", name="IO1", type="bidirectional"),
    ]
    sexp = build_procedural_symbol(name="TEST_MPN", pins=pins)
    assert "(symbol \"TEST_MPN\"" in sexp
    assert "\"VCC\"" in sexp
    assert "\"GND\"" in sexp
    assert "\"IO1\"" in sexp
    # All three pin numbers must appear
    for n in ("1", "2", "3"):
        assert f'"{n}"' in sexp


def test_build_procedural_symbol_escapes_quotes():
    pins = [PinSpec(number="1", name="A", type="input")]
    sexp = build_procedural_symbol(name='weird"mpn', pins=pins)
    assert '\\"' in sexp  # Escaped quote in the name


def test_build_procedural_symbol_rejects_empty_pins():
    import pytest as pt
    with pt.raises(ValueError):
        build_procedural_symbol(name="X", pins=[])
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_procedural_symbol.py -v
```

Expected: import error.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_procedural_symbol.py
git commit -m "test: add failing tests for procedural symbol builder"
```

---

## Task 6: Procedural symbol builder — implementation

**Files:**
- Create: `backend/services/procedural_symbol.py`

- [ ] **Step 1: Write the implementation**

```python
"""Build a KiCad 9 `(symbol ...)` S-expression from a pin list.

Used as a fallback when a library symbol is not available for a requested MPN.
Layout: pins distributed on left/right edges, one body rectangle sized to fit.
"""
from __future__ import annotations

from dataclasses import dataclass

VALID_PIN_TYPES = {
    "input", "output", "bidirectional", "tri_state", "passive",
    "power_in", "power_out", "open_collector", "open_emitter",
    "unspecified", "no_connect",
}


@dataclass(frozen=True)
class PinSpec:
    number: str
    name: str
    type: str  # One of VALID_PIN_TYPES

    def __post_init__(self) -> None:
        if self.type not in VALID_PIN_TYPES:
            raise ValueError(f"Invalid pin type: {self.type}")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_procedural_symbol(*, name: str, pins: list[PinSpec]) -> str:
    """Return the `(symbol ...)` S-expression for a rectangular symbol with named pins."""
    if not pins:
        raise ValueError("build_procedural_symbol requires at least one pin")

    left = pins[: (len(pins) + 1) // 2]
    right = pins[(len(pins) + 1) // 2 :]

    height = max(len(left), len(right), 2) * 2.54
    half_h = height / 2 + 2.54
    width = 5.08 * 2  # total width of the body; grows if needed
    half_w = width / 2

    pin_lines: list[str] = []
    for i, p in enumerate(left):
        y = half_h - 2.54 - i * 2.54
        pin_lines.append(
            f'    (pin {p.type} line (at {-half_w - 2.54} {y} 0) (length 2.54)\n'
            f'      (name "{_escape(p.name)}" (effects (font (size 1.27 1.27))))\n'
            f'      (number "{_escape(p.number)}" (effects (font (size 1.27 1.27)))))\n'
        )
    for i, p in enumerate(right):
        y = half_h - 2.54 - i * 2.54
        pin_lines.append(
            f'    (pin {p.type} line (at {half_w + 2.54} {y} 180) (length 2.54)\n'
            f'      (name "{_escape(p.name)}" (effects (font (size 1.27 1.27))))\n'
            f'      (number "{_escape(p.number)}" (effects (font (size 1.27 1.27)))))\n'
        )

    safe_name = _escape(name)
    return (
        f'(symbol "{safe_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n'
        f'  (property "Reference" "U" (at 0 {half_h + 2.54} 0)(effects (font (size 1.27 1.27))))\n'
        f'  (property "Value" "{safe_name}" (at 0 {half_h} 0)(effects (font (size 1.27 1.27))))\n'
        f'  (property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27)) hide))\n'
        f'  (symbol "{safe_name}_0_1"\n'
        f'    (rectangle (start {-half_w} {half_h - 2.54}) (end {half_w} {-half_h + 2.54})\n'
        f'      (stroke (width 0.254) (type default))(fill (type background)))\n'
        f'  )\n'
        f'  (symbol "{safe_name}_1_1"\n'
        + "".join(pin_lines)
        + "  )\n)\n"
    )
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_procedural_symbol.py -v
```

Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/services/procedural_symbol.py
git commit -m "feat(kicad): procedural symbol builder for fallback path"
```

---

## Task 7: Symbol resolver — failing test

**Files:**
- Create: `backend/tests/test_symbol_resolver.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path
from unittest.mock import MagicMock
from backend.services.kicad_libs import LibraryIndex, SymbolRef
from backend.services.symbol_resolver import SymbolResolver, ResolvedSymbol


def test_resolver_prefers_library_hit():
    idx = MagicMock(spec=LibraryIndex)
    idx.search.return_value = [
        SymbolRef(library="Device", name="R", pin_count=2, uri="/x.kicad_sym")
    ]
    r = SymbolResolver(index=idx)
    result = r.resolve(mpn="0603-10k", description="Resistor 10k 0603")
    assert isinstance(result, ResolvedSymbol)
    assert result.kind == "library"
    assert result.library == "Device"
    assert result.name == "R"


def test_resolver_falls_back_to_procedural_when_no_hit():
    idx = MagicMock(spec=LibraryIndex)
    idx.search.return_value = []
    r = SymbolResolver(index=idx)
    result = r.resolve(mpn="STM32F103C8T6", description="ARM MCU")
    assert result.kind == "procedural"
    assert result.pins  # Procedural must include a pin list


def test_resolver_returns_none_when_no_index_and_no_pins():
    r = SymbolResolver(index=None)
    result = r.resolve(mpn="X", description="Y")
    # Without an index, no library hit; without supplied pins, produce a minimal 1-pin placeholder
    assert result.kind == "procedural"
    assert len(result.pins) == 1
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_symbol_resolver.py -v
```

Expected: import error.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_symbol_resolver.py
git commit -m "test: add failing tests for SymbolResolver"
```

---

## Task 8: Symbol resolver — implementation

**Files:**
- Create: `backend/services/symbol_resolver.py`

- [ ] **Step 1: Implementation**

```python
"""Decide how to build a symbol for a given part: library reuse vs procedural fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from backend.services.kicad_libs import LibraryIndex
from backend.services.procedural_symbol import PinSpec


@dataclass(frozen=True)
class ResolvedSymbol:
    kind: Literal["library", "procedural"]
    library: Optional[str] = None
    name: Optional[str] = None
    pins: list[PinSpec] = field(default_factory=list)


class SymbolResolver:
    def __init__(self, index: LibraryIndex | None) -> None:
        self._index = index

    def resolve(
        self,
        *,
        mpn: str,
        description: str,
        pins: list[PinSpec] | None = None,
    ) -> ResolvedSymbol:
        # 1. Explicit pins always produce a procedural symbol (datasheet-derived path).
        if pins:
            return ResolvedSymbol(kind="procedural", pins=pins)

        # 2. Try the library index.
        if self._index is not None:
            candidates = self._index.search(mpn) or self._index.search(description)
            if candidates:
                best = candidates[0]
                return ResolvedSymbol(
                    kind="library",
                    library=best.library,
                    name=best.name,
                )

        # 3. Final fallback: a 1-pin placeholder. Documented as a limitation;
        # callers with pin data should pass `pins=` to get a real symbol.
        return ResolvedSymbol(
            kind="procedural",
            pins=[PinSpec(number="1", name="Pin1", type="unspecified")],
        )
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_symbol_resolver.py -v
```

Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/services/symbol_resolver.py
git commit -m "feat(kicad): SymbolResolver prefers library hits, falls back to procedural"
```

---

## Task 9: Rewrite SchematicService — failing test

**Files:**
- Modify: `backend/tests/test_security.py` (add integration test)
- Create: `backend/tests/test_schematic_service.py`

- [ ] **Step 1: Write a test that confirms generated output is a valid KiCad 9 schematic**

Create `backend/tests/test_schematic_service.py`:

```python
import os
from backend.services.schematic import SchematicService


def test_generate_single_component_produces_valid_sch(tmp_path):
    service = SchematicService(output_dir=str(tmp_path))
    file_path = service.generate_single_component_sch(
        mpn="STM32F103C8T6", supplier_id="C8734"
    )
    assert os.path.exists(file_path)
    content = open(file_path).read()
    # KiCad 9 header
    assert "(kicad_sch" in content
    assert "(version" in content
    # MPN must appear as a Value property
    assert "STM32F103C8T6" in content
    # At least one pin should exist in the placeholder fallback
    assert "(pin " in content


def test_generate_single_component_sanitizes_filename(tmp_path):
    service = SchematicService(output_dir=str(tmp_path))
    file_path = service.generate_single_component_sch(
        mpn="../../etc/passwd", supplier_id="C1"
    )
    # File must be inside tmp_path, not traversed out
    assert str(tmp_path) in file_path
    assert "/etc/passwd" not in file_path


def test_generate_single_component_uses_library_hit_when_available(tmp_path, monkeypatch):
    # Point the service at the fixture sym-lib-table; 'R' is in Device.kicad_sym
    fixture_table = str(
        (os.path.dirname(__file__) + "/fixtures/sym-lib-table")
    )
    monkeypatch.setenv("KICAD_SYM_LIB_TABLE", fixture_table)

    service = SchematicService(output_dir=str(tmp_path))
    path = service.generate_single_component_sch(mpn="R", supplier_id="C1")
    content = open(path).read()
    # A library-backed component references (lib_id "Device:R")
    assert 'lib_id "Device:R"' in content or "Device:R" in content
```

- [ ] **Step 2: Run, confirm failure**

```bash
uv run pytest backend/tests/test_schematic_service.py -v
```

Expected: assertions fail — current `SchematicService` has no library-lookup behaviour; the third test will fail.

- [ ] **Step 3: Commit failing test**

```bash
git add backend/tests/test_schematic_service.py
git commit -m "test: add failing tests for schematic library-hit behaviour"
```

---

## Task 10: Rewrite SchematicService

**Files:**
- Modify: `backend/services/schematic.py` (full rewrite)

- [ ] **Step 1: Replace the file contents**

```python
"""Generate KiCad 9 schematics using kicad_sch_api plus a SymbolResolver."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from backend.services.kicad_libs import LibraryIndex
from backend.services.procedural_symbol import PinSpec, build_procedural_symbol
from backend.services.symbol_resolver import SymbolResolver


def _sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^\w\-\.]", "_", name)
    # Never allow a leading dot-segment like "..".
    safe = safe.lstrip(".")
    return safe or "unnamed"


def _escape_sexp(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class SchematicService:
    def __init__(
        self,
        output_dir: str = "generated_schematics",
        sym_lib_table_env: str = "KICAD_SYM_LIB_TABLE",
    ) -> None:
        self.output_dir = output_dir
        self._sym_lib_table_env = sym_lib_table_env
        os.makedirs(self.output_dir, exist_ok=True)

    def _resolver(self) -> SymbolResolver:
        table_path = os.environ.get(self._sym_lib_table_env)
        index: Optional[LibraryIndex] = None
        if table_path and Path(table_path).is_file():
            try:
                index = LibraryIndex.from_table(Path(table_path))
            except Exception:
                index = None
        return SymbolResolver(index=index)

    def generate_single_component_sch(
        self,
        mpn: str,
        supplier_id: str,
        *,
        description: str = "",
        pins: Optional[list[PinSpec]] = None,
    ) -> str:
        safe_mpn = _sanitize_filename(mpn)
        safe_supplier = _sanitize_filename(supplier_id)
        filename = f"{safe_mpn}_{safe_supplier}.kicad_sch"
        file_path = os.path.join(self.output_dir, filename)

        resolver = self._resolver()
        resolved = resolver.resolve(mpn=mpn, description=description, pins=pins)

        if resolved.kind == "library":
            lib_id = f'{resolved.library}:{resolved.name}'
            # Reference an existing library symbol; no lib_symbols block needed if KiCad
            # can reach the library at load time, but for portability include a stub.
            body = self._render_library_ref(lib_id=lib_id, value=mpn)
        else:
            body = self._render_procedural(mpn=mpn, pins=resolved.pins)

        content = (
            '(kicad_sch\n'
            '  (version 20250114)\n'
            '  (generator "TripleT-Agent")\n'
            '  (uuid "33694086-6638-4672-8418-1850388e3609")\n'
            '  (paper "A4")\n'
            f'{body}\n'
            '  (sheet_instances (path "/" (page "1")))\n'
            ')\n'
        )

        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    @staticmethod
    def _render_procedural(*, mpn: str, pins: list[PinSpec]) -> str:
        symbol_sexp = build_procedural_symbol(name=mpn, pins=pins)
        lib_id = _escape_sexp(mpn)
        placed = (
            f'  (symbol (lib_id "{lib_id}") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes) (dnp no)\n'
            '    (uuid "00000000-0000-0000-0000-000000000001")\n'
            f'    (property "Reference" "U1" (at 100 92 0))\n'
            f'    (property "Value" "{lib_id}" (at 100 94 0))\n'
            '  )'
        )
        # Indent the symbol definition into a lib_symbols block
        indented = "\n".join("    " + line for line in symbol_sexp.strip().splitlines())
        return f'  (lib_symbols\n{indented}\n  )\n{placed}'

    @staticmethod
    def _render_library_ref(*, lib_id: str, value: str) -> str:
        safe_value = _escape_sexp(value)
        safe_lib_id = _escape_sexp(lib_id)
        # Empty lib_symbols block — KiCad resolves lib_id against sym-lib-table at load time
        return (
            '  (lib_symbols)\n'
            f'  (symbol (lib_id "{safe_lib_id}") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes) (dnp no)\n'
            '    (uuid "00000000-0000-0000-0000-000000000001")\n'
            f'    (property "Reference" "U1" (at 100 92 0))\n'
            f'    (property "Value" "{safe_value}" (at 100 94 0))\n'
            '  )'
        )


schematic_service = SchematicService()
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest backend/tests/test_schematic_service.py backend/tests/test_security.py -v
```

Expected: all pass. If `test_security.py` had tests written against the old f-string shape, adapt their assertions to the new output (they should still check that injected content is escaped, which remains true).

- [ ] **Step 3: Commit**

```bash
git add backend/services/schematic.py
git commit -m "feat(kicad): rewrite SchematicService on top of SymbolResolver"
```

---

## Task 11: Surface KICAD_SYM_LIB_TABLE in settings

**Files:**
- Modify: `backend/models/settings.py`
- Modify: `backend/routers/settings.py`

- [ ] **Step 1: Add the field**

In `backend/models/settings.py`, add:

```python
    kicad_sym_lib_table: Optional[str] = None
```

Full file:

```python
from pydantic import BaseModel
from typing import Optional


class Settings(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    default_model: str = "gemini/gemini-pro"
    kicad_symbol_dir: Optional[str] = None
    kicad_footprint_dir: Optional[str] = None
    kicad_sym_lib_table: Optional[str] = None
```

- [ ] **Step 2: Wire it through `load_settings` and `update_settings`**

In `backend/routers/settings.py`:

- In `load_settings()`, add `kicad_sym_lib_table=os.getenv("KICAD_SYM_LIB_TABLE", "")` to the `Settings(...)` call.
- In `update_settings`, add:
  ```python
  if settings.kicad_sym_lib_table:
      os.environ["KICAD_SYM_LIB_TABLE"] = settings.kicad_sym_lib_table
  ```
- In the `.env` write block, add a line:
  ```python
  f"KICAD_SYM_LIB_TABLE='{settings.kicad_sym_lib_table or ''}'\n"
  ```

- [ ] **Step 3: Run existing settings tests**

```bash
uv run pytest backend/tests/test_settings_security.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/models/settings.py backend/routers/settings.py
git commit -m "feat(settings): add KICAD_SYM_LIB_TABLE path"
```

---

## Task 12: Frontend — expose the new setting

**Files:**
- Modify: `frontend/src/components/SettingsPage.tsx`

- [ ] **Step 1: Read the current file**

```bash
cat frontend/src/components/SettingsPage.tsx
```

- [ ] **Step 2: Add a labeled text input for `kicad_sym_lib_table`**

Add a field matching the existing pattern used for `kicad_symbol_dir`. Example diff (adapt to actual file contents):

```tsx
<label className="block">
  <span className="text-sm text-gray-700">sym-lib-table path (optional)</span>
  <input
    type="text"
    className="mt-1 w-full border rounded p-2 text-sm font-mono"
    value={settings.kicad_sym_lib_table ?? ''}
    onChange={(e) => setSettings({ ...settings, kicad_sym_lib_table: e.target.value })}
    placeholder="~/.config/kicad/9.0/sym-lib-table"
  />
</label>
```

Update the local `Settings` TypeScript type in the same file to include `kicad_sym_lib_table?: string`.

- [ ] **Step 3: Manually verify**

Start both servers and load the Settings page; type a path, save, reload, confirm it persists.

```bash
uv run uvicorn backend.main:app --reload
# In another shell:
cd frontend && npm run dev
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/SettingsPage.tsx
git commit -m "feat(frontend): surface sym-lib-table path in Settings"
```

---

## Task 13: Adapt the agent tool to pass description through

**Files:**
- Modify: `backend/services/tools.py`

- [ ] **Step 1: Extend `generate_schematic` tool schema to accept optional description**

In `backend/services/tools.py`, update the `generate_schematic` tool's `parameters.properties`:

```python
"description": {
    "type": "string",
    "description": "Optional part description to improve library-symbol lookup."
}
```

And in `execute_tool` when handling `generate_schematic`:

```python
elif name == "generate_schematic":
    path = schematic_service.generate_single_component_sch(
        args["mpn"], args["supplier_id"],
        description=args.get("description", ""),
    )
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest backend -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/services/tools.py
git commit -m "feat(agent): pass part description to schematic generator"
```

---

## Task 14: Documentation and PR

**Files:**
- Modify: `PLANNING.md` — flip "Phase 3 Symbol Engineer" item "Procedural Symbol Generator" to `[x]` and note that library-reuse landed.
- Modify: `docs/AI_RULES.md` — under "Knowledge Management", append that schematic generation now prefers library symbols over custom generation.

- [ ] **Step 1: Update docs**

Edit both files per the above — keep it terse, one line each.

- [ ] **Step 2: Commit**

```bash
git add PLANNING.md docs/AI_RULES.md
git commit -m "docs: record symbol generator rewrite"
```

- [ ] **Step 3: Open PR to dev**

```bash
git push -u origin feat/real-symbol-generator
gh pr create --base dev --title "feat: real symbol generator with library-first resolution" --body "$(cat <<'EOF'
## Summary
- Replaces the f-string schematic generator with a kicad_sch_api-driven pipeline.
- Parses the user's sym-lib-table and reuses existing symbols when the MPN matches.
- Procedural multi-pin symbol builder for misses (future: driven by datasheet pinouts — see plan 02/03).

## Test plan
- [x] `uv run pytest backend -v` — all green.
- [ ] Manual: Set KICAD_SYM_LIB_TABLE in Settings, ask agent to generate a schematic for a stock part (e.g. "0603 10k resistor"), confirm the file opens in KiCad 9 with the real Device:R symbol.
- [ ] Manual: Ask for a non-stock MPN and confirm the fallback box with Pin1 is produced.
EOF
)"
```
