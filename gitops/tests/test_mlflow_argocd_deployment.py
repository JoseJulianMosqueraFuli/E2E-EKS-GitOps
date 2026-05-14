"""
Tests for MLflow ArgoCD Deployment Configuration (Task 3.1)

Validates:
- All required manifests exist and are valid YAML
- Sync wave ordering is correct (namespace → secrets → PostgreSQL → MinIO → MLflow)
- Health checks are configured on ArgoCD Applications
- Environment-specific values are properly set
- Secret references are consistent

Validates: Requirements 3.1
"""

import os
import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Optional


# Base paths
GITOPS_ROOT = Path(__file__).parent.parent.resolve()
MLFLOW_BASE = GITOPS_ROOT / "applications" / "apps" / "mlflow" / "base"
MLFLOW_OVERLAYS = GITOPS_ROOT / "applications" / "apps" / "mlflow" / "overlays"
ENVIRONMENTS_DIR = GITOPS_ROOT / "applications" / "environments"

ENVIRONMENTS = ["dev", "staging", "production"]

# Expected base manifest files
EXPECTED_BASE_MANIFESTS = [
    "namespace.yaml",
    "serviceaccount.yaml",
    "external-secrets.yaml",
    "configmap.yaml",
    "postgresql-statefulset.yaml",
    "postgresql-service.yaml",
    "minio-pvc.yaml",
    "minio-deployment.yaml",
    "minio-service.yaml",
    "deployment.yaml",
    "service.yaml",
    "kustomization.yaml",
]

# Expected sync wave ordering: lower waves deploy first
# namespace(-2) → serviceaccount/secretstore(-1) → configmap/externalsecrets/pvc(0)
#   → postgresql/minio(1) → mlflow(2)
EXPECTED_SYNC_WAVES = {
    "namespace.yaml": -2,
    "serviceaccount.yaml": -1,
    "configmap.yaml": 0,
    "minio-pvc.yaml": 0,
    "postgresql-statefulset.yaml": 1,
    "postgresql-service.yaml": 1,
    "minio-deployment.yaml": 1,
    "minio-service.yaml": 1,
    "deployment.yaml": 2,
    "service.yaml": 2,
}


