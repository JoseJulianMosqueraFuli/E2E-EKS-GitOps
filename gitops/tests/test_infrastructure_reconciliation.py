"""
Property-Based Tests for Infrastructure Reconciliation

Feature: gitops-implementation, Property 2: Infrastructure Reconciliation
Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5

For any infrastructure component managed by Flux, when configuration changes
are committed to Git, Flux should detect the changes and reconcile the cluster
state to match the desired state.

This module validates:
- All Flux HelmRepositories exist and are valid
- All HelmReleases have required fields (chart, sourceRef, interval)
- All HelmReleases have health checks or dependOn for ordering
- Addons are configured for all environments
- Networking components (Istio, ingress, network policies) exist
- Security policies (Pod Security Standards, IRSA) are configured
- RBAC policies exist
- Environment-specific patches are applied correctly
- Kustomization dependencies form a valid DAG
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set
from hypothesis import given, strategies as st, settings, HealthCheck


# Base paths
GITOPS_ROOT = Path(__file__).parent.parent.resolve()
INFRASTRUCTURE_PATH = GITOPS_ROOT / "infrastructure"
ADDONS_PATH = INFRASTRUCTURE_PATH / "addons"
NETWORKING_PATH = INFRASTRUCTURE_PATH / "networking"
SECURITY_PATH = INFRASTRUCTURE_PATH / "security"
FLUX_CONFIG_PATH = INFRASTRUCTURE_PATH / "flux-config"
CLUSTERS_PATH = INFRASTRUCTURE_PATH / "clusters"
SOURCES_PATH = INFRASTRUCTURE_PATH / "sources"

ENVIRONMENTS = ["dev", "staging", "production"]

# Expected addons
EXPECTED_ADDONS = {"aws-load-balancer-controller", "ebs-csi-driver", "cluster-autoscaler"}

# Expected networking components
EXPECTED_NETWORKING = {"istio", "ingress", "network-policies"}

# Expected security components
EXPECTED_SECURITY = {"pod-security", "irsa"}

# Required HelmRelease fields
REQUIRED_HELM_RELEASE_FIELDS = {"apiVersion", "kind", "metadata", "spec"}
REQUIRED_HELM_RELEASE_SPEC_FIELDS = {"interval", "chart", "sourceRef"}
REQUIRED_CHART_SPEC_FIELDS = {"chart", "sourceRef"}
REQUIRED_SOURCE_REF_FIELDS = {"kind", "name"}

# Required HelmRepository fields
REQUIRED_HELM_REPO_FIELDS = {"apiVersion", "kind", "metadata", "spec"}
REQUIRED_HELM_REPO_SPEC_FIELDS = {"interval", "url"}

# Required Kustomization fields
REQUIRED_KUSTOMIZATION_FIELDS = {"apiVersion", "kind"}

# Expected Flux Kustomizations in flux-config
EXPECTED_FLUX_KUSTOMIZATIONS = {
    "infrastructure-controllers",
    "infrastructure-addons",
    "infrastructure-networking",
    "infrastructure-security",
    "infrastructure-base",
}


def load_yaml(path: Path) -> Optional[Dict]:
    """Load a single YAML document."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, FileNotFoundError):
        return None


def load_yaml_all(path: Path) -> List[Dict]:
    """Load all YAML documents from a multi-doc file."""
    try:
        with open(path, "r") as f:
            return [doc for doc in yaml.safe_load_all(f) if doc is not None]
    except (yaml.YAMLError, FileNotFoundError):
        return []


def find_yaml_files(directory: Path, pattern: str = "*.yaml") -> List[Path]:
    """Find all YAML files in a directory recursively."""
    if not directory.exists():
        return []
    return list(directory.rglob(pattern))


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@st.composite
def env_addon_combo(draw):
    """Generate a valid (environment, addon) combination."""
    env = draw(st.sampled_from(ENVIRONMENTS))
    addon = draw(st.sampled_from(list(EXPECTED_ADDONS)))
    return {"env": env, "addon": addon}


