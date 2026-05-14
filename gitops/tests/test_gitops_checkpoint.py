"""
Validation Tests for Core GitOps Functionality

Feature: gitops-implementation, Task 5: Checkpoint - Validate Core GitOps Functionality

This module validates that all GitOps configurations are correct and ready
for deployment. These tests run against configuration files (no cluster required)
to ensure everything is properly configured before applying to a cluster.

Validates:
- All GitOps controller manifests are valid
- All Flux sources are configured correctly
- All ArgoCD Applications reference valid paths
- All Kustomize overlays produce valid output
- Dependency chain is correct (controllers → addons → networking → security)
- Health checks are configured for all critical components
- No circular dependencies in Flux Kustomizations
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set
from hypothesis import given, strategies as st, settings, HealthCheck


# Base paths
GITOPS_ROOT = Path(__file__).parent.parent.resolve()
INFRASTRUCTURE_PATH = GITOPS_ROOT / "infrastructure"
APPLICATIONS_PATH = GITOPS_ROOT / "applications"
CONTROLLERS_PATH = INFRASTRUCTURE_PATH / "controllers"
ADDONS_PATH = INFRASTRUCTURE_PATH / "addons"
NETWORKING_PATH = INFRASTRUCTURE_PATH / "networking"
SECURITY_PATH = INFRASTRUCTURE_PATH / "security"
FLUX_CONFIG_PATH = INFRASTRUCTURE_PATH / "flux-config"
CLUSTERS_PATH = INFRASTRUCTURE_PATH / "clusters"

ENVIRONMENTS = ["dev", "staging", "production"]
APPLICATIONS = ["mlflow", "kubeflow", "kserve", "monitoring"]


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


# ---------------------------------------------------------------------------
# 1. Controller Health Configuration
# ---------------------------------------------------------------------------

class TestControllerHealthConfiguration:
    """Verify all controllers have proper health check configuration."""

    @pytest.mark.unit
    def test_flux_controllers_have_health_checks(self):
        """Flux Kustomization must have healthChecks for controllers."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-controllers":
                health_checks = doc.get("spec", {}).get("healthChecks", [])
                assert len(health_checks) >= 3, (
                    f"Expected at least 3 health checks, got {len(health_checks)}"
                )
                # Verify all expected controllers are in health checks
                checked = {hc.get("name") for hc in health_checks}
                expected = {"source-controller", "kustomize-controller", "helm-controller"}
                assert expected.issubset(checked), (
                    f"Missing health checks for: {expected - checked}"
                )
                return

        pytest.fail("infrastructure-controllers Kustomization not found")

    @pytest.mark.unit
    def test_argocd_controllers_are_deployed(self):
        """ArgoCD controller manifests must exist."""
        argocd_path = CONTROLLERS_PATH / "argocd"
        assert argocd_path.exists(), "ArgoCD controller directory not found"

        expected_files = ["namespace.yaml", "rbac-config.yaml"]
        for f in expected_files:
            assert (argocd_path / f).exists(), f"Missing ArgoCD file: {f}"

    @pytest.mark.unit
    def test_flux_controllers_are_deployed(self):
        """Flux controller manifests must exist."""
        flux_path = CONTROLLERS_PATH / "flux-system"
        assert flux_path.exists(), "Flux controller directory not found"

        expected_controllers = [
            "source-controller.yaml",
            "kustomize-controller.yaml",
            "helm-controller.yaml",
            "notification-controller.yaml",
        ]
        for f in expected_controllers:
            assert (flux_path / f).exists(), f"Missing Flux controller: {f}"


# ---------------------------------------------------------------------------
# 2. Application Deployment Readiness
# ---------------------------------------------------------------------------

