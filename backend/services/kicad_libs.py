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