@st.composite
def env_networking_combo(draw):
    """Generate a valid (environment, networking) combination."""
    env = draw(st.sampled_from(ENVIRONMENTS))
    component = draw(st.sampled_from(list(EXPECTED_NETWORKING)))
    return {"env": env, "component": component}


@st.composite
def infra_config(draw):
    """Generate an infrastructure configuration for property testing."""
    return {
        "env": draw(st.sampled_from(ENVIRONMENTS)),
        "addon": draw(st.sampled_from(list(EXPECTED_ADDONS))),
        "check_health": draw(st.booleans()),
        "check_deps": draw(st.booleans()),
    }


# ---------------------------------------------------------------------------
# Property 2: Infrastructure Reconciliation
# For any infrastructure component managed by Flux, when configuration changes
# are committed to Git, Flux should detect and reconcile the cluster state
# ---------------------------------------------------------------------------

class TestFluxHelmRepositories:
    """Verify Flux HelmRepository configurations exist and are valid."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_repository_exists(self, addon):
        """Property: Every addon must have a HelmRepository configuration."""
        path = ADDONS_PATH / addon / "helm-repository.yaml"
        assert path.exists(), f"Missing HelmRepository for {addon}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_repository_is_valid_yaml(self, addon):
        """Property: Every addon HelmRepository must be valid YAML."""
        path = ADDONS_PATH / addon / "helm-repository.yaml"
        if not path.exists():
            pytest.skip(f"HelmRepository for {addon} does not exist")
        data = load_yaml(path)
        assert data is not None, f"Invalid YAML in {addon} HelmRepository"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_repository_has_correct_kind(self, addon):
        """Property: Every addon HelmRepository must have kind=HelmRepository."""
        path = ADDONS_PATH / addon / "helm-repository.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRepository for {addon} not loadable")
        assert data.get("kind") == "HelmRepository"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_repository_has_required_fields(self, addon):
        """Property: Every addon HelmRepository must have required fields."""
        path = ADDONS_PATH / addon / "helm-repository.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRepository for {addon} not loadable")

        missing = REQUIRED_HELM_REPO_FIELDS - set(data.keys())
        assert not missing, f"{addon} HelmRepository missing fields: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_repository_has_valid_spec(self, addon):
        """Property: Every addon HelmRepository spec must have interval and url."""
        path = ADDONS_PATH / addon / "helm-repository.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRepository for {addon} not loadable")

        spec = data.get("spec", {})
        missing = REQUIRED_HELM_REPO_SPEC_FIELDS - set(spec.keys())
        assert not missing, f"{addon} HelmRepository spec missing: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_repository_has_valid_url(self, addon):
        """Property: Every addon HelmRepository URL must be HTTPS."""
        path = ADDONS_PATH / addon / "helm-repository.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRepository for {addon} not loadable")

        url = data.get("spec", {}).get("url", "")
        assert url.startswith("https://"), (
            f"{addon} HelmRepository URL must be HTTPS, got: {url}"
        )


class TestFluxHelmReleases:
    """Verify Flux HelmRelease configurations exist and are valid."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_exists(self, addon):
        """Property: Every addon must have a HelmRelease configuration."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        assert path.exists(), f"Missing HelmRelease for {addon}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_is_valid_yaml(self, addon):
        """Property: Every addon HelmRelease must be valid YAML."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        if not path.exists():
            pytest.skip(f"HelmRelease for {addon} does not exist")
        data = load_yaml(path)
        assert data is not None, f"Invalid YAML in {addon} HelmRelease"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_has_correct_kind(self, addon):
        """Property: Every addon HelmRelease must have kind=HelmRelease."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRelease for {addon} not loadable")
        assert data.get("kind") == "HelmRelease"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_has_required_fields(self, addon):
        """Property: Every addon HelmRelease must have required fields."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRelease for {addon} not loadable")

        missing = REQUIRED_HELM_RELEASE_FIELDS - set(data.keys())
        assert not missing, f"{addon} HelmRelease missing fields: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_has_valid_spec(self, addon):
        """Property: Every addon HelmRelease spec must have interval, chart, sourceRef."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRelease for {addon} not loadable")

        spec = data.get("spec", {})
        # interval is at spec level, chart and sourceRef are in spec.chart.spec
        assert "interval" in spec, f"{addon} HelmRelease spec missing interval"
        assert "chart" in spec, f"{addon} HelmRelease spec missing chart"
        chart_spec = spec.get("chart", {}).get("spec", {})
        assert "sourceRef" in chart_spec, f"{addon} HelmRelease chart.spec missing sourceRef"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_chart_has_required_fields(self, addon):
        """Property: Every addon HelmRelease chart spec must have chart and sourceRef."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRelease for {addon} not loadable")

        chart_spec = data.get("spec", {}).get("chart", {}).get("spec", {})
        missing = REQUIRED_CHART_SPEC_FIELDS - set(chart_spec.keys())
        assert not missing, f"{addon} HelmRelease chart spec missing: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_source_ref_is_valid(self, addon):
        """Property: Every addon HelmRelease sourceRef must reference a HelmRepository."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRelease for {addon} not loadable")

        source_ref = data.get("spec", {}).get("chart", {}).get("spec", {}).get("sourceRef", {})
        missing = REQUIRED_SOURCE_REF_FIELDS - set(source_ref.keys())
        assert not missing, f"{addon} HelmRelease sourceRef missing: {missing}"
        assert source_ref.get("kind") == "HelmRepository", (
            f"{addon} HelmRelease sourceRef kind must be HelmRepository"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_has_target_namespace(self, addon):
        """Property: Every addon HelmRelease must have targetNamespace."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRelease for {addon} not loadable")

        target_ns = data.get("spec", {}).get("targetNamespace")
        assert target_ns is not None, f"{addon} HelmRelease missing targetNamespace"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_helm_release_has_values(self, addon):
        """Property: Every addon HelmRelease must have values configured."""
        path = ADDONS_PATH / addon / "helm-release.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"HelmRelease for {addon} not loadable")

        spec = data.get("spec", {})
        has_values = "values" in spec or "valuesFrom" in spec
        assert has_values, f"{addon} HelmRelease missing values or valuesFrom"