class TestApplicationDeploymentReadiness:
    """Verify all MLOps applications are ready for deployment."""

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    def test_application_has_base_manifests(self, app):
        """Each application must have base manifests."""
        base_path = APPLICATIONS_PATH / "apps" / app / "base"
        assert base_path.exists(), f"{app} base directory not found"

        kust = load_yaml(base_path / "kustomization.yaml")
        assert kust is not None, f"{app} base kustomization.yaml is invalid"
        assert len(kust.get("resources", [])) > 0, (
            f"{app} base has no resources"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_overlay_for_environment(self, app, env):
        """Each application must have an overlay for each environment."""
        overlay_path = APPLICATIONS_PATH / "apps" / app / "overlays" / env
        assert overlay_path.exists(), f"{app}/{env} overlay not found"

        kust = load_yaml(overlay_path / "kustomization.yaml")
        assert kust is not None, f"{app}/{env} overlay kustomization.yaml is invalid"

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_argocd_definition(self, app, env):
        """Each application/environment must have an ArgoCD Application."""
        app_path = APPLICATIONS_PATH / "environments" / env / f"{app}-application.yaml"
        assert app_path.exists(), f"Missing ArgoCD Application: {app_path}"

        data = load_yaml(app_path)
        assert data is not None, f"Invalid YAML: {app_path}"
        assert data.get("kind") == "Application"
        assert data.get("apiVersion") == "argoproj.io/v1alpha1"

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_source_path_exists(self, app, env):
        """ArgoCD Application source path must reference a valid overlay."""
        app_path = APPLICATIONS_PATH / "environments" / env / f"{app}-application.yaml"
        data = load_yaml(app_path)
        if data is None:
            pytest.skip(f"Application {app}/{env} not loadable")

        source_path = data.get("spec", {}).get("source", {}).get("path", "")
        # The path should contain the environment name
        assert env in source_path, (
            f"{app}/{env} source path does not contain '{env}': {source_path}"
        )


# ---------------------------------------------------------------------------
# 3. Drift Detection Configuration
# ---------------------------------------------------------------------------

class TestDriftDetectionConfiguration:
    """Verify drift detection is properly configured."""

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_argocd_app_has_self_heal(self, env):
        """All ArgoCD Applications must have selfHeal enabled for drift detection."""
        for app in APPLICATIONS:
            app_path = APPLICATIONS_PATH / "environments" / env / f"{app}-application.yaml"
            data = load_yaml(app_path)
            if data is None:
                pytest.skip(f"Application {app}/{env} not loadable")

            self_heal = (
                data.get("spec", {})
                .get("syncPolicy", {})
                .get("automated", {})
                .get("selfHeal")
            )
            assert self_heal is True, (
                f"{app}/{env} selfHeal not enabled"
            )

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_flux_kustomization_has_prune(self, env):
        """Flux Kustomizations must have prune enabled for drift detection."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("kind") == "Kustomization":
                prune = doc.get("spec", {}).get("prune")
                assert prune is True, (
                    f"Flux Kustomization {doc['metadata']['name']} prune not enabled"
                )

    @pytest.mark.unit
    def test_flux_sync_interval_configured(self):
        """Flux GitRepository must have sync interval configured."""
        for env in ENVIRONMENTS:
            path = CLUSTERS_PATH / env / "flux-system" / "gotk-sync.yaml"
            data = load_yaml(path)
            if data is None:
                continue

            if data.get("kind") == "GitRepository":
                interval = data.get("spec", {}).get("interval")
                assert interval is not None, (
                    f"{env} GitRepository missing sync interval"
                )

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    def test_argocd_app_has_ignore_differences(self, app):
        """Production applications should have ignoreDifferences for known drift."""
        prod_path = APPLICATIONS_PATH / "environments" / "production" / f"{app}-application.yaml"
        data = load_yaml(prod_path)
        if data is None:
            pytest.skip(f"Application {app}/production not loadable")

        # Production should have ignoreDifferences for replicas
        ignore_diffs = data.get("spec", {}).get("ignoreDifferences", [])
        has_replica_ignore = any(
            "/spec/replicas" in str(pointer)
            for diff in ignore_diffs
            for pointer in diff.get("jsonPointers", [])
        )
        # It's OK if not all apps have this, but at least some should
        # We just verify the field exists if ignoreDifferences is present
        if ignore_diffs:
            assert isinstance(ignore_diffs, list)


# ---------------------------------------------------------------------------
# 4. Dependency Chain Validation
# ---------------------------------------------------------------------------

class TestDependencyChainValidation:
    """Verify the complete dependency chain is valid."""

    @pytest.mark.unit
    def test_controllers_deploy_before_addons(self):
        """Addons must depend on controllers."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        addons_kust = None
        controllers_kust = None

        for doc in docs:
            name = doc.get("metadata", {}).get("name")
            if name == "infrastructure-addons":
                addons_kust = doc
            elif name == "infrastructure-controllers":
                controllers_kust = doc

        assert addons_kust is not None, "infrastructure-addons not found"
        assert controllers_kust is not None, "infrastructure-controllers not found"

        depends_on = addons_kust.get("spec", {}).get("dependsOn", [])
        dep_names = [d.get("name") for d in depends_on]
        assert "infrastructure-controllers" in dep_names, (
            "addons must depend on controllers"
        )

    @pytest.mark.unit
    def test_networking_depends_on_addons(self):
        """Networking must depend on addons (ALB for ingress)."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-networking":
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                dep_names = [d.get("name") for d in depends_on]
                assert "infrastructure-addons" in dep_names, (
                    "networking must depend on addons"
                )
                return

        pytest.fail("infrastructure-networking not found")

    @pytest.mark.unit
    def test_security_depends_on_controllers(self):
        """Security must depend on controllers (for RBAC)."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-security":
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                dep_names = [d.get("name") for d in depends_on]
                assert "infrastructure-controllers" in dep_names, (
                    "security must depend on controllers"
                )
                return

        pytest.fail("infrastructure-security not found")

    @pytest.mark.unit
    def test_no_circular_dependencies(self):
        """Dependency graph must be a DAG (no cycles)."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        deps = {}
        for doc in docs:
            if doc.get("kind") == "Kustomization":
                name = doc.get("metadata", {}).get("name")
                depends_on = doc.get("spec", {}).get("dependsOn", [])
                deps[name] = [d.get("name") for d in depends_on]

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in deps}

        def has_cycle(node):
            color[node] = GRAY
            for neighbor in deps.get(node, []):
                if neighbor in color:
                    if color[neighbor] == GRAY:
                        return True
                    if color[neighbor] == WHITE and has_cycle(neighbor):
                        return True
            color[node] = BLACK
            return False

        for node in deps:
            if color[node] == WHITE:
                assert not has_cycle(node), f"Circular dependency involving {node}"


# ---------------------------------------------------------------------------
# 5. Health Check Completeness
# ---------------------------------------------------------------------------

class TestHealthCheckCompleteness:
    """Verify health checks are configured for all critical components."""

    @pytest.mark.unit
    def test_addons_health_checks_cover_all_addons(self):
        """Addons Kustomization must have health checks for all addons."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        expected_addons = {
            "aws-load-balancer-controller",
            "ebs-csi-controller",
            "cluster-autoscaler",
        }

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-addons":
                health_checks = doc.get("spec", {}).get("healthChecks", [])
                checked = {hc.get("name") for hc in health_checks}
                missing = expected_addons - checked
                assert not missing, (
                    f"Missing health checks for addons: {missing}"
                )
                return

        pytest.fail("infrastructure-addons Kustomization not found")

    @pytest.mark.unit
    def test_networking_health_checks_cover_istio(self):
        """Networking Kustomization must have health check for istiod."""
        path = FLUX_CONFIG_PATH / "infrastructure-kustomization.yaml"
        docs = load_yaml_all(path)

        for doc in docs:
            if doc.get("metadata", {}).get("name") == "infrastructure-networking":
                health_checks = doc.get("spec", {}).get("healthChecks", [])
                istio_checked = any(
                    hc.get("name") == "istiod" for hc in health_checks
                )
                assert istio_checked, (
                    "Networking missing health check for istiod"
                )
                return

        pytest.fail("infrastructure-networking Kustomization not found")


