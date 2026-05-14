"""
Unit Tests for Promotion Pipeline

Validates:
- Promotion path validation
- Configuration file validation
- Promotion engine logic
- Notification system
- PR description generation

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

import os
import sys
import pytest
import yaml
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch, MagicMock

# Add promotion scripts to path
PROMOTION_PATH = Path(__file__).parent.parent / "scripts" / "promotion"
sys.path.insert(0, str(PROMOTION_PATH))

from promote import (
    PromotionValidator,
    PromotionEngine,
    PromotionResult,
    create_promotion_pr,
    VALID_PROMOTIONS,
    ENV_BRANCHES,
    GITOPS_ROOT,
)
from notifications import (
    PromotionEvent,
    SlackNotifier,
    DocumentationUpdater,
    notify_promotion,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_gitops(tmp_path):
    """Create a temporary gitops directory structure for testing."""
    # Create directory structure and cluster configs
    for env in ["dev", "staging", "production"]:
        (tmp_path / "applications" / "environments" / env).mkdir(parents=True)
        (tmp_path / "infrastructure" / "clusters" / env).mkdir(parents=True)
        (tmp_path / "infrastructure" / "clusters" / env / "infrastructure").mkdir(parents=True)
        (tmp_path / "infrastructure" / "clusters" / env / "config").mkdir(parents=True)
        (tmp_path / "infrastructure" / "clusters" / env / "flux-system").mkdir(parents=True)

        # Create cluster kustomization
        cluster_kust = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": ["flux-system", "infrastructure", "config"],
            "commonLabels": {"environment": env},
        }
        with open(tmp_path / "infrastructure" / "clusters" / env / "kustomization.yaml", "w") as f:
            yaml.dump(cluster_kust, f)

        # Create environment kustomization
        env_kust = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": [f"{a}-{env}.yaml" for a in ["mlflow", "kubeflow", "kserve", "monitoring"]],
            "labels": [{"pairs": {"environment": env}, "includeSelectors": False}],
        }
        with open(tmp_path / "applications" / "environments" / env / "kustomization.yaml", "w") as f:
            yaml.dump(env_kust, f)

        # Create cluster config
        cluster_config = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cluster-config", "namespace": "flux-system"},
            "data": {
                "environment": env,
                "cluster_name": f"mlops-{env}-cluster",
            },
        }
        with open(tmp_path / "infrastructure" / "clusters" / env / "config" / "cluster-config.yaml", "w") as f:
            yaml.dump(cluster_config, f)

        # Create flux-system gotk-sync.yaml
        gotk_sync = {
            "apiVersion": "source.toolkit.fluxcd.io/v1",
            "kind": "GitRepository",
            "metadata": {"name": "flux-system", "namespace": "flux-system"},
            "spec": {"interval": "1m", "ref": {"branch": env}},
        }
        with open(tmp_path / "infrastructure" / "clusters" / env / "flux-system" / "gotk-sync.yaml", "w") as f:
            yaml.dump(gotk_sync, f)

        # Create infrastructure kustomization
        infra_kust = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": ["../../../sources", "../../../flux-config"],
            "commonLabels": {"environment": env},
        }
        with open(tmp_path / "infrastructure" / "clusters" / env / "infrastructure" / "kustomization.yaml", "w") as f:
            yaml.dump(infra_kust, f)

    # Create app structures
    for app in ["mlflow", "kubeflow", "kserve", "monitoring"]:
        (tmp_path / "applications" / "apps" / app / "base").mkdir(parents=True, exist_ok=True)

        # Create base kustomization and namespace
        kust = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": ["namespace.yaml"],
        }
        with open(tmp_path / "applications" / "apps" / app / "base" / "kustomization.yaml", "w") as f:
            yaml.dump(kust, f)

        ns = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": app},
        }
        with open(tmp_path / "applications" / "apps" / app / "base" / "namespace.yaml", "w") as f:
            yaml.dump(ns, f)

        for env in ["dev", "staging", "production"]:
            (tmp_path / "applications" / "apps" / app / "overlays" / env).mkdir(parents=True, exist_ok=True)

            # Create overlay kustomization
            overlay = {**kust, "resources": ["../../base"]}
            with open(tmp_path / "applications" / "apps" / app / "overlays" / env / "kustomization.yaml", "w") as f:
                yaml.dump(overlay, f)

            # Create ArgoCD Application
            app_data = {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Application",
                "metadata": {
                    "name": f"{app}-{env}",
                    "labels": {"environment": env},
                    "annotations": {
                        "notifications.argoproj.io/subscribe.on-sync-failed.slack": f"mlops-alerts-{env}",
                    },
                },
                "spec": {
                    "project": "mlops-core",
                    "source": {
                        "repoURL": "https://github.com/org/gitops-applications",
                        "targetRevision": ENV_BRANCHES[env],
                        "path": f"apps/{app}/overlays/{env}",
                    },
                    "destination": {
                        "server": "https://kubernetes.default.svc",
                        "namespace": app,
                    },
                    "syncPolicy": {
                        "automated": {
                            "prune": env != "production",
                            "selfHeal": True,
                        },
                    },
                },
            }
            with open(tmp_path / "applications" / "environments" / env / f"{app}-{env}.yaml", "w") as f:
                yaml.dump(app_data, f)

    # Create flux-config
    flux_config = [
        {
            "apiVersion": "kustomize.toolkit.fluxcd.io/v1",
            "kind": "Kustomization",
            "metadata": {"name": "infrastructure-controllers", "namespace": "flux-system"},
            "spec": {"interval": "10m", "prune": True, "dependsOn": []},
        },
        {
            "apiVersion": "kustomize.toolkit.fluxcd.io/v1",
            "kind": "Kustomization",
            "metadata": {"name": "infrastructure-addons", "namespace": "flux-system"},
            "spec": {"interval": "10m", "prune": True, "dependsOn": [{"name": "infrastructure-controllers"}]},
        },
        {
            "apiVersion": "kustomize.toolkit.fluxcd.io/v1",
            "kind": "Kustomization",
            "metadata": {"name": "infrastructure-networking", "namespace": "flux-system"},
            "spec": {"interval": "10m", "prune": True, "dependsOn": [{"name": "infrastructure-addons"}]},
        },
        {
            "apiVersion": "kustomize.toolkit.fluxcd.io/v1",
            "kind": "Kustomization",
            "metadata": {"name": "infrastructure-security", "namespace": "flux-system"},
            "spec": {"interval": "10m", "prune": True, "dependsOn": [{"name": "infrastructure-controllers"}]},
        },
    ]
    flux_dir = tmp_path / "infrastructure" / "flux-config"
    flux_dir.mkdir(parents=True, exist_ok=True)
    with open(flux_dir / "infrastructure-kustomization.yaml", "w") as f:
        yaml.dump_all(flux_config, f)

    # Create sources directory
    sources_dir = tmp_path / "infrastructure" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    with open(sources_dir / "kustomization.yaml", "w") as f:
        yaml.dump({"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization", "resources": ["git-repository.yaml", "helm-repository.yaml"]}, f)
    with open(sources_dir / "git-repository.yaml", "w") as f:
        yaml.dump({"apiVersion": "source.toolkit.fluxcd.io/v1", "kind": "GitRepository", "metadata": {"name": "infra-repo", "namespace": "flux-system"}, "spec": {"interval": "5m", "url": "https://github.com/org/infra"}}, f)
    with open(sources_dir / "helm-repository.yaml", "w") as f:
        yaml.dump({"apiVersion": "source.toolkit.fluxcd.io/v1beta2", "kind": "HelmRepository", "metadata": {"name": "bitnami", "namespace": "flux-system"}, "spec": {"interval": "1h", "url": "https://charts.bitnami.com/bitnami"}}, f)

    return tmp_path


# ---------------------------------------------------------------------------
# Test PromotionValidator
# ---------------------------------------------------------------------------

class TestPromotionValidator:
    """Tests for PromotionValidator."""

    @pytest.mark.unit
    def test_valid_promotion_path(self, tmp_gitops):
        """Valid promotion paths should pass."""
        validator = PromotionValidator("dev", "staging", gitops_root=tmp_gitops)
        assert validator.validate()

    @pytest.mark.unit
    def test_invalid_promotion_path(self, tmp_gitops):
        """Invalid promotion paths should fail."""
        validator = PromotionValidator("dev", "production", gitops_root=tmp_gitops)
        assert not validator.validate()
        assert any("Invalid promotion path" in e for e in validator.errors)

    @pytest.mark.unit
    def test_reverse_promotion_fails(self, tmp_gitops):
        """Reverse promotions should fail."""
        validator = PromotionValidator("staging", "dev", gitops_root=tmp_gitops)
        assert not validator.validate()

    @pytest.mark.unit
    def test_validates_source_environment(self, tmp_gitops):
        """Source environment must exist."""
        validator = PromotionValidator("dev", "staging", gitops_root=tmp_gitops)
        assert validator.validate()

    @pytest.mark.unit
    def test_validates_target_environment(self, tmp_gitops):
        """Target environment must exist."""
        validator = PromotionValidator("dev", "staging", gitops_root=tmp_gitops)
        assert validator.validate()

    @pytest.mark.unit
    def test_validates_argocd_applications(self, tmp_gitops):
        """ArgoCD Applications must be valid YAML."""
        validator = PromotionValidator("dev", "staging", gitops_root=tmp_gitops)
        assert validator.validate()

    @pytest.mark.unit
    def test_validates_kustomize_overlays(self, tmp_gitops):
        """Kustomize overlays must be valid."""
        validator = PromotionValidator("dev", "staging", gitops_root=tmp_gitops)
        assert validator.validate()

    @pytest.mark.unit
    def test_detects_invalid_yaml(self, tmp_gitops):
        """Invalid YAML should be detected."""
        # Write invalid YAML
        app_file = tmp_gitops / "applications" / "environments" / "dev" / "mlflow-application.yaml"
        with open(app_file, "w") as f:
            f.write("invalid: yaml: content: [")

        validator = PromotionValidator("dev", "staging", gitops_root=tmp_gitops)
        assert not validator.validate()
        assert any("YAML" in e for e in validator.errors)

    @pytest.mark.unit
    def test_detects_missing_files(self, tmp_gitops):
        """Missing required files should be detected."""
        # Remove required file
        kust_file = tmp_gitops / "applications" / "environments" / "dev" / "kustomization.yaml"
        kust_file.unlink()

        validator = PromotionValidator("dev", "staging", gitops_root=tmp_gitops)
        assert not validator.validate()
        assert any("Required file missing" in e for e in validator.errors)


# ---------------------------------------------------------------------------
# Test PromotionEngine
# ---------------------------------------------------------------------------

class TestPromotionEngine:
    """Tests for PromotionEngine."""

    @pytest.mark.unit
    def test_dry_run_no_changes(self, tmp_gitops):
        """Dry run should not modify files."""
        engine = PromotionEngine("dev", "staging", dry_run=True, gitops_root=tmp_gitops)
        result = engine.promote()

        assert result.success
        assert result.validation_passed
        assert any("DRY RUN" in c for c in result.changes)

    @pytest.mark.unit
    def test_promotion_updates_application_name(self, tmp_gitops):
        """Promotion should update application name for target environment."""
        engine = PromotionEngine("dev", "staging", dry_run=False, gitops_root=tmp_gitops)
        result = engine.promote()

        assert result.success

        # Check staging application has correct name
        staging_app = tmp_gitops / "applications" / "environments" / "staging" / "mlflow-staging.yaml"
        assert staging_app.exists()

        with open(staging_app, "r") as f:
            data = yaml.safe_load(f)
        assert data["metadata"]["name"] == "mlflow-staging"

    @pytest.mark.unit
    def test_promotion_updates_environment_label(self, tmp_gitops):
        """Promotion should update environment label."""
        engine = PromotionEngine("dev", "staging", dry_run=False, gitops_root=tmp_gitops)
        result = engine.promote()

        assert result.success

        staging_app = tmp_gitops / "applications" / "environments" / "staging" / "mlflow-staging.yaml"
        with open(staging_app, "r") as f:
            data = yaml.safe_load(f)
        assert data["metadata"]["labels"]["environment"] == "staging"

    @pytest.mark.unit
    def test_promotion_updates_source_path(self, tmp_gitops):
        """Promotion should update source path to target overlay."""
        engine = PromotionEngine("dev", "staging", dry_run=False, gitops_root=tmp_gitops)
        result = engine.promote()

        assert result.success

        staging_app = tmp_gitops / "applications" / "environments" / "staging" / "mlflow-staging.yaml"
        with open(staging_app, "r") as f:
            data = yaml.safe_load(f)
        assert "staging" in data["spec"]["source"]["path"]

    @pytest.mark.unit
    def test_promotion_updates_target_revision(self, tmp_gitops):
        """Promotion should update targetRevision to target branch."""
        engine = PromotionEngine("dev", "staging", dry_run=False, gitops_root=tmp_gitops)
        result = engine.promote()

        assert result.success

        staging_app = tmp_gitops / "applications" / "environments" / "staging" / "mlflow-staging.yaml"
        with open(staging_app, "r") as f:
            data = yaml.safe_load(f)
        assert data["spec"]["source"]["targetRevision"] == ENV_BRANCHES["staging"]

    @pytest.mark.unit
    def test_promotion_validates_before_applying(self, tmp_gitops):
        """Promotion should fail if validation fails."""
        # Remove required file
        kust_file = tmp_gitops / "applications" / "environments" / "dev" / "kustomization.yaml"
        kust_file.unlink()

        engine = PromotionEngine("dev", "staging", dry_run=False, gitops_root=tmp_gitops)
        result = engine.promote()

        assert not result.success
        assert not result.validation_passed

    @pytest.mark.unit
    def test_promotion_reports_changes(self, tmp_gitops):
        """Promotion should report all changes made."""
        engine = PromotionEngine("dev", "staging", dry_run=False, gitops_root=tmp_gitops)
        result = engine.promote()

        assert result.success
        assert len(result.changes) > 0


# ---------------------------------------------------------------------------
# Test PR Description
# ---------------------------------------------------------------------------

class TestPRDescription:
    """Tests for PR description generation."""

    @pytest.mark.unit
    def test_pr_description_contains_environments(self):
        """PR description should contain source and target environments."""
        desc = create_promotion_pr("dev", "staging", ["change1", "change2"])
        assert "dev" in desc
        assert "staging" in desc

    @pytest.mark.unit
    def test_pr_production_requires_approval(self):
        """Production PR should mention approval requirement."""
        desc = create_promotion_pr("staging", "production", ["change1"])
        assert "PRODUCTION" in desc
        assert "approval" in desc.lower()

    @pytest.mark.unit
    def test_pr_non_production_auto_merge(self):
        """Non-production PR should mention auto-merge."""
        desc = create_promotion_pr("dev", "staging", ["change1"])
        assert "Auto-merge" in desc

    @pytest.mark.unit
    def test_pr_contains_changes(self):
        """PR description should list all changes."""
        changes = ["change1", "change2", "change3"]
        desc = create_promotion_pr("dev", "staging", changes)
        for change in changes:
            assert change in desc

    @pytest.mark.unit
    def test_pr_contains_validation_checklist(self):
        """PR description should contain validation checklist."""
        desc = create_promotion_pr("dev", "staging", [])
        assert "Validation" in desc
        assert "YAML syntax" in desc


# ---------------------------------------------------------------------------
# Test Notifications
# ---------------------------------------------------------------------------

class TestPromotionEvent:
    """Tests for PromotionEvent."""

    @pytest.mark.unit
    def test_event_has_timestamp(self):
        """Event should have a timestamp."""
        event = PromotionEvent(
            source_env="dev",
            target_env="staging",
            status="success",
            changes=[],
        )
        assert event.timestamp is not None

    @pytest.mark.unit
    def test_event_custom_timestamp(self):
        """Event should accept custom timestamp."""
        event = PromotionEvent(
            source_env="dev",
            target_env="staging",
            status="success",
            changes=[],
            timestamp="2024-01-01 00:00:00 UTC",
        )
        assert event.timestamp == "2024-01-01 00:00:00 UTC"


class TestSlackNotifier:
    """Tests for SlackNotifier."""

    @pytest.mark.unit
    def test_no_webhook_returns_false(self):
        """Should return False if no webhook URL configured."""
        notifier = SlackNotifier(webhook_url="")
        event = PromotionEvent("dev", "staging", "success", [])
        assert not notifier.send_promotion_notification(event)

    @pytest.mark.unit
    @patch("urllib.request.urlopen")
    def test_successful_notification(self, mock_urlopen):
        """Should return True on successful notification."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        event = PromotionEvent("dev", "staging", "success", ["change1"])
        assert notifier.send_promotion_notification(event)

    @pytest.mark.unit
    @patch("urllib.request.urlopen")
    def test_failed_notification(self, mock_urlopen):
        """Should return False on failed notification."""
        mock_urlopen.side_effect = Exception("Network error")

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        event = PromotionEvent("dev", "staging", "success", [])
        assert not notifier.send_promotion_notification(event)


