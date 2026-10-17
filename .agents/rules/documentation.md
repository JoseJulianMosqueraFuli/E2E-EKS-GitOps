---
description: Documentation conventions for docs/, READMEs, backlog and critical tracking
globs: docs/**, **/*.md
---

# Documentation

- `docs/README.md` is the hub: every new doc is linked from it.
- `README.md` and `README.es.md` are kept in sync; a change to one requires the equivalent change in the other.
- `docs/project/backlog.md` is the canonical backlog, `docs/project/critical.md` holds CRITICAL/HIGH details. Use existing IDs (`CRIT-004`, `HIGH-013`) when referring to items; new items get the next free ID.
- Write for an engineer new to the repo: what it is, why, how to run it, how to verify it. Prefer runnable commands over prose.
- Keep docs factual and current: when a command, path or component changes, update the docs in the same change. Remove outdated sections rather than annotating them.
- Diagrams: source in `docs/architecture.drawio` / `docs/diagrams/`; update them when topology changes.
- Shared agent instructions live in `AGENTS.md` and `.agents/rules/`. Run `make agents-sync` to maintain the minimal tool entry points and MCP configurations; do not recreate per-tool rule copies.