def load_yaml(path: Path) -> Optional[Dict]:
    """Load a single YAML document from a file."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, FileNotFoundError):
        return None


def load_yaml_all(path: Path) -> List[Dict]:
    """Load all YAML documents from a multi-document file."""
    try:
        with open(path, "r") as f:
            return [doc for doc in yaml.safe_load_all(f) if doc is not None]
    except (yaml.YAMLError, FileNotFoundError):
        return []


def get_sync_wave(manifest: Dict) -> Optional[int]:
    """Extract the argocd sync-wave annotation value from a manifest."""
    annotations = manifest.get("metadata", {}).get("annotations", {})
    wave = annotations.get("argocd.argoproj.io/sync-wave")
    if wave is not None:
        return int(wave)
    return None


# ---------------------------------------------------------------------------
# 1. Manifest existence and YAML validity
# ---------------------------------------------------------------------------

class TestBaseManifestsExist:
    """Verify all required MLflow base manifests exist and are valid YAML."""

    @pytest.mark.unit
    @pytest.mark.parametrize("manifest", EXPECTED_BASE_MANIFESTS)
    def test_base_manifest_exists(self, manifest):
        path = MLFLOW_BASE / manifest
        assert path.exists(), f"Missing base manifest: {manifest}"

    @pytest.mark.unit
    @pytest.mark.parametrize("manifest", EXPECTED_BASE_MANIFESTS)
    def test_base_manifest_is_valid_yaml(self, manifest):
        path = MLFLOW_BASE / manifest
        if not path.exists():
            pytest.skip(f"{manifest} does not exist")
        # external-secrets.yaml is multi-doc
        if manifest == "external-secrets.yaml":
            docs = load_yaml_all(path)
            assert len(docs) > 0, f"{manifest} has no valid YAML documents"
        else:
            data = load_yaml(path)
            assert data is not None, f"{manifest} is not valid YAML"

    @pytest.mark.unit
    def test_kustomization_includes_all_resources(self):
        """The base kustomization.yaml must reference every other base manifest."""
        kust = load_yaml(MLFLOW_BASE / "kustomization.yaml")
        assert kust is not None
        resources = kust.get("resources", [])
        expected = [m for m in EXPECTED_BASE_MANIFESTS if m != "kustomization.yaml"]
        for m in expected:
            assert m in resources, f"kustomization.yaml missing resource: {m}"


# ---------------------------------------------------------------------------
# 2. Sync wave ordering
# ---------------------------------------------------------------------------

class TestSyncWaveOrdering:
    """Verify sync-wave annotations enforce correct deployment ordering."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "manifest,expected_wave",
        list(EXPECTED_SYNC_WAVES.items()),
        ids=list(EXPECTED_SYNC_WAVES.keys()),
    )
    def test_sync_wave_value(self, manifest, expected_wave):
        path = MLFLOW_BASE / manifest
        if not path.exists():
            pytest.skip(f"{manifest} does not exist")
        data = load_yaml(path)
        assert data is not None
        wave = get_sync_wave(data)
        assert wave is not None, f"{manifest} missing sync-wave annotation"
        assert wave == expected_wave, (
            f"{manifest}: expected sync-wave {expected_wave}, got {wave}"
        )

    @pytest.mark.unit
    def test_external_secrets_sync_waves(self):
        """ExternalSecrets file has multiple docs; SecretStore at -1, ExternalSecrets at 0."""
        docs = load_yaml_all(MLFLOW_BASE / "external-secrets.yaml")
        assert len(docs) >= 3, "Expected at least 3 documents in external-secrets.yaml"

        for doc in docs:
            kind = doc.get("kind", "")
            wave = get_sync_wave(doc)
            if kind == "SecretStore":
                assert wave == -1, f"SecretStore should have sync-wave -1, got {wave}"
            elif kind == "ExternalSecret":
                assert wave == 0, f"ExternalSecret should have sync-wave 0, got {wave}"

    @pytest.mark.unit
    def test_namespace_deploys_before_everything(self):
        """Namespace wave must be strictly less than all other waves."""
        ns_data = load_yaml(MLFLOW_BASE / "namespace.yaml")
        assert ns_data is not None
        ns_wave = get_sync_wave(ns_data)
        assert ns_wave is not None

        for manifest, expected_wave in EXPECTED_SYNC_WAVES.items():
            if manifest != "namespace.yaml":
                assert ns_wave < expected_wave, (
                    f"Namespace wave ({ns_wave}) must be < {manifest} wave ({expected_wave})"
                )

    @pytest.mark.unit
    def test_postgresql_deploys_before_mlflow(self):
        """PostgreSQL (wave 1) must deploy before MLflow server (wave 2)."""
        pg = load_yaml(MLFLOW_BASE / "postgresql-statefulset.yaml")
        mlflow = load_yaml(MLFLOW_BASE / "deployment.yaml")
        assert pg is not None and mlflow is not None
        assert get_sync_wave(pg) < get_sync_wave(mlflow)

    @pytest.mark.unit
    def test_minio_deploys_before_mlflow(self):
        """MinIO (wave 1) must deploy before MLflow server (wave 2)."""
        minio = load_yaml(MLFLOW_BASE / "minio-deployment.yaml")
        mlflow = load_yaml(MLFLOW_BASE / "deployment.yaml")
        assert minio is not None and mlflow is not None
        assert get_sync_wave(minio) < get_sync_wave(mlflow)


# ---------------------------------------------------------------------------
# 3. ArgoCD Application health checks and configuration
# ---------------------------------------------------------------------------

