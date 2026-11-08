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
elif args[:2] == ['s3api', 'head-bucket']:
    sys.exit(1)
elif args[:2] == ['s3api', 'put-bucket-policy'] and os.environ.get('FAIL_BUCKET_POLICY'):
    sys.exit(7)
"""


@pytest.mark.parametrize("region", ["us-east-1", "eu-west-2"])
@pytest.mark.parametrize("fail_bucket_policy", [False, True])
def test_backend_names_are_unique_and_failures_are_not_hidden(tmp_path, region, fail_bucket_policy):
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
    if fail_bucket_policy:
        env["FAIL_BUCKET_POLICY"] = "true"
    result = subprocess.run(
        ["bash", str(script), "dev", region], env=env, capture_output=True, text=True
    )
    backend = tmp_path / "infra/environments/dev/backend.hcl"
    calls = json.loads((tmp_path / "calls.json").read_text())
    assert (result.returncode != 0) == fail_bucket_policy
    assert backend.exists() != fail_bucket_policy
    create = next(call for call in calls if call[:2] == ["s3api", "create-bucket"])
    assert create[create.index("--bucket") + 1] == f'mlops-terraform-state-dev-{"1" * 12}-{region}'
    assert ("--create-bucket-configuration" in create) == (region != "us-east-1")
    assert any(call[:2] == ["s3api", "put-bucket-versioning"] for call in calls)
    assert any(call[:2] == ["s3api", "put-public-access-block"] for call in calls)
    assert any(call[:2] == ["s3api", "put-bucket-policy"] for call in calls)
    assert not [call for call in calls if call[0] == "dynamodb"]
    if not fail_bucket_policy:
        settings = backend.read_text()
        assert "use_lockfile = true" in settings
        assert "encrypt = true" in settings
        assert "dynamodb_table" not in settings


@pytest.mark.parametrize("environment", ["dev", "staging", "prod"])
def test_roots_require_a_terraform_version_with_s3_lockfiles(environment):
    main = (ROOT / f"infra/environments/{environment}/main.tf").read_text()
    assert 'required_version = ">= 1.11"' in main
