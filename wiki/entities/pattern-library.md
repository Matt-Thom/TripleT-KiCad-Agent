---
title: Pattern Library
type: entity
tags: [patterns, knowledge, bm25, kicad_sch_api]
created: 2026-04-24
updated: 2026-04-24
related_files: [backend/knowledge/protocol.py, backend/knowledge/registry.py, backend/knowledge/patterns/]
---

Executable circuit patterns discovered at runtime and indexed for retrieval. Patterns are preferred over raw schematic generation whenever a user request matches a known sub-circuit.

## Protocol

`backend/knowledge/protocol.py`. A `Pattern` is any object with:

- `metadata: PatternMetadata` — `id`, `title`, `tags: tuple[str, ...]`, `description`, and an `inputs` dict (`name -> short-type-label`, surfaced to the LLM so it knows how to call `apply_pattern`).
- `apply(sch, **inputs) -> sch` — mutates the supplied `kicad_sch_api` schematic.

`Pattern` is a `runtime_checkable` Protocol but `is_pattern()` uses structural checks — concrete classes don't need to inherit anything, they just need the attributes.

## Discovery

`PatternRegistry.discover()` (`backend/knowledge/registry.py:22`) walks `backend/knowledge/patterns/*` with `pkgutil.iter_modules`, imports each module, instantiates every class defined in it (skipping those that can't be no-arg constructed), and keeps the instances that pass `is_pattern()`. Failures during import log a warning and skip the module — one broken pattern doesn't kill the registry.

## Retrieval — BM25

`PatternRetriever` (line 49) builds a BM25Okapi index over each pattern's tokenized `title + tags + description`. Queries are lowercased and whitespace-split. `search(query, top_k=3, min_score=0.1)` returns the top matches above the threshold. The minimum score exists so unrelated queries return `[]` rather than whatever pattern scored highest — the `lookup_pattern` tool uses that empty signal to tell the agent to fall back to ad-hoc generation.

## Seed patterns

Current contents of `backend/knowledge/patterns/`: `ldo_regulator`, `usb_c_input`, `i2c_pullups`, `mcu_reset`. Each is one Python module containing one class.

To add a pattern: drop a new module in `patterns/`, define a class with the required `metadata` and `apply()`, and it's picked up on next discovery. No registration boilerplate.

## Tool surface

Two tools in `backend/services/tools.py`:

- `lookup_pattern(query)` — returns up to 3 pattern summaries (`id`, `title`, `description`, `inputs`) for the model to choose from.
- `apply_pattern(pattern_id, inputs)` — instantiates a blank schematic via `ksa.create_schematic()`, calls `pat.apply(sch, **inputs)`, saves to `generated_schematics/{pattern_id}.kicad_sch`.

The system prompt (`backend/main.py:127`) explicitly tells the model to `lookup_pattern` before `apply_pattern` and to prefer patterns over custom generation for standard sub-circuits.