class TestArgocdApplicationHealthChecks:
    """Verify ArgoCD Application definitions have health checks and sync policies."""

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_exists(self, env):
        path = ENVIRONMENTS_DIR / env / "mlflow-application.yaml"
        assert path.exists(), f"Missing ArgoCD Application for {env}"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_is_valid_yaml(self, env):
        path = ENVIRONMENTS_DIR / env / "mlflow-application.yaml"
        data = load_yaml(path)
        assert data is not None, f"Invalid YAML in {env}/mlflow-application.yaml"
        assert data.get("kind") == "Application"
        assert data.get("apiVersion") == "argoproj.io/v1alpha1"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_tracking_method(self, env):
        """Each ArgoCD Application should have resource tracking annotation."""
        data = load_yaml(ENVIRONMENTS_DIR / env / "mlflow-application.yaml")
        assert data is not None
        annotations = data.get("metadata", {}).get("annotations", {})
        assert "argocd.argoproj.io/tracking-method" in annotations, (
            f"{env} application missing tracking-method annotation"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_sync_policy(self, env):
        """Each ArgoCD Application must have automated sync policy."""
        data = load_yaml(ENVIRONMENTS_DIR / env / "mlflow-application.yaml")
        assert data is not None
        sync_policy = data.get("spec", {}).get("syncPolicy", {})
        assert "automated" in sync_policy, f"{env} missing automated sync policy"
        assert "retry" in sync_policy, f"{env} missing retry configuration"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_self_heal(self, env):
        """selfHeal should be enabled for drift reconciliation."""
        data = load_yaml(ENVIRONMENTS_DIR / env / "mlflow-application.yaml")
        assert data is not None
        automated = data["spec"]["syncPolicy"]["automated"]
        assert automated.get("selfHeal") is True, f"{env} selfHeal not enabled"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_retry_backoff(self, env):
        """Retry policy must include backoff configuration."""
        data = load_yaml(ENVIRONMENTS_DIR / env / "mlflow-application.yaml")
        assert data is not None
        retry = data["spec"]["syncPolicy"]["retry"]
        assert "backoff" in retry, f"{env} missing retry backoff"
        assert "duration" in retry["backoff"]
        assert "factor" in retry["backoff"]
        assert "maxDuration" in retry["backoff"]

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_finalizer(self, env):
        """Applications should have resource finalizer for cleanup."""
        data = load_yaml(ENVIRONMENTS_DIR / env / "mlflow-application.yaml")
        assert data is not None
        finalizers = data.get("metadata", {}).get("finalizers", [])
        assert "resources-finalizer.argocd.argoproj.io" in finalizers, (
            f"{env} missing ArgoCD resource finalizer"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_application_has_notification_annotations(self, env):
        """Each environment should have at least a sync-failed notification."""
        data = load_yaml(ENVIRONMENTS_DIR / env / "mlflow-application.yaml")
        assert data is not None
        annotations = data.get("metadata", {}).get("annotations", {})
        has_notification = any(
            k.startswith("notifications.argoproj.io/") for k in annotations
        )
        assert has_notification, f"{env} missing notification annotations"

    @pytest.mark.unit
    def test_production_has_no_auto_prune(self):
        """Production should NOT auto-prune to prevent accidental deletions."""
        data = load_yaml(ENVIRONMENTS_DIR / "production" / "mlflow-application.yaml")
        assert data is not None
        automated = data["spec"]["syncPolicy"]["automated"]
        assert automated.get("prune") is False, "Production should not auto-prune"

    @pytest.mark.unit
    def test_dev_has_auto_prune(self):
        """Dev should auto-prune for fast iteration."""
        data = load_yaml(ENVIRONMENTS_DIR / "dev" / "mlflow-application.yaml")
        assert data is not None
        automated = data["spec"]["syncPolicy"]["automated"]
        assert automated.get("prune") is True, "Dev should auto-prune"


# ---------------------------------------------------------------------------
# 4. Environment-specific values
# ---------------------------------------------------------------------------

class TestEnvironmentSpecificValues:
    """Verify overlays set correct environment-specific configurations."""

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_overlay_exists(self, env):
        path = MLFLOW_OVERLAYS / env / "kustomization.yaml"
        assert path.exists(), f"Missing overlay for {env}"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_overlay_references_base(self, env):
        data = load_yaml(MLFLOW_OVERLAYS / env / "kustomization.yaml")
        assert data is not None
        resources = data.get("resources", [])
        assert "../../base" in resources, f"{env} overlay does not reference base"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_overlay_has_environment_label(self, env):
        data = load_yaml(MLFLOW_OVERLAYS / env / "kustomization.yaml")
        assert data is not None
        labels_list = data.get("labels", [])
        env_labels = {}
        for entry in labels_list:
            env_labels.update(entry.get("pairs", {}))
        assert "environment" in env_labels, f"{env} overlay missing environment label"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_overlay_has_name_prefix(self, env):
        data = load_yaml(MLFLOW_OVERLAYS / env / "kustomization.yaml")
        assert data is not None
        assert "namePrefix" in data, f"{env} overlay missing namePrefix"

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_overlay_patches_external_secrets(self, env):
        """Each overlay should patch ExternalSecret remote refs to env-specific paths."""
        data = load_yaml(MLFLOW_OVERLAYS / env / "kustomization.yaml")
        assert data is not None
        patches = data.get("patches", [])
        es_patches = [
            p for p in patches
            if p.get("target", {}).get("kind") == "ExternalSecret"
        ]
        assert len(es_patches) > 0, (
            f"{env} overlay missing ExternalSecret patches"
        )

    @pytest.mark.unit
    def test_dev_has_smallest_replicas(self):
        """Dev should have 1 replica for MLflow server."""
        data = load_yaml(MLFLOW_OVERLAYS / "dev" / "kustomization.yaml")
        assert data is not None
        patches = data.get("patches", [])
        for p in patches:
            target = p.get("target", {})
            if target.get("kind") == "Deployment" and target.get("name") == "mlflow-server":
                patch_str = p.get("patch", "")
                if "replicas" in patch_str:
                    assert "1" in patch_str
                    return
        pytest.fail("Dev overlay missing replica patch for mlflow-server")

    @pytest.mark.unit
    def test_production_has_most_replicas(self):
        """Production should have 3 replicas for MLflow server."""
        data = load_yaml(MLFLOW_OVERLAYS / "production" / "kustomization.yaml")
        assert data is not None
        patches = data.get("patches", [])
        for p in patches:
            target = p.get("target", {})
            if target.get("kind") == "Deployment" and target.get("name") == "mlflow-server":
                patch_str = p.get("patch", "")
                if "replicas" in patch_str:
                    assert "3" in patch_str
                    return
        pytest.fail("Production overlay missing replica patch for mlflow-server")

    @pytest.mark.unit
    @pytest.mark.parametrize("env", ENVIRONMENTS)
    def test_argocd_app_points_to_correct_overlay(self, env):
        """ArgoCD Application source path must point to the correct overlay."""
        data = load_yaml(ENVIRONMENTS_DIR / env / "mlflow-application.yaml")
        assert data is not None
        path = data["spec"]["source"]["path"]
        assert env in path, f"{env} application path does not contain '{env}': {path}"


# ---------------------------------------------------------------------------
# 5. Secret references consistency
# ---------------------------------------------------------------------------

class TestSecretReferencesConsistency:
    """Verify secret references are consistent between deployments and ExternalSecrets."""

    @pytest.mark.unit
    def test_mlflow_deployment_references_mlflow_secrets(self):
        """MLflow deployment must reference mlflow-secrets for backend_store_uri."""
        data = load_yaml(MLFLOW_BASE / "deployment.yaml")
        assert data is not None
        raw = yaml.dump(data)
        assert "mlflow-secrets" in raw, "Deployment missing mlflow-secrets reference"

    @pytest.mark.unit
    def test_mlflow_deployment_references_minio_secrets(self):
        """MLflow deployment must reference mlflow-minio-secrets for S3 credentials."""
        data = load_yaml(MLFLOW_BASE / "deployment.yaml")
        assert data is not None
        raw = yaml.dump(data)
        assert "mlflow-minio-secrets" in raw, "Deployment missing mlflow-minio-secrets reference"

    @pytest.mark.unit
    def test_postgresql_references_mlflow_secrets(self):
        """PostgreSQL StatefulSet must reference mlflow-secrets for DB credentials."""
        data = load_yaml(MLFLOW_BASE / "postgresql-statefulset.yaml")
        assert data is not None
        raw = yaml.dump(data)
        assert "mlflow-secrets" in raw, "PostgreSQL missing mlflow-secrets reference"

    @pytest.mark.unit
    def test_minio_references_minio_secrets(self):
        """MinIO deployment must reference mlflow-minio-secrets for root credentials."""
        data = load_yaml(MLFLOW_BASE / "minio-deployment.yaml")
        assert data is not None
        raw = yaml.dump(data)
        assert "mlflow-minio-secrets" in raw, "MinIO missing mlflow-minio-secrets reference"

    @pytest.mark.unit
    def test_external_secrets_produce_expected_secrets(self):
        """ExternalSecrets must produce both mlflow-secrets and mlflow-minio-secrets."""
        docs = load_yaml_all(MLFLOW_BASE / "external-secrets.yaml")
        target_names = set()
        for doc in docs:
            if doc.get("kind") == "ExternalSecret":
                target = doc.get("spec", {}).get("target", {}).get("name")
                if target:
                    target_names.add(target)
        assert "mlflow-secrets" in target_names, "ExternalSecret for mlflow-secrets not found"
        assert "mlflow-minio-secrets" in target_names, (
            "ExternalSecret for mlflow-minio-secrets not found"
        )

    @pytest.mark.unit
    def test_mlflow_secrets_has_backend_store_uri(self):
        """The mlflow-secrets ExternalSecret must template a backend_store_uri key."""
        docs = load_yaml_all(MLFLOW_BASE / "external-secrets.yaml")
        for doc in docs:
            if doc.get("kind") == "ExternalSecret":
                target_name = doc.get("spec", {}).get("target", {}).get("name")
                if target_name == "mlflow-secrets":
                    template_data = (
                        doc.get("spec", {})
                        .get("target", {})
                        .get("template", {})
                        .get("data", {})
                    )
                    assert "backend_store_uri" in template_data, (
                        "mlflow-secrets missing backend_store_uri in template"
                    )
                    return
        pytest.fail("mlflow-secrets ExternalSecret not found")


# ---------------------------------------------------------------------------
# 6. Component health probes in base manifests
# ---------------------------------------------------------------------------

class TestComponentHealthProbes:
    """Verify that workloads have liveness and readiness probes."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "manifest,container_index",
        [
            ("deployment.yaml", 0),
            ("postgresql-statefulset.yaml", 0),
            ("minio-deployment.yaml", 0),
        ],
    )
    def test_workload_has_liveness_probe(self, manifest, container_index):
        data = load_yaml(MLFLOW_BASE / manifest)
        assert data is not None
        containers = (
            data.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )
        assert len(containers) > container_index
        container = containers[container_index]
        assert "livenessProbe" in container, f"{manifest} missing livenessProbe"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "manifest,container_index",
        [
            ("deployment.yaml", 0),
            ("postgresql-statefulset.yaml", 0),
            ("minio-deployment.yaml", 0),
        ],
    )
    def test_workload_has_readiness_probe(self, manifest, container_index):
        data = load_yaml(MLFLOW_BASE / manifest)
        assert data is not None
        containers = (
            data.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )
        assert len(containers) > container_index
        container = containers[container_index]
        assert "readinessProbe" in container, f"{manifest} missing readinessProbe"

    @pytest.mark.unit
    def test_mlflow_deployment_has_init_containers(self):
        """MLflow deployment should wait for PostgreSQL and MinIO via init containers."""
        data = load_yaml(MLFLOW_BASE / "deployment.yaml")
        assert data is not None
        init_containers = (
            data.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("initContainers", [])
        )
        init_names = [c["name"] for c in init_containers]
        assert "wait-for-postgresql" in init_names, "Missing wait-for-postgresql init container"
        assert "wait-for-minio" in init_names, "Missing wait-for-minio init container"
