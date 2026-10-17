# .agents — shared rules and MCP configuration

[AGENTS.md](../AGENTS.md) is the shared entry point for project instructions. The detailed rules live
only in this directory. Claude and Copilot reference that entry point; Kiro reads it directly.

## Layout

| Path | Content |
|------|---------|
| [`../AGENTS.md`](../AGENTS.md) | Project context and instructions for reading the shared rules |
| `rules/*.md` | Engineering guidance, maintained once per topic |
| `mcp/servers.json` | Canonical MCP server configuration (all read-only) |

## Rules

Before changing files, read the rules marked **always**, then the rules relevant to the task.
`AGENTS.md` directs each agent to this index. Frontmatter records each rule's scope; separate per-tool
files for automatic path-based inclusion are no longer generated.

| Rule | Read when |
|------|-----------|
| [Engineering](rules/engineering.md) | always |
| [Architecture](rules/architecture.md) | always |
| [Security](rules/security.md) | always |
| [ML architecture](rules/ml-architecture.md) | always |
| [Terraform](rules/terraform.md) | `**/*.tf`, `infra/**` |
| [Kubernetes / GitOps](rules/kubernetes-gitops.md) | `k8s/**`, `gitops/applications/**`, `gitops/charts/**`, `gitops/infrastructure/**` |
| [Python](rules/python.md) | `**/*.py`, `**/pyproject.toml` |
| [ML engineering](rules/ml-engineering.md) | `ml-platform/**` |
| [CI/CD](rules/ci-cd.md) | CI configs, `Makefile` |
| [Documentation](rules/documentation.md) | `docs/**`, `**/*.md` |

## Tool entry points

| Tool | Shared instructions | MCP configuration |
|------|---------------------|-------------------|
| Kiro | Root `AGENTS.md`, loaded natively | `.kiro/settings/mcp.json` |
| VS Code / Copilot | `.github/copilot-instructions.md` links to `AGENTS.md` | `.vscode/mcp.json` |
| Claude Code | `CLAUDE.md` contains only `@AGENTS.md` | `.mcp.json` |

Kiro's [AGENTS.md support](https://kiro.dev/docs/steering/#agentsmd), Claude's
[imports](https://code.claude.com/docs/en/memory), and VS Code's
[instruction references](https://code.visualstudio.com/docs/agent-customization/custom-instructions)
let the tools share project guidance. The tool-specific MCP files remain necessary because their
locations, schemas, and environment-variable syntax differ.

```bash
make agents-sync
make agents-check
```

`agents-sync` generates the two small instruction entry points and the three MCP configurations.
It also removes obsolete generated rule references from `.kiro/steering/`, `.claude/rules/`, and
`.github/instructions/`; if one contains customized instructions, it stops without deleting it.
`agents-check` reports stale generated files or obsolete references without writing anything.
Edit `AGENTS.md`, the shared rules, and `mcp/servers.json`; let the generator maintain the tool files.

## MCP servers

All servers are read-only. None mutate AWS, the cluster, or GitHub.

| Server | Purpose | Requirements |
|--------|---------|--------------|
| `terraform` | Terraform Registry docs | Docker |
| `aws-docs` | AWS docs / Well-Architected | `uv` (`brew install uv`) |
| `github` | Issues, PRs, Actions (`GITHUB_READ_ONLY=1`) | Docker, `GITHUB_PERSONAL_ACCESS_TOKEN` env var |
| `eks` | EKS inspection (no `--allow-write`) | `uv`, AWS credentials — disabled in Kiro by default |
| `kubernetes` | kubectl read-only (`ALLOW_ONLY_READONLY_TOOLS`) | Node, kubeconfig — disabled in Kiro by default |

Secrets are never stored here: reference them as `{env:VAR}` in `servers.json`; the generator renders
that reference in each tool's required format.
