import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENTS = ["dev", "staging", "prod"]
APPS = ROOT / "gitops/applications/apps"
OVERLAYS = sorted(p for p in APPS.glob("*/overlays/*") if (p / "kustomization.yaml").exists())
PREFIXES = ("dev-", "staging-", "prod-")
EXEC_ALLOWED = {"argo-workflow-controller", "litmus-stress"}


def read(path):
    return (ROOT / path).read_text()


def block(text, header):
    start = text.index(header)
    end = text.find("\nresource ", start + len(header))
    return text[start:] if end == -1 else text[start:end]


def test_account_baseline_enables_detective_and_preventive_controls():
    account = read("infra/environments/account/main.tf")
    trail = block(account, 'resource "aws_cloudtrail" "account"')
    assert re.search(r"is_multi_region_trail\s*=\s*true", trail)
    assert re.search(r"enable_log_file_validation\s*=\s*true", trail)
    assert re.search(r"kms_key_id\s*=\s*aws_kms_key\.trail\.arn", trail)
    assert re.search(r"enable_key_rotation\s*=\s*true", block(account, 'resource "aws_kms_key"'))
    for control in (
        'resource "aws_s3_account_public_access_block"',
        'resource "aws_ebs_encryption_by_default"',
        'resource "aws_accessanalyzer_analyzer"',
        'resource "aws_guardduty_detector"',
        'resource "aws_budgets_budget"',
    ):
        assert control in account
    assert "aws:SecureTransport" in account
    assert account.count('variable = "aws:SourceArn"') >= 4


def test_eks_uses_access_entries_and_enforces_network_policies():
    eks = read("infra/modules/eks/main.tf")
    assert re.search(r'authentication_mode\s*=\s*"API"', eks)
    assert re.search(r"endpoint_private_access\s*=\s*true", eks)
    assert re.search(r"enableNetworkPolicy\s*=\s*\"true\"", eks)


@pytest.mark.parametrize("env", ENVIRONMENTS)
def test_public_eks_endpoint_is_opt_in_and_never_open_to_the_internet(env):
    main = read(f"infra/environments/{env}/main.tf")
    assert re.search(r"endpoint_public_access\s*=\s*var\.endpoint_public_access", main)
    variables = read(f"infra/environments/{env}/variables.tf")
    endpoint = re.search(r'variable "endpoint_public_access" \{[^}]*\}', variables).group(0)
    assert re.search(r"default\s*=\s*false", endpoint)
    module = read("infra/modules/eks/variables.tf")
    assert 'cidr != "0.0.0.0/0"' in module
    assert "!var.endpoint_public_access || length(var.public_access_cidrs) > 0" in module


def test_cluster_autoscaler_mutates_only_this_clusters_node_groups():
    policy = block(
        read("infra/modules/eks/main.tf"), 'resource "aws_iam_policy" "cluster_autoscaler"'
    )
    statements = policy.split("Effect")
    mutating = [s for s in statements if "SetDesiredCapacity" in s or "TerminateInstance" in s]
    assert mutating and all("Condition" in s for s in mutating)
    assert "k8s.io/cluster-autoscaler/${var.cluster_name}" in policy


def test_argocd_is_not_exposed_to_the_internet():
    ingress = yaml.safe_load(read("gitops/infrastructure/controllers/argocd/ingress.yaml"))
    annotations = ingress["metadata"]["annotations"]
    assert annotations["alb.ingress.kubernetes.io/scheme"] == "internal"


def test_ci_defaults_to_a_read_only_token():
    workflow = yaml.safe_load(read(".github/workflows/ci.yml"))
    assert workflow["permissions"] == {"contents": "read"}


@lru_cache(maxsize=None)
def rendered(overlay):
    output = subprocess.check_output(["kustomize", "build", str(overlay)], text=True)
    return tuple(doc for doc in yaml.safe_load_all(output) if doc)


def base_name(name):
    return next((name[len(p) :] for p in PREFIXES if name.startswith(p)), name)


def rules(overlay):
    for doc in rendered(overlay):
        if doc["kind"] in ("Role", "ClusterRole"):
            for rule in doc.get("rules", []):
                yield doc, rule


