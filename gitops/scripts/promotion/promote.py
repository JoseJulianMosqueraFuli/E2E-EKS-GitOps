"""
Environment Promotion Pipeline for GitOps MLOps Platform

Promotes changes through environments: dev → staging → production

Usage:
    python promote.py dev staging          # Promote dev to staging
    python promote.py staging production   # Promote staging to production
    python promote.py dev staging --dry-run  # Preview changes without applying
    python promote.py staging production --approve  # Skip approval gate
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Valid promotion paths
VALID_PROMOTIONS = {
    ("dev", "staging"),
    ("staging", "production"),
}

# Environment branch mapping
ENV_BRANCHES = {
    "dev": "develop",
    "staging": "staging",
    "production": "main",
}

# GitOps root directory (parent of scripts/)
GITOPS_ROOT = Path(__file__).parent.parent.parent


@dataclass
class PromotionResult:
    """Result of a promotion operation."""
    success: bool
    source_env: str
    target_env: str
    changes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    validation_passed: bool = False
    approval_required: bool = False


class PromotionValidator:
    """Validates promotion readiness."""

    def __init__(self, source_env: str, target_env: str, gitops_root: Optional[Path] = None):
        self.source_env = source_env
        self.target_env = target_env
        self.gitops_root = gitops_root or GITOPS_ROOT
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> bool:
        """Run all validation checks."""
        checks = [
            self._check_valid_promotion_path,
            self._check_source_environment_exists,
            self._check_target_environment_exists,
            self._check_argocd_applications_valid,
            self._check_kustomize_overlays_valid,
            self._check_no_yaml_syntax_errors,
            self._check_required_files_exist,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.errors.append(f"Validation check {check.__name__} failed: {e}")

        return len(self.errors) == 0

    def _check_valid_promotion_path(self):
        """Verify promotion path is valid."""
        if (self.source_env, self.target_env) not in VALID_PROMOTIONS:
            self.errors.append(
                f"Invalid promotion path: {self.source_env} → {self.target_env}. "
                f"Valid paths: {VALID_PROMOTIONS}"
            )

    def _check_source_environment_exists(self):
        """Verify source environment configurations exist."""
        infra_path = self.gitops_root / "infrastructure" / "clusters" / self.source_env
        apps_path = self.gitops_root / "applications" / "environments" / self.source_env

        if not infra_path.exists():
            self.errors.append(f"Source infrastructure not found: {infra_path}")
        if not apps_path.exists():
            self.errors.append(f"Source applications not found: {apps_path}")

    def _check_target_environment_exists(self):
        """Verify target environment configurations exist."""
        infra_path = self.gitops_root / "infrastructure" / "clusters" / self.target_env
        apps_path = self.gitops_root / "applications" / "environments" / self.target_env

        if not infra_path.exists():
            self.errors.append(f"Target infrastructure not found: {infra_path}")
        if not apps_path.exists():
            self.errors.append(f"Target applications not found: {apps_path}")

    def _check_argocd_applications_valid(self):
        """Verify ArgoCD Applications are valid YAML."""
        import yaml

        apps_path = self.gitops_root / "applications" / "environments" / self.source_env
        if not apps_path.exists():
            return

        for app_file in apps_path.glob("*-application.yaml"):
            try:
                with open(app_file, "r") as f:
                    data = yaml.safe_load(f)
                if data is None:
                    self.errors.append(f"Empty YAML file: {app_file}")
                elif data.get("kind") != "Application":
                    self.errors.append(
                        f"Expected Application kind in {app_file}, got {data.get('kind')}"
                    )
            except yaml.YAMLError as e:
                self.errors.append(f"Invalid YAML in {app_file}: {e}")

    def _check_kustomize_overlays_valid(self):
        """Verify Kustomize overlays are valid."""
        import yaml

        apps = ["mlflow", "kubeflow", "kserve", "monitoring"]
        for app in apps:
            overlay_path = (
                self.gitops_root / "applications" / "apps" / app / "overlays" / self.source_env
            )
            if overlay_path.exists():
                kust_file = overlay_path / "kustomization.yaml"
                if kust_file.exists():
                    try:
                        with open(kust_file, "r") as f:
                            data = yaml.safe_load(f)
                        if data is None:
                            self.errors.append(f"Empty kustomization: {kust_file}")
                    except yaml.YAMLError as e:
                        self.errors.append(f"Invalid kustomization {kust_file}: {e}")

    def _check_no_yaml_syntax_errors(self):
        """Check all YAML files in source environment for syntax errors."""
        import yaml

        yaml_files = list((self.gitops_root / "applications" / "environments" / self.source_env).rglob("*.yaml"))
        yaml_files.extend(
            (self.gitops_root / "infrastructure" / "clusters" / self.source_env).rglob("*.yaml")
        )

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r") as f:
                    list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                self.errors.append(f"YAML syntax error in {yaml_file}: {e}")

    def _check_required_files_exist(self):
        """Verify required files exist in source environment."""
        required = [
            self.gitops_root / "applications" / "environments" / self.source_env / "kustomization.yaml",
            self.gitops_root / "infrastructure" / "clusters" / self.source_env / "kustomization.yaml",
        ]

        for path in required:
            if not path.exists():
                self.errors.append(f"Required file missing: {path}")


class PromotionEngine:
    """Handles the actual promotion of configurations."""

    def __init__(self, source_env: str, target_env: str, dry_run: bool = False, gitops_root: Optional[Path] = None):
        self.source_env = source_env
        self.target_env = target_env
        self.dry_run = dry_run
        self.gitops_root = gitops_root or GITOPS_ROOT
        self.changes: List[str] = []

    def promote(self) -> PromotionResult:
        """Execute the promotion."""
        result = PromotionResult(
            success=False,
            source_env=self.source_env,
            target_env=self.target_env,
        )

        # Validate first
        validator = PromotionValidator(self.source_env, self.target_env, gitops_root=self.gitops_root)
        result.validation_passed = validator.validate()

        if not result.validation_passed:
            result.errors.extend(validator.errors)
            return result

        try:
            # Promote application configurations
            app_changes = self._promote_applications()
            self.changes.extend(app_changes)

            # Promote infrastructure configurations
            infra_changes = self._promote_infrastructure()
            self.changes.extend(infra_changes)

            # Promote cluster configurations
            cluster_changes = self._promote_cluster()
            self.changes.extend(cluster_changes)

            result.changes = self.changes
            result.success = True

        except Exception as e:
            result.errors.append(f"Promotion failed: {e}")

        return result

    def _promote_applications(self) -> List[str]:
        """Promote application configurations from source to target."""
        changes = []
        source_apps = self.gitops_root / "applications" / "environments" / self.source_env
        target_apps = self.gitops_root / "applications" / "environments" / self.target_env

        if not source_apps.exists():
            return changes

        for app_file in source_apps.glob("*.yaml"):
            if app_file.name == "kustomization.yaml":
                continue

            # Extract app name from filename (e.g., mlflow-dev.yaml -> mlflow)
            stem = app_file.stem
            app_name = stem.replace(f"-{self.source_env}", "")
            target_file = target_apps / f"{app_name}-{self.target_env}.yaml"

            if self.dry_run:
                changes.append(f"[DRY RUN] Would update {target_file}")
                continue

            # Read source and update for target
            import yaml
            with open(app_file, "r") as f:
                data = yaml.safe_load(f)

            if data:
                # Update metadata
                data["metadata"]["name"] = f"{app_name}-{self.target_env}"
                data["metadata"]["labels"]["environment"] = self.target_env

                # Update source path to target overlay
                data["spec"]["source"]["path"] = f"apps/{app_name}/overlays/{self.target_env}"

                # Update target revision
                data["spec"]["source"]["targetRevision"] = ENV_BRANCHES[self.target_env]

                # Update notification annotations for target environment
                if "annotations" not in data["metadata"]:
                    data["metadata"]["annotations"] = {}

                # Update Slack channel based on environment
                for key in list(data["metadata"]["annotations"].keys()):
                    if "slack" in key:
                        old_channel = data["metadata"]["annotations"][key]
                        if self.target_env == "production":
                            new_channel = old_channel.replace("-dev", "").replace("alerts", "deployments")
                        else:
                            new_channel = old_channel
                        data["metadata"]["annotations"][key] = new_channel

                # Write updated file
                with open(target_file, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

                changes.append(f"Updated {target_file}")

        return changes

    def _promote_infrastructure(self) -> List[str]:
        """Promote infrastructure configurations."""
        changes = []
        source_infra = self.gitops_root / "infrastructure" / "clusters" / self.source_env / "infrastructure"
        target_infra = self.gitops_root / "infrastructure" / "clusters" / self.target_env / "infrastructure"

        if not source_infra.exists() or not target_infra.exists():
            return changes

        # The infrastructure kustomization already references the correct paths
        # Just verify it's properly configured
        import yaml
        target_kust = target_infra / "kustomization.yaml"
        if target_kust.exists():
            with open(target_kust, "r") as f:
                data = yaml.safe_load(f)

            if data:
                # Verify commonLabels has correct environment
                labels = data.get("commonLabels", {})
                if labels.get("environment") != self.target_env:
                    if self.dry_run:
                        changes.append(f"[DRY RUN] Would update environment label in {target_kust}")
                    else:
                        data["commonLabels"]["environment"] = self.target_env
                        with open(target_kust, "w") as f:
                            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                        changes.append(f"Updated environment label in {target_kust}")

        return changes

    def _promote_cluster(self) -> List[str]:
        """Promote cluster configurations."""
        changes = []
        source_config = self.gitops_root / "infrastructure" / "clusters" / self.source_env / "config"
        target_config = self.gitops_root / "infrastructure" / "clusters" / self.target_env / "config"

        if not source_config.exists() or not target_config.exists():
            return changes

        import yaml
        target_cluster_config = target_config / "cluster-config.yaml"
        if target_cluster_config.exists():
            # Cluster config is environment-specific, don't overwrite
            # Just verify it exists
            changes.append(f"Verified cluster config exists: {target_cluster_config}")

        return changes


def create_promotion_pr(source_env: str, target_env: str, changes: List[str]) -> str:
    """Create a promotion pull request description."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    pr_body = f"""# Environment Promotion: {source_env} → {target_env}

