import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TerraformInitialPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repository = self.root / "repository"
        scripts = self.repository / "scripts"
        scripts.mkdir(parents=True)
        self.script = scripts / "terraform-initial-plan.sh"
        shutil.copy2(
            Path(__file__).resolve().parents[2] / "scripts/terraform-initial-plan.sh",
            self.script,
        )
        self.infrastructure = self.repository / "infra/environments/dev"
        self.infrastructure.mkdir(parents=True)
        (self.infrastructure / "main.tf").write_text(
            'terraform {\n  backend "s3" {}\n}\n', encoding="utf-8"
        )
        for name in ("terraform.tfstate", "terraform.tfvars", "private.auto.tfvars.json"):
            (self.infrastructure / name).write_text("must not reach the plan", encoding="utf-8")
        binary_directory = self.root / "bin"
        binary_directory.mkdir()
        terraform = binary_directory / "terraform"
        terraform.write_text(
            """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1].split("=", 1)[1])
command = sys.argv[2]
if command not in {"init", "validate", "plan"}:
    sys.exit(99)
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps({
        "command": command,
        "arguments": sys.argv[3:],
        "root": str(root),
        "files": sorted(path.name for path in root.iterdir()),
        "backend": (root / "zz_initial_plan_override.tf").read_text(),
    }) + "\\n")
sys.exit(int(os.environ.get("STUB_" + command.upper() + "_EXIT_CODE", "0")))
""",
            encoding="utf-8",
        )
        terraform.chmod(0o755)
        self.log = self.root / "terraform.log"
        self.summary = self.root / "summary.md"
        self.environment = {
            **os.environ,
            "PATH": f"{binary_directory}{os.pathsep}{os.environ['PATH']}",
            "GITHUB_ACTIONS": "true",
            "RUNNER_TEMP": str(self.root),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "STUB_LOG": str(self.log),
            "STUB_PLAN_EXIT_CODE": "2",
        }

    def run_plan(self, environment: str = "dev") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.script), environment],
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_changes_succeed_without_copying_state_or_saving_a_plan(self) -> None:
        result = self.run_plan()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual([call["command"] for call in calls], ["init", "validate", "plan"])
        for call in calls:
            self.assertEqual(call["files"], ["main.tf", "zz_initial_plan_override.tf"])
            self.assertIn('backend "local"', call["backend"])
            self.assertFalse(Path(call["root"]).parents[2].exists())
        self.assertIn("-detailed-exitcode", calls[-1]["arguments"])
        self.assertFalse(any(arg.startswith("-out") for arg in calls[-1]["arguments"]))
        self.assertIn("Changes proposed", self.summary.read_text())
        self.assertIn('backend "s3"', (self.infrastructure / "main.tf").read_text())
        self.assertTrue((self.infrastructure / "terraform.tfstate").exists())
        self.assertFalse((self.infrastructure / "zz_initial_plan_override.tf").exists())

    def test_no_changes_succeed(self) -> None:
        self.environment["STUB_PLAN_EXIT_CODE"] = "0"
        self.assertEqual(self.run_plan().returncode, 0)
        self.assertIn("No changes proposed", self.summary.read_text())

    def test_plan_errors_fail_and_cleanup(self) -> None:
        self.environment["STUB_PLAN_EXIT_CODE"] = "1"
        self.assertEqual(self.run_plan().returncode, 1)
        self.assertFalse(self.summary.exists())
        self.assertEqual(list(self.root.glob("terraform-initial-plan.*")), [])

    def test_validation_failure_prevents_planning(self) -> None:
        self.environment["STUB_VALIDATE_EXIT_CODE"] = "1"
        self.assertEqual(self.run_plan().returncode, 1)
        calls = [json.loads(line)["command"] for line in self.log.read_text().splitlines()]
        self.assertEqual(calls, ["init", "validate"])

    def test_refuses_local_execution(self) -> None:
        self.environment.pop("GITHUB_ACTIONS")
        result = self.run_plan()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local AWS planning is disabled", result.stderr)
        self.assertFalse(self.log.exists())

    def test_rejects_invalid_environment_before_running_terraform(self) -> None:
        self.assertNotEqual(self.run_plan("../../outside").returncode, 0)
        self.assertFalse(self.log.exists())
