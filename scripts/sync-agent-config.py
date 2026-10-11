#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / ".agents" / "rules"
MCP_SOURCE = ROOT / ".agents" / "mcp" / "servers.json"
ENV_REF = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def parse_rule(path):
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n+(.*)$", text, re.S)
    if not match:
        raise SystemExit(f"{path}: missing frontmatter")
    meta = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    globs = [g.strip() for g in meta.get("globs", "").split(",") if g.strip()]
    return {
        "name": path.stem,
        "description": meta.get("description", ""),
        "globs": globs,
        "source": path.relative_to(ROOT).as_posix(),
    }


def yaml_str(value):
    return json.dumps(value)


def kiro_rule(rule):
    lines = ["---"]
    if rule["globs"]:
        lines.append("inclusion: fileMatch")
        if len(rule["globs"]) == 1:
            lines.append(f"fileMatchPattern: {yaml_str(rule['globs'][0])}")
        else:
            lines.append(f"fileMatchPattern: [{', '.join(yaml_str(g) for g in rule['globs'])}]")
    else:
        lines.append("inclusion: always")
    lines += ["---", "", f"#[[file:{rule['source']}]]", ""]
    return "\n".join(lines)


def copilot_rule(rule):
    apply_to = ",".join(rule["globs"]) if rule["globs"] else "**"
    lines = [
        "---",
        f"description: {yaml_str(rule['description'])}",
        f"applyTo: {yaml_str(apply_to)}",
        "---",
        "",
        f"Read and follow [{rule['name']}](../../{rule['source']}).",
        "",
    ]
    return "\n".join(lines)


def claude_rule(rule):
    include = f"@../../{rule['source']}\n"
    if not rule["globs"]:
        return include
    lines = ["---", "paths:"]
    lines += [f"  - {yaml_str(g)}" for g in rule["globs"]]
    lines += ["---", "", include]
    return "\n".join(lines)


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
    outputs = {}
    for path in sorted(RULES_DIR.glob("*.md")):
        rule = parse_rule(path)
        outputs[ROOT / ".kiro" / "steering" / f"{rule['name']}.md"] = kiro_rule(rule)
        outputs[ROOT / ".github" / "instructions" / f"{rule['name']}.instructions.md"] = (
            copilot_rule(rule)
        )
        outputs[ROOT / ".claude" / "rules" / f"{rule['name']}.md"] = claude_rule(rule)
    outputs.update(mcp_configs(json.loads(MCP_SOURCE.read_text())["servers"]))
    return outputs


def main():
    check = "--check" in sys.argv[1:]
    stale = []
    for path, content in build_outputs().items():
        current = path.read_text() if path.exists() else None
        if current == content:
            continue
        stale.append(path.relative_to(ROOT))
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if check and stale:
        print("Out of date (run `make agents-sync`):")
        for path in stale:
            print(f"  {path}")
        return 1
    print(f"{'Checked' if check else 'Synced'}: {len(stale)} file(s) {'stale' if check else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