@pytest.mark.parametrize("overlay", OVERLAYS, ids=lambda p: f"{p.parts[-3]}-{p.name}")
def test_no_cluster_role_reads_every_secret(overlay):
    for doc, rule in rules(overlay):
        if doc["kind"] == "ClusterRole" and {"secrets", "*"} & set(rule.get("resources", [])):
            assert rule.get("resourceNames"), doc["metadata"]["name"]


@pytest.mark.parametrize("overlay", OVERLAYS, ids=lambda p: f"{p.parts[-3]}-{p.name}")
def test_pod_exec_is_limited_to_justified_roles(overlay):
    for doc, rule in rules(overlay):
        if "pods/exec" in rule.get("resources", []):
            assert base_name(doc["metadata"]["name"]) in EXEC_ALLOWED, doc["metadata"]["name"]
            assert set(rule["verbs"]) <= {"create", "get"}


def pod_specs(overlay):
    for doc in rendered(overlay):
        if doc["kind"] == "CronJob":
            yield doc, doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        elif doc["kind"] in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
            yield doc, doc["spec"]["template"]["spec"]


@pytest.mark.parametrize("overlay", OVERLAYS, ids=lambda p: f"{p.parts[-3]}-{p.name}")
def test_workloads_run_read_only_unprivileged_and_non_root(overlay):
    for doc, spec in pod_specs(overlay):
        pod = spec.get("securityContext", {})
        for container in spec.get("initContainers", []) + spec.get("containers", []):
            context = container.get("securityContext", {})
            where = f'{doc["metadata"]["name"]}/{container["name"]}'
            assert context.get("readOnlyRootFilesystem") is True, where
            assert context.get("allowPrivilegeEscalation") is False, where
            assert "ALL" in context.get("capabilities", {}).get("drop", []), where
            assert context.get("runAsNonRoot", pod.get("runAsNonRoot")) is True, where


def test_scanner_exceptions_name_existing_files_and_a_reason():
    exceptions = yaml.safe_load(read(".trivyignore.yaml"))["misconfigurations"]
    assert exceptions
    for exception in exceptions:
        assert re.fullmatch(r"[A-Z]+-\d{4}", exception["id"])
        assert all((ROOT / path).is_file() for path in exception["paths"])
        assert len(exception["statement"]) > 60


def test_argocd_install_renders_its_patches_in_the_argocd_namespace():
    argocd = ROOT / "gitops/infrastructure/controllers/argocd"
    kustomization = yaml.safe_load((argocd / "kustomization.yaml").read_text())
    assert kustomization["namespace"] == "argocd"
    patches = kustomization["patchesStrategicMerge"]
    assert "rbac-config.yaml" in patches
    assert "rbac-config.yaml" not in kustomization["resources"]
    for patch in patches:
        assert "namespace" not in yaml.safe_load((argocd / patch).read_text())["metadata"]


def test_registries_are_immutable_and_public_subnets_assign_no_addresses():
    assert (
        "condition     = alltrue([for repo in var.repositories : repo.image_tag_mutability == "
        in (read("infra/modules/ecr/variables.tf"))
    )
    for env in ENVIRONMENTS:
        assert 'image_tag_mutability = "MUTABLE"' not in read(f"infra/environments/{env}/main.tf")
    assert re.search(r"map_public_ip_on_launch\s*=\s*false", read("infra/modules/vpc/main.tf"))


def test_images_are_scanned_before_they_reach_ecr():
    steps = yaml.safe_load(read(".github/workflows/publish-ecr.yml"))["jobs"]["publish"]["steps"]
    names = [step.get("name", "") for step in steps]
    push = names.index("Push scanned images")
    scans = [i for i, step in enumerate(steps) if "trivy-action" in step.get("uses", "")]
    assert len(scans) == 3 and max(scans) < push
    assert all(step["with"]["exit-code"] == "1" for step in (steps[i] for i in scans))
    assert not any(step.get("with", {}).get("push") is True for step in steps)
    build = yaml.safe_load(read(".github/workflows/ml-platform-image.yml"))["jobs"]["test"]["steps"]
    assert sum("trivy-action" in step.get("uses", "") for step in build) == 3
