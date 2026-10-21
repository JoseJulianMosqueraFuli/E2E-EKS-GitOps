import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AWS_DOUBLE = r"""
import json
import os
import sys
from pathlib import Path

path = Path(os.environ['AWS_CALLS'])
calls = json.loads(path.read_text()) if path.exists() else []
args = sys.argv[1:]
calls.append(args)
path.write_text(json.dumps(calls))
if args[:2] == ['sts', 'get-caller-identity']:
    print('1' * 12)
elif args[:2] in [['s3api', 'head-bucket'], ['dynamodb', 'describe-table']]:
    sys.exit(1)
elif args[:2] == ['dynamodb', 'create-table'] and os.environ.get('FAIL_LOCK_TABLE'):
    sys.exit(7)
"""


@pytest.mark.parametrize("region", ["us-east-1", "eu-west-2"])
@pytest.mark.parametrize("fail_lock_table", [False, True])
def test_backend_names_are_unique_and_failures_are_not_hidden(tmp_path, region, fail_lock_table):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "infra/environments/dev").mkdir(parents=True)
    script = tmp_path / "scripts/bootstrap-terraform-backend.sh"
    shutil.copy(ROOT / "scripts/bootstrap-terraform-backend.sh", script)
    binary = tmp_path / "bin"
    binary.mkdir()
    aws = binary / "aws"
    aws.write_text(f"#!{sys.executable}\n{AWS_DOUBLE}")
    aws.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f'{binary}:{os.environ["PATH"]}',
        "AWS_CALLS": str(tmp_path / "calls.json"),
    }
    if fail_lock_table:
        env["FAIL_LOCK_TABLE"] = "true"
    result = subprocess.run(
        ["bash", str(script), "dev", region], env=env, capture_output=True, text=True
    )
    backend = tmp_path / "infra/environments/dev/backend.hcl"
    calls = json.loads((tmp_path / "calls.json").read_text())
    assert (result.returncode != 0) == fail_lock_table
    assert backend.exists() != fail_lock_table
    create = next(call for call in calls if call[:2] == ["s3api", "create-bucket"])
    assert create[create.index("--bucket") + 1] == f'mlops-terraform-state-dev-{"1" * 12}-{region}'
    assert ("--create-bucket-configuration" in create) == (region != "us-east-1")
    assert any(call[:2] == ["s3api", "put-public-access-block"] for call in calls)
    assert any(call[:2] == ["s3api", "put-bucket-policy"] for call in calls)
    if not fail_lock_table:
        assert "encrypt = true" in backend.read_text()
        assert 'dynamodb_table = "mlops-terraform-locks-dev"' in backend.read_text()