class TestDocumentationUpdater:
    """Tests for DocumentationUpdater."""

    @pytest.mark.unit
    def test_creates_deployment_log(self, tmp_path):
        """Should create deployment log if it doesn't exist."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        updater = DocumentationUpdater(docs_path=docs_path)

        event = PromotionEvent("dev", "staging", "success", ["change1"])
        result = updater.update_deployment_log(event)

        assert Path(result).exists()
        content = Path(result).read_text()
        assert "dev" in content
        assert "staging" in content

    @pytest.mark.unit
    def test_appends_to_existing_log(self, tmp_path):
        """Should append to existing deployment log."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        log_file = docs_path / "deployment-log.md"
        log_file.write_text("# Deployment Log\n\n## Previous entry\n")

        updater = DocumentationUpdater(docs_path=docs_path)
        event = PromotionEvent("dev", "staging", "success", ["change1"])
        updater.update_deployment_log(event)

        content = log_file.read_text()
        assert "Previous entry" in content
        assert "dev" in content
        assert "staging" in content

    @pytest.mark.unit
    def test_creates_status_dashboard(self, tmp_path):
        """Should create status dashboard if it doesn't exist."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        updater = DocumentationUpdater(docs_path=docs_path)

        event = PromotionEvent("dev", "staging", "success", [])
        result = updater.update_status_dashboard(event)

        assert Path(result).exists()
        content = Path(result).read_text()
        assert "staging" in content


class TestNotifyPromotion:
    """Tests for notify_promotion function."""

    @pytest.mark.unit
    def test_returns_results_dict(self, tmp_path):
        """Should return a dictionary of results."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()

        with patch.object(DocumentationUpdater, "__init__", lambda self, docs_path=None: None):
            with patch.object(DocumentationUpdater, "update_deployment_log", return_value="log.md"):
                with patch.object(DocumentationUpdater, "update_status_dashboard", return_value="dashboard.md"):
                    with patch.object(SlackNotifier, "send_promotion_notification", return_value=False):
                        event = PromotionEvent("dev", "staging", "success", [])
                        results = notify_promotion(event)

        assert isinstance(results, dict)
        assert "slack" in results
        assert "deployment_log" in results
        assert "status_dashboard" in results


# ---------------------------------------------------------------------------
# Test Constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Tests for module constants."""

    @pytest.mark.unit
    def test_valid_promotions(self):
        """VALID_PROMOTIONS should contain expected paths."""
        assert ("dev", "staging") in VALID_PROMOTIONS
        assert ("staging", "production") in VALID_PROMOTIONS
        assert ("dev", "production") not in VALID_PROMOTIONS

    @pytest.mark.unit
    def test_env_branches(self):
        """ENV_BRANCHES should map environments to branches."""
        assert ENV_BRANCHES["dev"] == "develop"
        assert ENV_BRANCHES["staging"] == "staging"
        assert ENV_BRANCHES["production"] == "main"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