**Promoted at**: {timestamp}
**Promoted by**: Automated Pipeline

## Changes

"""
    for change in changes:
        pr_body += f"- {change}\n"

    pr_body += f"""

## Validation

- [x] Source environment validated
- [x] YAML syntax verified
- [x] ArgoCD Applications valid
- [x] Kustomize overlays valid
- [x] Required files present

## Approval Required

{'⚠️ **PRODUCTION PROMOTION** - Manual approval required before merge.' if target_env == 'production' else '✅ Auto-merge enabled for non-production environments.'}

## Post-Merge Actions

1. ArgoCD will automatically sync the {target_env} environment
2. Monitor deployment status in ArgoCD UI
3. Verify application health in {target_env}
"""
    return pr_body


def main():
    parser = argparse.ArgumentParser(
        description="Promote GitOps configurations between environments"
    )
    parser.add_argument(
        "source",
        choices=["dev", "staging"],
        help="Source environment",
    )
    parser.add_argument(
        "target",
        choices=["staging", "production"],
        help="Target environment",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Skip approval gate (for CI/CD)",
    )
    parser.add_argument(
        "--output-pr",
        action="store_true",
        help="Output PR description to stdout",
    )

    args = parser.parse_args()

    # Validate promotion path
    if (args.source, args.target) not in VALID_PROMOTIONS:
        print(f"Error: Invalid promotion path {args.source} → {args.target}")
        sys.exit(1)

    # Approval gate for production
    if args.target == "production" and not args.approve and not args.dry_run:
        print("⚠️  Production promotion requires --approve flag")
        print("This should typically be done through a PR approval process")
        sys.exit(1)

    print(f"Promoting {args.source} → {args.target}")
    if args.dry_run:
        print("[DRY RUN] No changes will be applied")
    print()

    # Run promotion
    engine = PromotionEngine(args.source, args.target, dry_run=args.dry_run)
    result = engine.promote()

    if result.success:
        print(f"✅ Promotion successful!")
        print(f"\nChanges ({len(result.changes)}):")
        for change in result.changes:
            print(f"  - {change}")

        if args.output_pr:
            print("\n--- PR Description ---")
            print(create_promotion_pr(args.source, args.target, result.changes))
    else:
        print(f"❌ Promotion failed!")
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