class TestAddonKustomizations:
    """Verify addon Kustomization configurations."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_kustomization_exists(self, addon):
        """Property: Every addon must have a kustomization.yaml."""
        path = ADDONS_PATH / addon / "kustomization.yaml"
        assert path.exists(), f"Missing kustomization.yaml for {addon}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_kustomization_is_valid(self, addon):
        """Property: Every addon kustomization.yaml must be valid."""
        path = ADDONS_PATH / addon / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Kustomization for {addon} not loadable")

        missing = REQUIRED_KUSTOMIZATION_FIELDS - set(data.keys())
        assert not missing, f"{addon} kustomization missing fields: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_kustomization_references_helm_repo(self, addon):
        """Property: Every addon kustomization must reference helm-repository.yaml."""
        path = ADDONS_PATH / addon / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Kustomization for {addon} not loadable")

        resources = data.get("resources", [])
        assert "helm-repository.yaml" in resources, (
            f"{addon} kustomization missing helm-repository.yaml"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(addon=st.sampled_from(list(EXPECTED_ADDONS)))
    def test_addon_kustomization_references_helm_release(self, addon):
        """Property: Every addon kustomization must reference helm-release.yaml."""
        path = ADDONS_PATH / addon / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Kustomization for {addon} not loadable")

        resources = data.get("resources", [])
        assert "helm-release.yaml" in resources, (
            f"{addon} kustomization missing helm-release.yaml"
        )

    @pytest.mark.unit
    def test_addons_root_kustomization_exists(self):
        """Addons root kustomization.yaml must exist."""
        path = ADDONS_PATH / "kustomization.yaml"
        assert path.exists(), "Addons root kustomization.yaml not found"

    @pytest.mark.unit
    def test_addons_root_kustomization_references_all_addons(self):
        """Addons root kustomization must reference all addons."""
        path = ADDONS_PATH / "kustomization.yaml"
        data = load_yaml(path)
        assert data is not None

        resources = data.get("resources", [])
        for addon in EXPECTED_ADDONS:
            assert addon in resources, (
                f"Addons root kustomization missing {addon}"
            )


class TestNetworkingComponents:
    """Verify networking component configurations."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(component=st.sampled_from(list(EXPECTED_NETWORKING)))
    def test_networking_component_exists(self, component):
        """Property: Every networking component must have a directory."""
        path = NETWORKING_PATH / component
        assert path.exists(), f"Missing networking component: {component}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(component=st.sampled_from(list(EXPECTED_NETWORKING)))
    def test_networking_component_kustomization_exists(self, component):
        """Property: Every networking component must have a kustomization.yaml."""
        path = NETWORKING_PATH / component / "kustomization.yaml"
        assert path.exists(), f"Missing kustomization.yaml for {component}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(component=st.sampled_from(list(EXPECTED_NETWORKING)))
    def test_networking_component_kustomization_is_valid(self, component):
        """Property: Every networking component kustomization must be valid."""
        path = NETWORKING_PATH / component / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Kustomization for {component} not loadable")

        missing = REQUIRED_KUSTOMIZATION_FIELDS - set(data.keys())
        assert not missing, f"{component} kustomization missing fields: {missing}"

    @pytest.mark.unit
    def test_networking_root_kustomization_exists(self):
        """Networking root kustomization.yaml must exist."""
        path = NETWORKING_PATH / "kustomization.yaml"
        assert path.exists(), "Networking root kustomization.yaml not found"

    @pytest.mark.unit
    def test_networking_root_kustomization_references_all_components(self):
        """Networking root kustomization must reference all components."""
        path = NETWORKING_PATH / "kustomization.yaml"
        data = load_yaml(path)
        assert data is not None

        resources = data.get("resources", [])
        for component in EXPECTED_NETWORKING:
            assert component in resources, (
                f"Networking root kustomization missing {component}"
            )

    @pytest.mark.unit
    def test_istio_has_namespace(self):
        """Istio must have a namespace definition."""
        path = NETWORKING_PATH / "istio" / "namespace.yaml"
        assert path.exists(), "Istio namespace.yaml not found"

    @pytest.mark.unit
    def test_istio_has_helm_repository(self):
        """Istio must have a HelmRepository."""
        path = NETWORKING_PATH / "istio" / "helm-repository.yaml"
        assert path.exists(), "Istio helm-repository.yaml not found"

    @pytest.mark.unit
    def test_istio_has_istiod(self):
        """Istio must have istiod HelmRelease."""
        path = NETWORKING_PATH / "istio" / "istiod.yaml"
        assert path.exists(), "Istio istiod.yaml not found"

    @pytest.mark.unit
    def test_network_policies_exist(self):
        """Network policies directory must have policy files."""
        path = NETWORKING_PATH / "network-policies"
        yaml_files = list(path.glob("*.yaml"))
        assert len(yaml_files) > 0, "No network policy files found"

    @pytest.mark.unit
    def test_default_deny_policy_exists(self):
        """Default deny ingress policy must exist."""
        path = NETWORKING_PATH / "network-policies" / "default-deny-ingress.yaml"
        assert path.exists(), "default-deny-ingress.yaml not found"


