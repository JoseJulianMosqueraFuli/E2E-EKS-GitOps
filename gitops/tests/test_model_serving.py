import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
KSERVE = ROOT / "gitops/applications/apps/kserve"
CERT_MANAGER = ROOT / "gitops/infrastructure/addons/cert-manager"
KSERVE_VERSION = "v0.21.0"
CERT_MANAGER_VERSION = "v1.21.3"
ALLOWED_KINDS = {"Namespace", "HelmRepository", "HelmRelease", "ServiceAccount", "NetworkPolicy"}


def render(path):
    output = subprocess.check_output(["kustomize", "build", str(path)], text=True)
    return [doc for doc in yaml.safe_load_all(output) if doc]


PREFIXES = {"dev": "dev-", "staging": "staging-", "production": "prod-"}


def by_name(resources, kind, name):
    return next(r for r in resources if r["kind"] == kind and r["metadata"]["name"] == name)


@pytest.fixture(scope="module", params=sorted(PREFIXES))
def kserve(request):
    prefix = PREFIXES[request.param]
    resources = render(KSERVE / "overlays" / request.param)
    return lambda kind, name: by_name(resources, kind, prefix + name), resources, prefix


def test_kserve_is_installed_from_pinned_charts_only(kserve):
    get, resources, prefix = kserve
    assert {r["kind"] for r in resources} <= ALLOWED_KINDS
    assert get("HelmRepository", "kserve")["spec"] == {
        "type": "oci",
        "interval": "1h",
        "url": "oci://ghcr.io/kserve/charts",
    }
    charts = {
        name: get("HelmRelease", name)["spec"]["chart"]["spec"] for name in ("kserve-crd", "kserve")
    }
    assert charts["kserve-crd"]["chart"] == "kserve-crd"
    assert charts["kserve"]["chart"] == "kserve-resources"
    assert {chart["version"] for chart in charts.values()} == {KSERVE_VERSION}
    assert {chart["sourceRef"]["name"] for chart in charts.values()} == {prefix + "kserve"}


def test_kserve_uses_standard_mode_without_ingress(kserve):
    get, _, prefix = kserve
    release = get("HelmRelease", "kserve")
    controller = release["spec"]["values"]["kserve"]["controller"]
    assert controller["deploymentMode"] == "Standard"
    assert controller["gateway"]["disableIngressCreation"] is True
    assert {"name": prefix + "kserve-crd"} in release["spec"]["dependsOn"]
    assert {
        get("HelmRelease", name)["spec"]["releaseName"] for name in ("kserve-crd", "kserve")
    } == {
        "kserve-crd",
        "kserve",
    }


def test_kserve_waits_for_the_cert_manager_addon(kserve):
    get, _, _ = kserve
    addon = by_name(render(CERT_MANAGER), "HelmRelease", "cert-manager")
    dependency = {"name": addon["metadata"]["name"], "namespace": addon["metadata"]["namespace"]}
    assert dependency in get("HelmRelease", "kserve")["spec"]["dependsOn"]


def test_cert_manager_is_pinned_and_installs_its_crds():
    addon = by_name(render(CERT_MANAGER), "HelmRelease", "cert-manager")
    chart = addon["spec"]["chart"]["spec"]
    assert chart["version"] == CERT_MANAGER_VERSION
    assert addon["spec"]["values"]["crds"] == {"enabled": True, "keep": True}
    sources = yaml.safe_load_all(
        (ROOT / "gitops/infrastructure/sources/helm-repository.yaml").read_text()
    )
    names = {(s["metadata"]["name"], s["metadata"]["namespace"]) for s in sources if s}
    assert (chart["sourceRef"]["name"], chart["sourceRef"]["namespace"]) in names
    addons = yaml.safe_load((CERT_MANAGER.parent / "kustomization.yaml").read_text())
    assert "cert-manager" in addons["resources"]


def test_predictors_run_without_api_credentials(kserve):
    get, resources, _ = kserve
    account = get("ServiceAccount", "model-predictor")
    assert account["metadata"]["namespace"] == "models"
    assert account["automountServiceAccountToken"] is False
    assert not [r for r in resources if r["kind"] == "Secret"]


def namespace_selectors(policy):
    rules = policy["spec"].get("ingress", []) + policy["spec"].get("egress", [])
    for rule in rules:
        for peer in rule.get("from", []) + rule.get("to", []):
            if "namespaceSelector" in peer:
                yield peer["namespaceSelector"]["matchLabels"]


def test_network_policies_select_namespaces_by_their_builtin_label(kserve):
    _, resources, _ = kserve
    policies = [r for r in resources if r["kind"] == "NetworkPolicy"]
    assert policies
    for policy in policies:
        for labels in namespace_selectors(policy):
            assert list(labels) == ["kubernetes.io/metadata.name"], policy["metadata"]["name"]


def test_predictors_only_reach_mlflow_and_dns(kserve):
    get, _, _ = kserve
    policy = get("NetworkPolicy", "model-predictors")
    assert policy["metadata"]["namespace"] == "models"
    assert policy["spec"]["podSelector"] == {
        "matchExpressions": [{"key": "serving.kserve.io/inferenceservice", "operator": "Exists"}]
    }
    egress = {
        (
            rule["to"][0]["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"],
            port["port"],
        )
        for rule in policy["spec"]["egress"]
        for port in rule["ports"]
    }
    assert egress == {("mlflow", 5000), ("kube-system", 53)}
    ingress_ports = {port["port"] for rule in policy["spec"]["ingress"] for port in rule["ports"]}
    assert ingress_ports == {8080}
