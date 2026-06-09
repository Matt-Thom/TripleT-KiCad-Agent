# Wiki Schema

Conventions for this wiki. Update as the project's needs evolve.

## Page types

- **overview** — one per wiki, the front door. Architectural tour.
- **entity** — documents a concrete thing in the codebase: a service, module, router, component, registry.
- **concept** — documents a cross-cutting pattern: a flow, a precedence rule, a strategy.
- **query** — filed answer to a synthesis question worth keeping.

## Frontmatter

Every page starts with YAML frontmatter:

```yaml
---
title: Page Title
type: overview | entity | concept | query
tags: [kw1, kw2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
related_files: [backend/services/foo.py]
---
```

## Writing rules

- **Source wins.** If the wiki and the code disagree, update the wiki.
- **Cite code.** Reference sources as `path/to/file.py:LINE`. These become stale — tolerate small drift (±5 lines), rewrite when they're wrong.
- **Cross-link.** Use `[[wiki/path/page]]` (slashes, no extension) for wiki-internal references.
- **Diagrams.** Use mermaid fenced as ` ```mermaid ` for flows and decision trees.
- **Be terse.** Pages over ~200 lines are a smell. Split them.
- **No prose summaries of code.** Describe intent, invariants, and decisions — not line-by-line behaviour the reader can see for themselves.

## When to update

| Event | Action |
|---|---|
| New service / module added | New entity page + update [[index]]. |
| File renamed or moved | Update `related_files` and any `file:line` refs on affected pages. |
| Architectural decision made | Add or update a concept page; note the reason. |
| New cross-cutting pattern | New concept page. |
| Formatting, comments, minor refactors | **Skip.** Don't pollute the log. |

## Log discipline

Every structural wiki change appends an entry to [[log]] with date, operation, and one-line reason.