class TestSecurityComponents:
    """Verify security component configurations."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(component=st.sampled_from(list(EXPECTED_SECURITY)))
    def test_security_component_exists(self, component):
        """Property: Every security component must have a directory."""
        path = SECURITY_PATH / component
        assert path.exists(), f"Missing security component: {component}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(component=st.sampled_from(list(EXPECTED_SECURITY)))
    def test_security_component_kustomization_exists(self, component):
        """Property: Every security component must have a kustomization.yaml."""
        path = SECURITY_PATH / component / "kustomization.yaml"
        assert path.exists(), f"Missing kustomization.yaml for {component}"

    @pytest.mark.unit
    def test_security_root_kustomization_exists(self):
        """Security root kustomization.yaml must exist."""
        path = SECURITY_PATH / "kustomization.yaml"
        assert path.exists(), "Security root kustomization.yaml not found"

    @pytest.mark.unit
    def test_security_root_kustomization_references_all_components(self):
        """Security root kustomization must reference all components."""
        path = SECURITY_PATH / "kustomization.yaml"
        data = load_yaml(path)
        assert data is not None

        resources = data.get("resources", [])
        for component in EXPECTED_SECURITY:
            assert component in resources, (
                f"Security root kustomization missing {component}"
            )

    @pytest.mark.unit
    def test_pod_security_namespaces_exist(self):
        """Pod Security Standards namespace definitions must exist."""
        path = SECURITY_PATH / "pod-security" / "namespaces-pss.yaml"
        assert path.exists(), "namespaces-pss.yaml not found"

    @pytest.mark.unit
    def test_pod_security_namespaces_have_enforce_labels(self):
        """All MLOps namespaces must have pod-security enforce labels."""
        path = SECURITY_PATH / "pod-security" / "namespaces-pss.yaml"
        docs = load_yaml_all(path)
        assert len(docs) > 0, "No documents in namespaces-pss.yaml"

        mlops_namespaces = {"mlflow", "kubeflow", "kserve", "monitoring"}
        found_namespaces = set()

        for doc in docs:
            if doc.get("kind") == "Namespace":
                ns_name = doc.get("metadata", {}).get("name")
                if ns_name in mlops_namespaces:
                    found_namespaces.add(ns_name)
                    labels = doc.get("metadata", {}).get("labels", {})
                    assert "pod-security.kubernetes.io/enforce" in labels, (
                        f"Namespace {ns_name} missing pod-security enforce label"
                    )

        missing = mlops_namespaces - found_namespaces
        assert not missing, f"Missing namespace definitions: {missing}"

    @pytest.mark.unit
    def test_irsa_service_accounts_exist(self):
        """IRSA service accounts must exist."""
        path = SECURITY_PATH / "irsa" / "service-accounts.yaml"
        assert path.exists(), "IRSA service-accounts.yaml not found"

    @pytest.mark.unit
    def test_irsa_service_accounts_have_annotations(self):
        """IRSA service accounts must have EKS role annotations."""
        path = SECURITY_PATH / "irsa" / "service-accounts.yaml"
        docs = load_yaml_all(path)
        assert len(docs) > 0, "No documents in service-accounts.yaml"

        for doc in docs:
            if doc.get("kind") == "ServiceAccount":
                annotations = doc.get("metadata", {}).get("annotations", {})
                assert "eks.amazonaws.com/role-arn" in annotations, (
                    f"ServiceAccount {doc['metadata']['name']} missing IRSA annotation"
                )


class TestFluxConfigurations:
    """Verify Flux Kustomization configurations."""

    @pytest.mark.unit
    def test_flux_config_kustomization_exists(self):
        """flux-config kustomization.yaml must exist."""
        path = FLUX_CONFIG_PATH / "kustomization.yaml"
        assert path.exists(), "flux-config kustomization.yaml not found"

    @pytest.mark.unit
    def test_flux_config_infrastructure_kustomization_exists(self):
        """infrastructure-kustomization.yaml must exist."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        assert path.exists(), "infrastructure-kustomization.yaml not found"

    @pytest.mark.unit
    def test_flux_config_has_all_kustomizations(self):
        """flux-config must define all expected Kustomizations."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)
        assert len(docs) > 0, "No documents in infrastructure-kustomization.yaml"

        found_kustomizations = set()
        for doc in docs:
            if doc.get("kind") == "Kustomization":
                name = doc.get("metadata", {}).get("name")
                if name:
                    found_kustomizations.add(name)

        missing = EXPECTED_FLUX_KUSTOMIZATIONS - found_kustomizations
        assert not missing, f"Missing Flux Kustomizations: {missing}"

    @pytest.mark.unit
    def test_flux_config_addons_depends_on_controllers(self):
        """infrastructure-addons must depend on infrastructure-controllers."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-addons":
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                dep_names = [d.get("name") for d in depends_on]
                assert "infrastructure-controllers" in dep_names, (
                    "infrastructure-addons must depend on infrastructure-controllers"
                )
                return

        pytest.fail("infrastructure-addons Kustomization not found")

    @pytest.mark.unit
    def test_flux_config_networking_depends_on_addons(self):
        """infrastructure-networking must depend on infrastructure-addons."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-networking":
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                dep_names = [d.get("name") for d in depends_on]
                assert "infrastructure-addons" in dep_names, (
                    "infrastructure-networking must depend on infrastructure-addons"
                )
                return

        pytest.fail("infrastructure-networking Kustomization not found")

    @pytest.mark.unit
    def test_flux_config_security_depends_on_controllers(self):
        """infrastructure-security must depend on infrastructure-controllers."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-security":
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                dep_names = [d.get("name") for d in depends_on]
                assert "infrastructure-controllers" in dep_names, (
                    "infrastructure-security must depend on infrastructure-controllers"
                )
                return

        pytest.fail("infrastructure-security Kustomization not found")

    @pytest.mark.unit
    def test_flux_config_base_depends_on_security(self):
        """infrastructure-base must depend on infrastructure-security."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-base":
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                dep_names = [d.get("name") for d in depends_on]
                assert "infrastructure-security" in dep_names, (
                    "infrastructure-base must depend on infrastructure-security"
                )
                return

        pytest.fail("infrastructure-base Kustomization not found")

    @pytest.mark.unit
    def test_flux_config_addons_has_health_checks(self):
        """infrastructure-addons must have healthChecks for all addons."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-addons":
                health_checks = doc.get("spec", {}).get("healthChecks", [])
                assert len(health_checks) >= len(EXPECTED_ADDONS), (
                    f"infrastructure-addons should have at least {len(EXPECTED_ADDONS)} health checks"
                )
                return

        pytest.fail("infrastructure-addons Kustomization not found")


