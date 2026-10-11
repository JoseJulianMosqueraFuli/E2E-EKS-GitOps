---
description: Documentation conventions for docs/, READMEs, backlog and critical tracking
globs: docs/**, **/*.md
---

# Documentation

- `docs/README.md` is the hub: every new doc is linked from it.
- `README.md` and `README.es.md` are kept in sync; a change to one requires the equivalent change in the other.
- `backlog.md` is the canonical backlog, `critical.md` holds CRITICAL/HIGH details. Use existing IDs (`CRIT-004`, `HIGH-013`) when referring to items; new items get the next free ID.
- Write for an engineer new to the repo: what it is, why, how to run it, how to verify it. Prefer runnable commands over prose.
- Keep docs factual and current: when a command, path or component changes, update the docs in the same change. Remove outdated sections rather than annotating them.
- Diagrams: source in `docs/architecture.drawio` / `docs/diagrams/`; update them when topology changes.
- Agent rules live in `.agents/rules/`; edit them there and run `make agents-sync`, never edit the generated copies in `.kiro/steering/`, `.github/instructions/` or `.claude/rules/`.
