"""Pattern protocol: every circuit pattern exposes metadata + apply(sch, **inputs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PatternMetadata:
    id: str
    title: str
    tags: tuple[str, ...]
    description: str
    inputs: dict[str, str] = field(default_factory=dict)  # name -> short-type-label


@runtime_checkable
class Pattern(Protocol):
    metadata: PatternMetadata

    def apply(self, sch: Any, **inputs: Any) -> Any:
        """Apply this pattern to an in-memory schematic. Returns the mutated schematic."""
        ...


def is_pattern(obj: Any) -> bool:
    """True if `obj` conforms to the `Pattern` protocol at runtime."""
    return (
        hasattr(obj, "metadata")
        and isinstance(getattr(obj, "metadata", None), PatternMetadata)
        and callable(getattr(obj, "apply", None))
    )
