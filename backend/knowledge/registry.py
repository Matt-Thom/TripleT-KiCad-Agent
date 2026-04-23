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


from rank_bm25 import BM25Okapi


class PatternRetriever:
    def __init__(self, registry: PatternRegistry) -> None:
        self._registry = registry
        self._patterns = registry.all()
        # Tokenized corpus: concatenate title + tags + description per pattern
        self._corpus_docs = [self._tokens_for(p) for p in self._patterns]
        self._bm25 = BM25Okapi(self._corpus_docs) if self._corpus_docs else None

    @staticmethod
    def _tokens_for(pat: Pattern) -> list[str]:
        md = pat.metadata
        text = f"{md.title} {' '.join(md.tags)} {md.description}"
        return [t.lower() for t in text.split() if t]

    def search(self, query: str, *, top_k: int = 3, min_score: float = 0.1) -> list[Pattern]:
        if self._bm25 is None:
            return []
        tokens = [t.lower() for t in query.split() if t]
        scores = self._bm25.get_scores(tokens)
        scored = sorted(
            zip(scores, self._patterns), key=lambda pair: pair[0], reverse=True
        )
        return [pat for score, pat in scored[:top_k] if score >= min_score]
