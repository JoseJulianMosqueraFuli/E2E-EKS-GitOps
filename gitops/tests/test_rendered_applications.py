import subprocess
from pathlib import Path

import pytest
import yaml

from .application_helpers import generate_applications, load_application
from validate_applications import validate_applications

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def rendered():
    result = {}
    for application in generate_applications():
        path = ROOT / application["spec"]["source"]["path"]
        output = subprocess.check_output(["kustomize", "build", str(path)], text=True)
        result[application["metadata"]["name"]] = list(yaml.safe_load_all(output))
    return result


def test_all_generated_overlays_render_and_are_authorized():
    count, errors = validate_applications()
    assert count == 30
    assert not errors, "\n".join(errors)


def test_environments_use_separate_clusters():
    destinations = [load_application("feast", env)["spec"]["destination"]["name"] for env in ["dev", "staging", "production"]]
    assert len(set(destinations)) == 3
    assert destinations == ["mlops-dev-cluster", "mlops-staging-cluster", "mlops-prod-cluster"]


@pytest.mark.parametrize("env,prefix", [("dev", "dev"), ("staging", "staging"), ("production", "prod")])
def test_mlflow_secret_references_resolve_after_prefixing(rendered, env, prefix):
    resources = rendered[f"mlflow-{env}"]
    stores = {r["metadata"]["name"]: r for r in resources if r["kind"] == "SecretStore"}
    accounts = {r["metadata"]["name"] for r in resources if r["kind"] == "ServiceAccount"}
    secrets = {r["spec"]["target"]["name"]: r for r in resources if r["kind"] == "ExternalSecret"}
    for secret in secrets.values():
        store = stores[secret["spec"]["secretStoreRef"]["name"]]
        assert store["spec"]["provider"]["aws"]["auth"]["jwt"]["serviceAccountRef"]["name"] in accounts
    assert f"{prefix}-mlflow-postgresql:5432" in secrets[f"{prefix}-mlflow-secrets"]["spec"]["target"]["template"]["data"]["backend_store_uri"]
    for resource in resources:
        if resource["kind"] not in ["Deployment", "StatefulSet"]:
            continue
        for container in resource["spec"]["template"]["spec"]["containers"]:
            for variable in container.get("env", []):
                reference = variable.get("valueFrom", {}).get("secretKeyRef")
                if reference:
                    assert reference["name"] in secrets
                    assert reference["key"] in secrets[reference["name"]]["spec"]["target"]["template"]["data"]


def test_production_prometheus_receives_production_patch(rendered):
    prometheus = next(r for r in rendered["monitoring-production"] if r["kind"] == "StatefulSet" and r["metadata"]["name"] == "prod-prometheus")
    assert prometheus["spec"]["replicas"] == 2
    resources = prometheus["spec"]["template"]["spec"]["containers"][0]["resources"]
    assert resources["requests"]["memory"] == "1Gi"
    assert resources["limits"]["memory"] == "4Gi"


def test_workflow_builder_has_no_privileged_daemon(rendered):
    workflow = next(r for r in rendered["argo-workflows-production"] if r["kind"] == "WorkflowTemplate" and r["metadata"]["name"].endswith("model-deployment-template"))
    template = next(t for t in workflow["spec"]["templates"] if t["name"] == "build-inference-image-step")
    assert template["container"]["image"] == "moby/buildkit:v0.16.0-rootless"
    for container in [template["container"], *template.get("initContainers", []), *template.get("sidecars", [])]:
        assert not container.get("securityContext", {}).get("privileged", False)
    assert all("hostPath" not in volume for volume in template.get("volumes", []))


def test_crds_preserve_workflow_spec(rendered):
    crd = next(r for r in rendered["argo-workflows-dev"] if r["kind"] == "CustomResourceDefinition" and r["metadata"]["name"] == "workflows.argoproj.io")
    schema = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
    assert schema.get("x-kubernetes-preserve-unknown-fields") or schema["properties"]["spec"].get("x-kubernetes-preserve-unknown-fields")
