#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / ".agents" / "rules"
MCP_SOURCE = ROOT / ".agents" / "mcp" / "servers.json"
ENV_REF = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def legacy_bridges() -> list[Path]:
    obsolete = []
    for rule in sorted(RULES_DIR.glob("*.md")):
        source = rule.relative_to(ROOT).as_posix()
        references = {
            ROOT / ".kiro" / "steering" / rule.name: f"#[[file:{source}]]",
            ROOT / ".claude" / "rules" / rule.name: f"@../../{source}",
            ROOT / ".github" / "instructions" / f"{rule.stem}.instructions.md": (
                f"Read and follow [{rule.stem}](../../{source})."
            ),
        }
        for path, reference in references.items():
            if not path.exists():
                continue
            body = re.sub(r"\A---\n.*?\n---\n*", "", path.read_text(), count=1, flags=re.S)
            if body.strip() != reference:
                raise SystemExit(
                    f"Preserving modified legacy instructions: {path.relative_to(ROOT)}"
                )
            obsolete.append(path)
    return obsolete


def render_env(env, style):
    def repl(match):
        name = match.group(1)
        return f"${{env:{name}}}" if style == "vscode" else f"${{{name}}}"

    return {key: ENV_REF.sub(repl, value) for key, value in env.items()}


def mcp_configs(servers):
    claude, vscode, kiro = {}, {}, {}
    for name, spec in servers.items():
        base = {"command": spec["command"], "args": spec["args"]}
        claude[name] = {"type": "stdio", **base, "env": render_env(spec["env"], "claude")}
        vscode[name] = {"type": "stdio", **base, "env": render_env(spec["env"], "vscode")}
        kiro[name] = {
            **base,
            "env": render_env(spec["env"], "kiro"),
            "disabled": bool(spec.get("optional")),
            "autoApprove": [],
        }
    dump = lambda data: json.dumps(data, indent=2) + "\n"
    return {
        ROOT / ".mcp.json": dump({"mcpServers": claude}),
        ROOT / ".vscode" / "mcp.json": dump({"servers": vscode}),
        ROOT / ".kiro" / "settings" / "mcp.json": dump({"mcpServers": kiro}),
    }


def build_outputs():
    outputs = {
        ROOT / "CLAUDE.md": "@AGENTS.md\n",
        ROOT / ".github" / "copilot-instructions.md": (
            "Read and follow [AGENTS.md](../AGENTS.md) before starting any task.\n"
        ),
    }
    outputs.update(mcp_configs(json.loads(MCP_SOURCE.read_text())["servers"]))
    return outputs


def main():
    check = "--check" in sys.argv[1:]
    obsolete = legacy_bridges()
    stale = []
    for path, content in build_outputs().items():
        current = path.read_text() if path.exists() else None
        if current == content:
            continue
        stale.append(path.relative_to(ROOT))
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if check and (stale or obsolete):
        print("Out of date (run `make agents-sync`):")
        for path in stale:
            print(f"  {path}")
        for path in obsolete:
            print(f"  Remove legacy bridge: {path.relative_to(ROOT)}")
        return 1
    if not check:
        for path in obsolete:
            path.unlink()
        for directory in sorted({path.parent for path in obsolete}):
            if not any(directory.iterdir()):
                directory.rmdir()
        claude_directory = ROOT / ".claude"
        if claude_directory.is_dir() and not any(claude_directory.iterdir()):
            claude_directory.rmdir()
        print(f"Removed {len(obsolete)} legacy bridge file(s)")
    action = "Checked" if check else "Synced"
    status = "stale" if check else "updated"
    print(f"{action}: {len(stale)} file(s) {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