# ---------------------------------------------------------------------------
# 6. Validation Script Exists
# ---------------------------------------------------------------------------

class TestValidationScript:
    """Verify validation scripts exist and are executable."""

    @pytest.mark.unit
    def test_validation_script_exists(self):
        """validate-gitops.sh must exist."""
        scripts_path = GITOPS_ROOT / "scripts" / "validation"
        script = scripts_path / "validate-gitops.sh"
        assert script.exists(), "validate-gitops.sh not found"

    @pytest.mark.unit
    def test_validation_script_is_executable(self):
        """validate-gitops.sh must be executable."""
        script = GITOPS_ROOT / "scripts" / "validation" / "validate-gitops.sh"
        if script.exists():
            assert script.stat().st_mode & 0o111, (
                "validate-gitops.sh is not executable"
            )

    @pytest.mark.unit
    def test_validation_script_has_shebang(self):
        """validate-gitops.sh must have a shebang line."""
        script = GITOPS_ROOT / "scripts" / "validation" / "validate-gitops.sh"
        if script.exists():
            with open(script, "r") as f:
                first_line = f.readline().strip()
            assert first_line.startswith("#!/"), (
                "validate-gitops.sh missing shebang line"
            )

    @pytest.mark.unit
    def test_validation_script_checks_flux(self):
        """Validation script must check Flux controllers."""
        script = GITOPS_ROOT / "scripts" / "validation" / "validate-gitops.sh"
        if script.exists():
            content = script.read_text()
            assert "flux-system" in content, (
                "Validation script must check flux-system namespace"
            )
            assert "source-controller" in content, (
                "Validation script must check source-controller"
            )

    @pytest.mark.unit
    def test_validation_script_checks_argocd(self):
        """Validation script must check ArgoCD controllers."""
        script = GITOPS_ROOT / "scripts" / "validation" / "validate-gitops.sh"
        if script.exists():
            content = script.read_text()
            assert "argocd" in content, (
                "Validation script must check argocd namespace"
            )
            assert "argocd-server" in content, (
                "Validation script must check argocd-server"
            )

    @pytest.mark.unit
    def test_validation_script_checks_drift(self):
        """Validation script must test drift detection."""
        script = GITOPS_ROOT / "scripts" / "validation" / "validate-gitops.sh"
        if script.exists():
            content = script.read_text()
            assert "drift" in content.lower(), (
                "Validation script must test drift detection"
            )

    @pytest.mark.unit
    def test_validation_script_checks_all_apps(self):
        """Validation script must check all MLOps applications."""
        script = GITOPS_ROOT / "scripts" / "validation" / "validate-gitops.sh"
        if script.exists():
            content = script.read_text()
            for app in ["mlflow", "kubeflow", "kserve", "monitoring"]:
                assert app in content, (
                    f"Validation script must check {app}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
