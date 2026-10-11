# .agents — AI agent configuration (source of truth)

Single source for the rules and MCP servers used by every AI assistant on this repo (Kiro, VS Code / GitHub Copilot, Claude Code). Edit here, then generate the tool-specific bridge files (frontmatter + a reference back to `.agents/rules/`, no copied content):

```bash
make agents-sync    # regenerate
make agents-check   # fail if generated files are stale
```

## Layout

| Path | Content |
|------|---------|
| `rules/*.md` | Best practices and agent documentation, one topic per file |
| `mcp/servers.json` | MCP servers (all read-only) |

## Rules

| Rule | Loaded |
|------|--------|
| `engineering.md` | always |
| `architecture.md` | always |
| `security.md` | always |
| `ml-architecture.md` | always |
| `terraform.md` | `**/*.tf`, `infra/**` |
| `kubernetes-gitops.md` | `k8s/**`, `gitops/applications/**`, `gitops/charts/**`, `gitops/infrastructure/**` |
| `python.md` | `**/*.py`, `**/pyproject.toml` |
| `ml-engineering.md` | `ml-platform/**` |
| `ci-cd.md` | CI configs, `Makefile` |
| `documentation.md` | `docs/**`, `**/*.md` |

Each rule has frontmatter:

```markdown
---
description: One line describing the rule
globs: comma, separated, globs   # empty = always loaded
---
```

## Generated bridge files (do not edit)

Each tool references the canonical rule with its own include syntax: Kiro `#[[file:...]]`, Claude Code `@...`, Copilot a Markdown link.

| Tool | Rules | MCP |
|------|-------|-----|
| Kiro | `.kiro/steering/*.md` | `.kiro/settings/mcp.json` |
| VS Code (Copilot) | `.github/instructions/*.instructions.md` | `.vscode/mcp.json` |
| Claude Code | `.claude/rules/*.md` | `.mcp.json` |

`AGENTS.md` (root) is read natively by Kiro, Copilot and Codex; `CLAUDE.md` imports it for Claude Code.

## MCP servers

All servers are read-only. None mutate AWS, the cluster or GitHub.

| Server | Purpose | Requirements |
|--------|---------|--------------|
| `terraform` | Terraform Registry docs | Docker |
| `aws-docs` | AWS docs / Well-Architected | `uv` (`brew install uv`) |
| `github` | Issues, PRs, Actions (`GITHUB_READ_ONLY=1`) | Docker, `GITHUB_PERSONAL_ACCESS_TOKEN` env var |
| `eks` | EKS inspection (no `--allow-write`) | `uv`, AWS credentials — disabled in Kiro by default |
| `kubernetes` | kubectl read-only (`ALLOW_ONLY_READONLY_TOOLS`) | Node, kubeconfig — disabled in Kiro by default |

Secrets are never stored here: reference them as `{env:VAR}` in `servers.json` and the generator renders the right syntax per tool.
