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


# ---------------------------------------------------------------------------
# LibraryIndex — lazily parsed index over a sym-lib-table
# ---------------------------------------------------------------------------
# kicad_sch_api 0.5.6 ships SymbolLibraryCache but its _load_library() is a
# stub that never parses the .kicad_sym file (returns empty results).
# We therefore use a minimal regex-based parser (_parse_kicad_sym) that:
#   1. Identifies top-level symbol blocks (skipping sub-unit names like R_0_1)
#   2. Counts `(pin ...)` occurrences within each block via bracket tracking
# ---------------------------------------------------------------------------

_TOP_SYMBOL_RE = re.compile(r'\(symbol\s+"([^"]+)"')
_SUBSYMBOL_RE = re.compile(r'^.+_\d+_\d+$')
_PIN_RE = re.compile(r'\(pin\s+\w+')


def _parse_kicad_sym(path: Path) -> list[tuple[str, int]]:
    """Minimal parser: returns list of (symbol_name, pin_count) for top-level symbols.

    Top-level symbols are direct children of the kicad_symbol_lib root — i.e.,
    their name does NOT match the sub-unit pattern ``<Name>_<N>_<M>``.
    Pins are counted by finding each top-level symbol's bracket-balanced block
    and scanning for ``(pin <type>`` occurrences within it.
    """
    text = path.read_text()
    results: list[tuple[str, int]] = []
    n = len(text)

    for m in _TOP_SYMBOL_RE.finditer(text):
        name = m.group(1)
        if _SUBSYMBOL_RE.match(name):
            continue

        # Walk forward from the opening paren of this symbol block to find its
        # matching close paren, tracking depth to handle nested sub-units.
        start = m.start()
        depth = 0
        j = start
        in_str = False
        while j < n:
            ch = text[j]
            if in_str:
                if ch == "\\":
                    j += 2
                    continue
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        break
            j += 1

        block = text[start : j + 1]
        pin_count = len(_PIN_RE.findall(block))
        results.append((name, pin_count))

    return results


@dataclass(frozen=True)
class SymbolRef:
    library: str
    name: str
    pin_count: int
    uri: str


class LibraryIndex:
    """A lazily-loaded index over all libraries in a sym-lib-table.

    Uses a minimal regex-based .kicad_sym parser (kicad_sch_api's
    SymbolLibraryCache._load_library is a stub in v0.5.6 and returns no data).
    """

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
            for sym_name, pin_count in _parse_kicad_sym(uri_path):
                refs.append(
                    SymbolRef(
                        library=entry.name,
                        name=sym_name,
                        pin_count=pin_count,
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
