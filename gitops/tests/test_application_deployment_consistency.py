"""
Property-Based Tests for MLOps Application Deployment Consistency

Feature: gitops-implementation, Property 1: Application Deployment Consistency
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5

For any MLOps application (MLflow, Kubeflow, KServe, monitoring), when ArgoCD
deploys the application, all required components should be deployed and report
healthy status.

This module validates:
- All ArgoCD Applications exist for all environments
- All applications have required sync policies, retries, and finalizers
- All Kustomize overlays reference base correctly
- All base manifests have required components (namespace, SA, config, workloads)
- Production has stricter policies (no auto-prune, longer retries)
- Environment-specific configurations are correct
- Notification annotations are present
"""

import os
import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set
from hypothesis import given, strategies as st, settings, HealthCheck


# Base paths
GITOPS_ROOT = Path(__file__).parent.parent.resolve()
APPLICATIONS_PATH = GITOPS_ROOT / "applications"
APPS_PATH = APPLICATIONS_PATH / "apps"
ENVIRONMENTS_DIR = APPLICATIONS_PATH / "environments"

ENVIRONMENTS = ["dev", "staging", "production"]
APPLICATIONS = ["mlflow", "kubeflow", "kserve", "monitoring"]

# Required components per application base
REQUIRED_BASE_COMPONENTS = {
    "mlflow": {
        "namespace.yaml",
        "serviceaccount.yaml",
        "configmap.yaml",
        "deployment.yaml",
        "service.yaml",
        "kustomization.yaml",
    },
    "kubeflow": {
        "namespace.yaml",
        "serviceaccount.yaml",
        "configmap.yaml",
        "kustomization.yaml",
    },
    "kserve": {
        "namespace.yaml",
        "serviceaccount.yaml",
        "configmap.yaml",
        "kustomization.yaml",
    },
    "monitoring": {
        "namespace.yaml",
        "serviceaccount.yaml",
        "configmap.yaml",
        "kustomization.yaml",
    },
}

# Required workloads per application (must have probes)
REQUIRED_WORKLOADS = {
    "mlflow": ["deployment.yaml"],
    "kubeflow": ["pipeline-controller.yaml"],
    "kserve": ["serving-runtime.yaml"],
    "monitoring": ["prometheus-deployment.yaml", "grafana-deployment.yaml"],
}

# Required ArgoCD Application fields
REQUIRED_APP_FIELDS = {"apiVersion", "kind", "metadata", "spec"}
REQUIRED_SPEC_FIELDS = {"project", "source", "destination", "syncPolicy"}
REQUIRED_SOURCE_FIELDS = {"repoURL", "targetRevision", "path"}
REQUIRED_DESTINATION_FIELDS = {"server", "namespace"}

