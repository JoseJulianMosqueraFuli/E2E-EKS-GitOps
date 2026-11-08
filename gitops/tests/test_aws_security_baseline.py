import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENTS = ["dev", "staging", "prod"]


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
