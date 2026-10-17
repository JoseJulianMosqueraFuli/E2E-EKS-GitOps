import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/sync-agent-config.py"
SPEC = importlib.util.spec_from_file_location("sync_agent_config", SCRIPT)
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class AgentConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        rules = self.root / ".agents/rules"
        rules.mkdir(parents=True)
        self.rule = rules / "engineering.md"
        self.rule.write_text("Shared instructions must survive migration.\n", encoding="utf-8")
        mcp = self.root / ".agents/mcp/servers.json"
        mcp.parent.mkdir()
        mcp.write_text(
            json.dumps(
                {
                    "servers": {
                        "sample": {
                            "command": "sample-mcp",
                            "args": ["--read-only"],
                            "env": {"TOKEN": "{env:SAMPLE_TOKEN}"},
                            "optional": True,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        self.patcher = patch.multiple(SYNC, ROOT=self.root, RULES_DIR=rules, MCP_SOURCE=mcp)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def run_sync(self, check: bool = False) -> int:
        arguments = [str(SCRIPT), "--check"] if check else [str(SCRIPT)]
        with patch("sys.argv", arguments), contextlib.redirect_stdout(io.StringIO()):
            return SYNC.main()

    def add_legacy_bridges(self) -> list[Path]:
        contents = {
            ".kiro/steering/engineering.md": (
                "---\ninclusion: always\n---\n\n#[[file:.agents/rules/engineering.md]]\n"
            ),
            ".claude/rules/engineering.md": "@../../.agents/rules/engineering.md\n",
            ".github/instructions/engineering.instructions.md": (
                '---\napplyTo: "**"\n---\n\n'
                "Read and follow [engineering](../../.agents/rules/engineering.md).\n"
            ),
        }
        paths = []
        for relative, content in contents.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
        return paths

    def test_migration_removes_only_generated_bridges_and_is_idempotent(self) -> None:
        bridges = self.add_legacy_bridges()
        custom = self.root / ".kiro/steering/local-notes.md"
        custom.write_text("Personal instructions.\n", encoding="utf-8")
        original_rule = self.rule.read_bytes()
        self.assertEqual(self.run_sync(check=True), 1)
        self.assertTrue(all(path.exists() for path in bridges))
        self.assertEqual(self.run_sync(), 0)
        self.assertTrue(all(not path.exists() for path in bridges))
        self.assertEqual(self.rule.read_bytes(), original_rule)
        self.assertEqual(custom.read_text(), "Personal instructions.\n")
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        self.assertIn("../AGENTS.md", (self.root / ".github/copilot-instructions.md").read_text())
        self.assertEqual(self.run_sync(check=True), 0)
        self.assertEqual(self.run_sync(), 0)
        self.assertTrue(all(not path.exists() for path in bridges))

    def test_modified_legacy_content_blocks_cleanup_without_writing(self) -> None:
        bridges = self.add_legacy_bridges()
        bridges[0].write_text("Custom instructions that must not be removed.\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "Preserving modified legacy instructions"):
            self.run_sync()
        self.assertTrue(all(path.exists() for path in bridges))
        self.assertFalse((self.root / ".github/copilot-instructions.md").exists())

    def test_mcp_generation_preserves_env_references_and_optional_servers(self) -> None:
        self.assertEqual(self.run_sync(), 0)
        claude = json.loads((self.root / ".mcp.json").read_text())["mcpServers"]["sample"]
        vscode = json.loads((self.root / ".vscode/mcp.json").read_text())["servers"]["sample"]
        kiro_config = json.loads((self.root / ".kiro/settings/mcp.json").read_text())
        kiro = kiro_config["mcpServers"]["sample"]
        self.assertEqual(claude["env"]["TOKEN"], "${SAMPLE_TOKEN}")
        self.assertEqual(vscode["env"]["TOKEN"], "${env:SAMPLE_TOKEN}")
        self.assertEqual(kiro["env"]["TOKEN"], "${SAMPLE_TOKEN}")
        self.assertTrue(kiro["disabled"])
        self.assertEqual(kiro["autoApprove"], [])
        self.assertEqual(kiro["args"], ["--read-only"])
