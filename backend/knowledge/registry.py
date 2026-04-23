"""PatternRegistry: auto-discovers Pattern subclasses in backend.knowledge.patterns."""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Optional

from backend.knowledge import patterns as _patterns_pkg
from backend.knowledge.protocol import Pattern, is_pattern


class PatternRegistry:
    def __init__(self, items: list[Pattern]) -> None:
        self._items = {p.metadata.id: p for p in items}

    @classmethod
    def discover(cls) -> "PatternRegistry":
        found: list[Pattern] = []
        for modinfo in pkgutil.iter_modules(_patterns_pkg.__path__):
            mod = importlib.import_module(f"{_patterns_pkg.__name__}.{modinfo.name}")
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if obj.__module__ != mod.__name__:
                    continue
                try:
                    instance = obj()
                except TypeError:
                    continue  # Needs args — not a simple Pattern class
                if is_pattern(instance):
                    found.append(instance)
        return cls(found)

    def all(self) -> list[Pattern]:
        return list(self._items.values())

    def get(self, pattern_id: str) -> Optional[Pattern]:
        return self._items.get(pattern_id)
