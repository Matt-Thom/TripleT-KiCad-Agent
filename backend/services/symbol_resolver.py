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