# Environment-specific target revisions
ENV_TARGET_REVISIONS = {
    "dev": "develop",
    "staging": "staging",
    "production": "main",
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


def get_app_path(app_name: str) -> Path:
    """Get the base path for an application."""
    return APPS_PATH / app_name


def get_overlay_path(app_name: str, env: str) -> Path:
    """Get the overlay path for an application/environment."""
    return APPS_PATH / app_name / "overlays" / env


def get_env_app_path(app_name: str, env: str) -> Path:
    """Get the ArgoCD Application path for an application/environment."""
    return ENVIRONMENTS_DIR / env / f"{app_name}-application.yaml"


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@st.composite
def app_env_combo(draw):
    """Generate a valid (application, environment) combination."""
    app = draw(st.sampled_from(APPLICATIONS))
    env = draw(st.sampled_from(ENVIRONMENTS))
    return {"app": app, "env": env}


@st.composite
def app_config(draw):
    """Generate an application configuration for property testing."""
    return {
        "app": draw(st.sampled_from(APPLICATIONS)),
        "env": draw(st.sampled_from(ENVIRONMENTS)),
        "min_replicas": draw(st.integers(min_value=1, max_value=3)),
        "check_probes": draw(st.booleans()),
    }


# ---------------------------------------------------------------------------
# Property 1: Application Deployment Consistency
# For any MLOps application, when ArgoCD deploys the application,
# all required components should be deployed and report healthy status
# ---------------------------------------------------------------------------

class TestArgocdApplicationExistence:
    """Verify all ArgoCD Applications exist for all environments."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_exists_for_all_combos(self, combo):
        """Property: Every (app, env) combination must have an ArgoCD Application."""
        app_name = combo["app"]
        env = combo["env"]
        path = get_env_app_path(app_name, env)
        assert path.exists(), f"Missing ArgoCD Application: {path}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_is_valid_yaml(self, combo):
        """Property: Every ArgoCD Application must be valid YAML."""
        app_name = combo["app"]
        env = combo["env"]
        path = get_env_app_path(app_name, env)
        if not path.exists():
            pytest.skip(f"Application {app_name}/{env} does not exist")
        data = load_yaml(path)
        assert data is not None, f"Invalid YAML in {app_name}/{env}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_correct_kind(self, combo):
        """Property: Every ArgoCD Application must have kind=Application."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")
        assert data.get("kind") == "Application"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_correct_api_version(self, combo):
        """Property: Every ArgoCD Application must use argoproj.io/v1alpha1."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")
        assert data.get("apiVersion") == "argoproj.io/v1alpha1"


class TestArgocdApplicationStructure:
    """Verify ArgoCD Applications have required structure and fields."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_required_fields(self, combo):
        """Property: Every ArgoCD Application must have all required fields."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        missing = REQUIRED_APP_FIELDS - set(data.keys())
        assert not missing, f"{app_name}/{env} missing fields: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_spec_has_required_fields(self, combo):
        """Property: Every ArgoCD Application spec must have project, source, destination, syncPolicy."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        spec = data.get("spec", {})
        missing = REQUIRED_SPEC_FIELDS - set(spec.keys())
        assert not missing, f"{app_name}/{env} spec missing: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_source_has_required_fields(self, combo):
        """Property: Every ArgoCD Application source must have repoURL, targetRevision, path."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        source = data.get("spec", {}).get("source", {})
        missing = REQUIRED_SOURCE_FIELDS - set(source.keys())
        assert not missing, f"{app_name}/{env} source missing: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_destination_has_required_fields(self, combo):
        """Property: Every ArgoCD Application destination must have server and namespace."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        dest = data.get("spec", {}).get("destination", {})
        missing = REQUIRED_DESTINATION_FIELDS - set(dest.keys())
        assert not missing, f"{app_name}/{env} destination missing: {missing}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_finalizer(self, combo):
        """Property: Every ArgoCD Application must have resource finalizer."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        finalizers = data.get("metadata", {}).get("finalizers", [])
        assert "resources-finalizer.argocd.argoproj.io" in finalizers, (
            f"{app_name}/{env} missing resource finalizer"
        )


class TestSyncPolicies:
    """Verify sync policies are correctly configured per environment."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_automated_sync(self, combo):
        """Property: Every ArgoCD Application must have automated sync policy."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        sync_policy = data.get("spec", {}).get("syncPolicy", {})
        assert "automated" in sync_policy, f"{app_name}/{env} missing automated sync"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_self_heal(self, combo):
        """Property: Every ArgoCD Application must have selfHeal enabled."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        automated = data["spec"]["syncPolicy"]["automated"]
        assert automated.get("selfHeal") is True, (
            f"{app_name}/{env} selfHeal not enabled"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_retry_config(self, combo):
        """Property: Every ArgoCD Application must have retry configuration."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        sync_policy = data.get("spec", {}).get("syncPolicy", {})
        assert "retry" in sync_policy, f"{app_name}/{env} missing retry config"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_retry_has_backoff(self, combo):
        """Property: Every ArgoCD Application retry must have backoff configuration."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        retry = data["spec"]["syncPolicy"]["retry"]
        backoff = retry.get("backoff", {})
        assert "duration" in backoff, f"{app_name}/{env} retry missing backoff.duration"
        assert "factor" in backoff, f"{app_name}/{env} retry missing backoff.factor"
        assert "maxDuration" in backoff, f"{app_name}/{env} retry missing backoff.maxDuration"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_create_namespace_option(self, combo):
        """Property: Every ArgoCD Application must have CreateNamespace sync option."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        sync_options = data["spec"]["syncPolicy"].get("syncOptions", [])
        assert "CreateNamespace=true" in sync_options, (
            f"{app_name}/{env} missing CreateNamespace=true"
        )


class TestProductionStricterPolicies:
    """Verify production has stricter policies than dev/staging."""

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    def test_production_no_auto_prune(self, app):
        """Production must NOT auto-prune to prevent accidental deletions."""
        data = load_yaml(get_env_app_path(app, "production"))
        assert data is not None
        automated = data["spec"]["syncPolicy"]["automated"]
        assert automated.get("prune") is False, (
            f"{app}/production should not auto-prune"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    def test_dev_has_auto_prune(self, app):
        """Dev should auto-prune for fast iteration."""
        data = load_yaml(get_env_app_path(app, "dev"))
        assert data is not None
        automated = data["spec"]["syncPolicy"]["automated"]
        assert automated.get("prune") is True, (
            f"{app}/dev should auto-prune"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    def test_production_has_longer_retry_max_duration(self, app):
        """Production should have longer retry maxDuration than dev."""
        dev_data = load_yaml(get_env_app_path(app, "dev"))
        prod_data = load_yaml(get_env_app_path(app, "production"))
        assert dev_data is not None and prod_data is not None

        dev_max = dev_data["spec"]["syncPolicy"]["retry"]["backoff"]["maxDuration"]
        prod_max = prod_data["spec"]["syncPolicy"]["retry"]["backoff"]["maxDuration"]

        # Parse duration strings like "3m", "5m"
        def parse_duration(s):
            if s.endswith("m"):
                return int(s[:-1])
            elif s.endswith("s"):
                return int(s[:-1]) / 60
            return int(s)

        assert parse_duration(prod_max) >= parse_duration(dev_max), (
            f"{app}/production maxDuration ({prod_max}) should be >= dev ({dev_max})"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    def test_production_has_higher_revision_history(self, app):
        """Production should have higher revisionHistoryLimit for rollback safety."""
        dev_data = load_yaml(get_env_app_path(app, "dev"))
        prod_data = load_yaml(get_env_app_path(app, "production"))
        assert dev_data is not None and prod_data is not None

        dev_limit = dev_data.get("spec", {}).get("revisionHistoryLimit", 5)
        prod_limit = prod_data.get("spec", {}).get("revisionHistoryLimit", 5)

        assert prod_limit >= dev_limit, (
            f"{app}/production revisionHistoryLimit ({prod_limit}) should be >= dev ({dev_limit})"
        )


class TestEnvironmentSpecificConfigurations:
    """Verify environment-specific configurations are correct."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_points_to_correct_overlay(self, combo):
        """Property: ArgoCD Application source path must point to correct overlay."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        path = data["spec"]["source"]["path"]
        assert env in path, (
            f"{app_name}/{env} application path does not contain '{env}': {path}"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_correct_target_revision(self, combo):
        """Property: ArgoCD Application must use correct targetRevision per environment."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        expected_revision = ENV_TARGET_REVISIONS[env]
        actual_revision = data["spec"]["source"]["targetRevision"]
        assert actual_revision == expected_revision, (
            f"{app_name}/{env} expected targetRevision '{expected_revision}', "
            f"got '{actual_revision}'"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_environment_label(self, combo):
        """Property: Every ArgoCD Application must have environment label."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        labels = data.get("metadata", {}).get("labels", {})
        assert labels.get("environment") == env, (
            f"{app_name}/{env} missing or incorrect environment label"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_correct_namespace(self, combo):
        """Property: ArgoCD Application destination namespace must match app name."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        expected_namespace = app_name
        actual_namespace = data["spec"]["destination"]["namespace"]
        assert actual_namespace == expected_namespace, (
            f"{app_name}/{env} expected namespace '{expected_namespace}', "
            f"got '{actual_namespace}'"
        )


class TestNotificationAnnotations:
    """Verify notification annotations are present."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_application_has_notification_annotations(self, combo):
        """Property: Every ArgoCD Application must have at least one notification annotation."""
        app_name = combo["app"]
        env = combo["env"]
        data = load_yaml(get_env_app_path(app_name, env))
        if data is None:
            pytest.skip(f"Application {app_name}/{env} not loadable")

        annotations = data.get("metadata", {}).get("annotations", {})
        has_notification = any(
            k.startswith("notifications.argoproj.io/") for k in annotations
        )
        assert has_notification, (
            f"{app_name}/{env} missing notification annotations"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app", APPLICATIONS)
    def test_production_has_sync_succeeded_notification(self, app):
        """Production should notify on sync success for deployment tracking."""
        data = load_yaml(get_env_app_path(app, "production"))
        assert data is not None
        annotations = data.get("metadata", {}).get("annotations", {})
        has_success = any(
            "on-sync-succeeded" in k for k in annotations
        )
        assert has_success, (
            f"{app}/production missing on-sync-succeeded notification"
        )


class TestKustomizeOverlayConsistency:
    """Verify Kustomize overlays are correctly configured."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_overlay_exists(self, combo):
        """Property: Every (app, env) combination must have a Kustomize overlay."""
        app_name = combo["app"]
        env = combo["env"]
        path = get_overlay_path(app_name, env) / "kustomization.yaml"
        assert path.exists(), f"Missing overlay: {path}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_overlay_references_base(self, combo):
        """Property: Every overlay must reference its base directory."""
        app_name = combo["app"]
        env = combo["env"]
        path = get_overlay_path(app_name, env) / "kustomization.yaml"
        if not path.exists():
            pytest.skip(f"Overlay {app_name}/{env} does not exist")

        data = load_yaml(path)
        assert data is not None
        resources = data.get("resources", [])
        assert "../../base" in resources, (
            f"{app_name}/{env} overlay does not reference base"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_overlay_has_name_prefix(self, combo):
        """Property: Every overlay must have a namePrefix for environment isolation."""
        app_name = combo["app"]
        env = combo["env"]
        path = get_overlay_path(app_name, env) / "kustomization.yaml"
        if not path.exists():
            pytest.skip(f"Overlay {app_name}/{env} does not exist")

        data = load_yaml(path)
        assert data is not None
        assert "namePrefix" in data, (
            f"{app_name}/{env} overlay missing namePrefix"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_overlay_has_environment_label(self, combo):
        """Property: Every overlay must have environment label."""
        app_name = combo["app"]
        env = combo["env"]
        path = get_overlay_path(app_name, env) / "kustomization.yaml"
        if not path.exists():
            pytest.skip(f"Overlay {app_name}/{env} does not exist")

        data = load_yaml(path)
        assert data is not None
        labels_list = data.get("labels", [])
        env_labels = {}
        for entry in labels_list:
            env_labels.update(entry.get("pairs", {}))
        assert "environment" in env_labels, (
            f"{app_name}/{env} overlay missing environment label"
        )


class TestBaseManifestConsistency:
    """Verify base manifests have required components."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_base_directory_exists(self, combo):
        """Property: Every application must have a base directory."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"
        assert base_path.exists(), f"Missing base directory for {app_name}"

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_required_base_components_exist(self, combo):
        """Property: Every application base must have required components."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"
        if not base_path.exists():
            pytest.skip(f"Base directory for {app_name} does not exist")

        expected = REQUIRED_BASE_COMPONENTS[app_name]
        existing = {f.name for f in base_path.iterdir() if f.is_file()}
        missing = expected - existing
        assert not missing, (
            f"{app_name} base missing components: {missing}"
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_kustomization_references_all_resources(self, combo):
        """Property: Base kustomization.yaml must reference all base manifests."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"
        kust_path = base_path / "kustomization.yaml"
        if not kust_path.exists():
            pytest.skip(f"{app_name} base kustomization.yaml does not exist")

        data = load_yaml(kust_path)
        assert data is not None
        resources = data.get("resources", [])

        expected = REQUIRED_BASE_COMPONENTS[app_name] - {"kustomization.yaml"}
        missing = expected - set(resources)
        assert not missing, (
            f"{app_name} kustomization.yaml missing resources: {missing}"
        )


class TestWorkloadHealthProbes:
    """Verify workloads have health probes configured."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_workloads_have_liveness_probes(self, combo):
        """Property: All workloads must have liveness probes."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"

        for manifest_file in REQUIRED_WORKLOADS.get(app_name, []):
            manifest_path = base_path / manifest_file
            if not manifest_path.exists():
                continue

            docs = load_yaml_all(manifest_path)
            for doc in docs:
                if doc.get("kind") not in ("Deployment", "StatefulSet"):
                    continue

                containers = (
                    doc.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )
                for container in containers:
                    assert "livenessProbe" in container, (
                        f"{app_name}/{manifest_file} container '{container.get('name')}' "
                        f"missing livenessProbe"
                    )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_workloads_have_readiness_probes(self, combo):
        """Property: All workloads must have readiness probes."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"

        for manifest_file in REQUIRED_WORKLOADS.get(app_name, []):
            manifest_path = base_path / manifest_file
            if not manifest_path.exists():
                continue

            docs = load_yaml_all(manifest_path)
            for doc in docs:
                if doc.get("kind") not in ("Deployment", "StatefulSet"):
                    continue

                containers = (
                    doc.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )
                for container in containers:
                    assert "readinessProbe" in container, (
                        f"{app_name}/{manifest_file} container '{container.get('name')}' "
                        f"missing readinessProbe"
                    )


class TestSecurityContexts:
    """Verify security contexts are configured on workloads."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_workloads_have_pod_security_context(self, combo):
        """Property: All workloads must have pod-level security context."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"

        for manifest_file in REQUIRED_WORKLOADS.get(app_name, []):
            manifest_path = base_path / manifest_file
            if not manifest_path.exists():
                continue

            docs = load_yaml_all(manifest_path)
            for doc in docs:
                if doc.get("kind") not in ("Deployment", "StatefulSet"):
                    continue

                pod_spec = doc.get("spec", {}).get("template", {}).get("spec", {})
                assert "securityContext" in pod_spec, (
                    f"{app_name}/{manifest_file} missing pod securityContext"
                )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_containers_have_security_context(self, combo):
        """Property: All containers must have container-level security context."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"

        for manifest_file in REQUIRED_WORKLOADS.get(app_name, []):
            manifest_path = base_path / manifest_file
            if not manifest_path.exists():
                continue

            docs = load_yaml_all(manifest_path)
            for doc in docs:
                if doc.get("kind") not in ("Deployment", "StatefulSet"):
                    continue

                containers = (
                    doc.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )
                for container in containers:
                    assert "securityContext" in container, (
                        f"{app_name}/{manifest_file} container '{container.get('name')}' "
                        f"missing securityContext"
                    )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_containers_drop_all_capabilities(self, combo):
        """Property: All containers should drop ALL capabilities."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"

        for manifest_file in REQUIRED_WORKLOADS.get(app_name, []):
            manifest_path = base_path / manifest_file
            if not manifest_path.exists():
                continue

            docs = load_yaml_all(manifest_path)
            for doc in docs:
                if doc.get("kind") not in ("Deployment", "StatefulSet"):
                    continue

                containers = (
                    doc.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )
                for container in containers:
                    sec_ctx = container.get("securityContext", {})
                    caps = sec_ctx.get("capabilities", {})
                    dropped = caps.get("drop", [])
                    assert "ALL" in dropped, (
                        f"{app_name}/{manifest_file} container '{container.get('name')}' "
                        f"does not drop ALL capabilities"
                    )


class TestResourceLimits:
    """Verify resource limits are configured."""

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(combo=app_env_combo())
    def test_containers_have_resource_limits(self, combo):
        """Property: All containers must have resource limits defined."""
        app_name = combo["app"]
        base_path = get_app_path(app_name) / "base"

        for manifest_file in REQUIRED_WORKLOADS.get(app_name, []):
            manifest_path = base_path / manifest_file
            if not manifest_path.exists():
                continue

            docs = load_yaml_all(manifest_path)
            for doc in docs:
                if doc.get("kind") not in ("Deployment", "StatefulSet"):
                    continue

                containers = (
                    doc.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )
                for container in containers:
                    resources = container.get("resources", {})
                    assert "limits" in resources, (
                        f"{app_name}/{manifest_file} container '{container.get('name')}' "
                        f"missing resource limits"
                    )
                    assert "requests" in resources, (
                        f"{app_name}/{manifest_file} container '{container.get('name')}' "
                        f"missing resource requests"
                    )


class TestArgocdProjectConfiguration:
    """Verify ArgoCD project configuration."""

    @pytest.mark.unit
    def test_mlops_core_project_exists(self):
        """mlops-core AppProject must exist."""
        project_path = APPLICATIONS_PATH / "projects" / "mlops-core.yaml"
        assert project_path.exists(), "mlops-core.yaml not found"

    @pytest.mark.unit
    def test_mlops_core_project_has_valid_structure(self):
        """mlops-core AppProject must have valid structure."""
        project_path = APPLICATIONS_PATH / "projects" / "mlops-core.yaml"
        data = load_yaml(project_path)
        assert data is not None
        assert data.get("kind") == "AppProject"
        assert data.get("apiVersion") == "argoproj.io/v1alpha1"

    @pytest.mark.unit
    def test_mlops_core_project_has_roles(self):
        """mlops-core AppProject must have RBAC roles defined."""
        project_path = APPLICATIONS_PATH / "projects" / "mlops-core.yaml"
        data = load_yaml(project_path)
        assert data is not None
        roles = data.get("spec", {}).get("roles", [])
        assert len(roles) > 0, "mlops-core project has no roles"

    @pytest.mark.unit
    def test_mlops_core_project_has_destinations(self):
        """mlops-core AppProject must define allowed destinations."""
        project_path = APPLICATIONS_PATH / "projects" / "mlops-core.yaml"
        data = load_yaml(project_path)
        assert data is not None
        destinations = data.get("spec", {}).get("destinations", [])
        assert len(destinations) > 0, "mlops-core project has no destinations"


class TestEnvironmentKustomization:
    """Verify environment-level kustomization files."""

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_environment_kustomization_exists(self, env):
        """Each environment must have a kustomization.yaml."""
        path = ENVIRONMENTS_DIR / env / "kustomization.yaml"
        assert path.exists(), f"Missing kustomization.yaml for {env}"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_environment_kustomization_references_all_apps(self, env):
        """Environment kustomization must reference all application manifests."""
        path = ENVIRONMENTS_DIR / env / "kustomization.yaml"
        data = load_yaml(path)
        assert data is not None

        resources = data.get("resources", [])
        expected_apps = {f"{app}-application.yaml" for app in APPLICATIONS}
        actual_apps = {Path(r).name for r in resources}
        missing = expected_apps - actual_apps
        assert not missing, (
            f"{env} kustomization.yaml missing applications: {missing}"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_environment_kustomization_has_environment_label(self, env):
        """Environment kustomization must have environment label."""
        path = ENVIRONMENTS_DIR / env / "kustomization.yaml"
        data = load_yaml(path)
        assert data is not None

        labels_list = data.get("labels", [])
        env_labels = {}
        for entry in labels_list:
            env_labels.update(entry.get("pairs", {}))
        assert "environment" in env_labels, (
            f"{env} kustomization missing environment label"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