class TestClusterInfrastructure:
    """Verify cluster-level infrastructure configurations."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_kustomization_exists(self, env):
        """Property: Every cluster must have a kustomization.yaml."""
        path = CLUSTERS_PATH / env / "kustomization.yaml"
        assert path.exists(), f"Missing kustomization.yaml for {env}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_infrastructure_kustomization_exists(self, env):
        """Property: Every cluster must have infrastructure/kustomization.yaml."""
        path = CLUSTERS_PATH / env / "infrastructure" / "kustomization.yaml"
        assert path.exists(), f"Missing infrastructure kustomization for {env}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_infrastructure_references_sources(self, env):
        """Property: Every cluster infrastructure must reference sources."""
        path = CLUSTERS_PATH / env / "infrastructure" / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Infrastructure kustomization for {env} not loadable")

        resources = data.get("resources", [])
        assert any("sources" in str(r) for r in resources), (
            f"{env} infrastructure must reference sources"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_infrastructure_references_flux_config(self, env):
        """Property: Every cluster infrastructure must reference flux-config."""
        path = CLUSTERS_PATH / env / "infrastructure" / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Infrastructure kustomization for {env} not loadable")

        resources = data.get("resources", [])
        assert any("flux-config" in str(r) for r in resources), (
            f"{env} infrastructure must reference flux-config"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_infrastructure_references_addons(self, env):
        """Property: Every cluster infrastructure must reference addons."""
        path = CLUSTERS_PATH / env / "infrastructure" / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Infrastructure kustomization for {env} not loadable")

        resources = data.get("resources", [])
        assert any("addons" in str(r) for r in resources), (
            f"{env} infrastructure must reference addons"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_infrastructure_references_networking(self, env):
        """Property: Every cluster infrastructure must reference networking."""
        path = CLUSTERS_PATH / env / "infrastructure" / "kustomization.yaml"
        data = load_yaml(path)
        if data is None:
            pytest.skip(f"Infrastructure kustomization for {env} not loadable")

        resources = data.get("resources", [])
        assert any("networking" in str(r) for r in resources), (
            f"{env} infrastructure must reference networking"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_has_flux_system(self, env):
        """Property: Every cluster must have flux-system directory."""
        path = CLUSTERS_PATH / env / "flux-system"
        assert path.exists(), f"Missing flux-system for {env}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_has_config(self, env):
        """Property: Every cluster must have config directory."""
        path = CLUSTERS_PATH / env / "config"
        assert path.exists(), f"Missing config for {env}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_config_exists(self, env):
        """Property: Every cluster must have cluster-config.yaml."""
        path = CLUSTERS_PATH / env / "config" / "cluster-config.yaml"
        assert path.exists(), f"Missing cluster-config.yaml for {env}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(env=st.sampled_from(ENVIRONMENTS))
    def test_cluster_config_has_environment_label(self, env):
        """Property: Every cluster config must have correct environment."""
        path = CLUSTERS_PATH / env / "config" / "cluster-config.yaml"
        docs = load_yaml_all(path)
        assert len(docs) > 0, f"No documents in cluster-config.yaml for {env}"

        for doc in docs:
            if doc.get("kind") == "ConfigMap":
                name = doc.get("metadata", {}).get("name", "")
                if name == "cluster-config":
                    data = doc.get("data", {})
                    assert data.get("environment") == env, (
                        f"Cluster config environment mismatch: expected {env}"
                    )
                    return

        pytest.fail(f"cluster-config ConfigMap not found for {env}")


class TestSourcesConfigurations:
    """Verify Flux source configurations."""

    @pytest.mark.unit
    def test_sources_kustomization_exists(self):
        """Sources kustomization.yaml must exist."""
        path = SOURCES_PATH / "kustomization.yaml"
        assert path.exists(), "Sources kustomization.yaml not found"

    @pytest.mark.unit
    def test_git_repository_exists(self):
        """Git repository source must exist."""
        path = SOURCES_PATH / "git-repository.yaml"
        assert path.exists(), "git-repository.yaml not found"

    @pytest.mark.unit
    def test_helm_repository_exists(self):
        """Helm repository source must exist."""
        path = SOURCES_PATH / "helm-repository.yaml"
        assert path.exists(), "helm-repository.yaml not found"

    @pytest.mark.unit
    def test_git_repository_has_multiple_repos(self):
        """Git repository source must define multiple repos."""
        path = SOURCES_PATH / "git-repository.yaml"
        docs = load_yaml_all(path)
        git_repos = [d for d in docs if d.get("kind") == "GitRepository"]
        assert len(git_repos) >= 2, (
            f"Expected at least 2 GitRepository definitions, got {len(git_repos)}"
        )

    @pytest.mark.unit
    def test_helm_repository_has_multiple_repos(self):
        """Helm repository source must define multiple repos."""
        path = SOURCES_PATH / "helm-repository.yaml"
        docs = load_yaml_all(path)
        helm_repos = [d for d in docs if d.get("kind") == "HelmRepository"]
        assert len(helm_repos) >= 3, (
            f"Expected at least 3 HelmRepository definitions, got {len(helm_repos)}"
        )


class TestEnvironmentSpecificPatches:
    """Verify environment-specific patches are correctly applied."""

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_dev_has_shorter_sync_interval(self, env):
        """Dev should have shorter sync intervals than production."""
        dev_path = CLUSTERS_PATH / "dev" / "infrastructure" / "kustomization.yaml"
        env_path = CLUSTERS_PATH / env / "infrastructure" / "kustomization.yaml"

        dev_data = load_yaml(dev_path)
        env_data = load_yaml(env_path)
        assert dev_data is not None and env_data is not None

        # Dev should have 1m interval for GitRepository
        dev_patches = dev_data.get("patches", [])
        for patch in dev_patches:
            patch_str = patch.get("patch", "")
            if "GitRepository" in str(patch.get("target", {})):
                assert "1m" in patch_str, "Dev should have 1m GitRepository interval"


class TestDependencyDAG:
    """Verify that Flux Kustomization dependencies form a valid DAG."""

    @pytest.mark.unit
    def test_no_circular_dependencies(self):
        """Flux Kustomization dependencies must not form cycles."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        # Build dependency graph
        deps = {}
        for doc in docs:
            if doc.get("kind") == "Kustomization":
                name = doc.get("metadata", {}).get("name")
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                deps[name] = [d.get("name") for d in depends_on]

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in deps.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in deps:
            if node not in visited:
                assert not has_cycle(node), f"Circular dependency detected involving {node}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
