import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "environment,prefix", [("dev", "dev"), ("staging", "staging"), ("production", "prod")]
)
def test_rendered_platform_identity_storage_and_images_agree(environment, prefix):
    config = dict(
        line.split("=", 1)
        for line in (ROOT / "gitops/platform/aws.env").read_text().splitlines()
        if "=" in line
    )
    account, region = config["AWS_ACCOUNT_ID"], config["AWS_REGION"]
    output = subprocess.check_output(
        [
            "kustomize",
            "build",
            str(ROOT / "gitops/applications/apps/mlflow/overlays" / environment),
        ],
        text=True,
    )
    docs = list(yaml.safe_load_all(output))
    backup = next(d for d in docs if d["kind"] == "CronJob")
    container = backup["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
    variables = {e["name"]: e.get("value") for e in container["env"]}
    assert variables["PGHOST"] == f"{prefix}-mlflow-postgresql"
    assert variables["S3_BACKUP_BUCKET"] == f"mlops-{prefix}-backups-{account}-{region}"
    store = next(d for d in docs if d["kind"] == "SecretStore")
    assert (
        store["spec"]["provider"]["aws"]["auth"]["jwt"]["serviceAccountRef"]["name"]
        == f"{prefix}-mlflow-secrets"
    )
    if environment == "production":
        deployment = next(
            d
            for d in docs
            if d["kind"] == "Deployment" and d["metadata"]["name"] == "prod-mlflow-server"
        )
        assert not any(
            e["name"] in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
            for e in deployment["spec"]["template"]["spec"]["containers"][0]["env"]
        )
    output = subprocess.check_output(
        [
            "kustomize",
            "build",
            str(ROOT / "gitops/applications/apps/argo-workflows/overlays" / environment),
        ],
        text=True,
    )
    docs = list(yaml.safe_load_all(output))
    workflow = next(
        d
        for d in docs
        if d["kind"] == "WorkflowTemplate" and d["metadata"]["name"] == "data-validation-template"
    )
    source = next(
        p for p in workflow["spec"]["arguments"]["parameters"] if p["name"] == "data-source"
    )["value"]
    assert source == f"s3://mlops-{prefix}-raw-data-{account}-{region}/input/data.csv"
    assert not any(
        token in output
        for token in (
            "mlops/data-validator",
            "mlops/kserve-deployer",
            "mlops/notifier",
            ":latest",
            "AWS_ACCOUNT_ID",
            "AWS_REGION",
        )
    )
    binding = next(
        d
        for d in docs
        if d["kind"] == "RoleBinding" and d["metadata"]["name"] == "model-deployment"
    )
    assert binding["metadata"]["namespace"] == "models"


def test_argocd_renders_without_an_ignored_aws_env_file(tmp_path):
    shutil.copytree(
        ROOT / "gitops",
        tmp_path / "gitops",
        ignore=shutil.ignore_patterns(
            "aws.env", ".venv", "__pycache__", ".hypothesis", ".pytest_cache"
        ),
    )
    env = {**os.environ, "AWS_ACCOUNT_ID": "1" * 12, "AWS_REGION": "eu-west-2"}
    script = tmp_path / "gitops/scripts/render-platform.sh"
    overlay = tmp_path / "gitops/applications/apps/mlflow/overlays/dev"
    result = subprocess.run(
        ["sh", str(script)], cwd=overlay, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert f"{env['AWS_ACCOUNT_ID']}.dkr.ecr.{env['AWS_REGION']}" in result.stdout
    assert "AWS_ACCOUNT_ID" not in result.stdout
    env["AWS_ACCOUNT_ID"] = "0" * 12
    result = subprocess.run(
        ["sh", str(script)], cwd=overlay, env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert not result.stdout
