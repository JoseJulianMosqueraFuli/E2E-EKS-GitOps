"""
Unit Tests for Repository Structure Validation


This module contains unit tests to verify that the GitOps repository structure
complies with GitOps patterns and best practices for:
- Infrastructure repository with Flux configurations
- Applications repository with ArgoCD configurations
- Helm charts repository for MLOps components
- Kustomize overlay configurations
"""

import os
import pytest
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set


# Base paths - resolve relative to the gitops directory
# When running from gitops/ with poetry, __file__ is in gitops/tests/
GITOPS_ROOT = Path(__file__).parent.parent.resolve()
INFRASTRUCTURE_PATH = GITOPS_ROOT / "infrastructure"
APPLICATIONS_PATH = GITOPS_ROOT / "applications"
CHARTS_PATH = GITOPS_ROOT / "charts"

# Expected environments
EXPECTED_ENVIRONMENTS = {"dev", "staging", "production"}

# Expected MLOps applications
EXPECTED_APPLICATIONS = {"mlflow", "kubeflow", "kserve", "monitoring"}

# Expected Helm charts
EXPECTED_CHARTS = {"mlflow", "kubeflow-pipelines", "kserve", "monitoring-stack"}

# Required Kustomization fields
REQUIRED_KUSTOMIZATION_FIELDS = {"apiVersion", "kind"}

# Required Helm Chart fields
REQUIRED_CHART_FIELDS = {"apiVersion", "name", "version"}


def load_yaml_file(file_path: Path) -> Optional[Dict]:
    """Load and parse a YAML file"""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, FileNotFoundError) as e:
        return None


def find_yaml_files(directory: Path, pattern: str = "*.yaml") -> List[Path]:
    """Find all YAML files in a directory recursively"""
    if not directory.exists():
        return []
    return list(directory.rglob(pattern))


class TestInfrastructureRepositoryStructure:
    """Tests for infrastructure repository structure (Requirement 2.1, 2.3)"""

    @pytest.mark.unit
    def test_infrastructure_directory_exists(self):
        """Verify infrastructure directory exists"""
        assert INFRASTRUCTURE_PATH.exists(), \
            f"Infrastructure directory not found at {INFRASTRUCTURE_PATH}"

    @pytest.mark.unit
    def test_infrastructure_has_clusters_directory(self):
        """Verify clusters directory exists for environment-specific configs"""
        clusters_path = INFRASTRUCTURE_PATH / "clusters"
        assert clusters_path.exists(), \
            "Infrastructure must have a 'clusters' directory for environment configs"

    @pytest.mark.unit
    def test_infrastructure_has_all_environments(self):
        """Verify all expected environments exist in clusters directory"""
        clusters_path = INFRASTRUCTURE_PATH / "clusters"
        existing_envs = {d.name for d in clusters_path.iterdir() if d.is_dir()}
        
        missing_envs = EXPECTED_ENVIRONMENTS - existing_envs
        assert len(missing_envs) == 0, \
            f"Missing environment directories in clusters: {missing_envs}"

    @pytest.mark.unit
    def test_infrastructure_has_controllers_directory(self):
        """Verify controllers directory exists for GitOps controllers"""
        controllers_path = INFRASTRUCTURE_PATH / "controllers"
        assert controllers_path.exists(), \
            "Infrastructure must have a 'controllers' directory"

    @pytest.mark.unit
    def test_flux_system_controller_exists(self):
        """Verify Flux system controller configuration exists"""
        flux_path = INFRASTRUCTURE_PATH / "controllers" / "flux-system"
        assert flux_path.exists(), \
            "Flux system controller directory not found"

    @pytest.mark.unit
    def test_argocd_controller_exists(self):
        """Verify ArgoCD controller configuration exists"""
        argocd_path = INFRASTRUCTURE_PATH / "controllers" / "argocd"
        assert argocd_path.exists(), \
            "ArgoCD controller directory not found"

    @pytest.mark.unit
    def test_infrastructure_has_sources_directory(self):
        """Verify sources directory exists for Flux source configurations"""
        sources_path = INFRASTRUCTURE_PATH / "sources"
        assert sources_path.exists(), \
            "Infrastructure must have a 'sources' directory for Flux sources"

    @pytest.mark.unit
    def test_git_repository_source_exists(self):
        """Verify Git repository source configuration exists"""
        git_repo_path = INFRASTRUCTURE_PATH / "sources" / "git-repository.yaml"
        assert git_repo_path.exists(), \
            "Git repository source configuration not found"

    @pytest.mark.unit
    def test_each_cluster_has_flux_system(self):
        """Verify each cluster environment has flux-system configuration"""
        clusters_path = INFRASTRUCTURE_PATH / "clusters"
        
        for env in EXPECTED_ENVIRONMENTS:
            env_path = clusters_path / env
            if env_path.exists():
                flux_system_path = env_path / "flux-system"
                assert flux_system_path.exists(), \
                    f"Environment {env} missing flux-system directory"

    @pytest.mark.unit
    def test_each_cluster_has_kustomization(self):
        """Verify each cluster environment has a kustomization.yaml"""
        clusters_path = INFRASTRUCTURE_PATH / "clusters"
        
        for env in EXPECTED_ENVIRONMENTS:
            env_path = clusters_path / env
            if env_path.exists():
                kustomization_path = env_path / "kustomization.yaml"
                assert kustomization_path.exists(), \
                    f"Environment {env} missing kustomization.yaml"


class TestApplicationsRepositoryStructure:
    """Tests for applications repository structure (Requirement 2.2, 2.5)"""

    @pytest.mark.unit
    def test_applications_directory_exists(self):
        """Verify applications directory exists"""
        assert APPLICATIONS_PATH.exists(), \
            f"Applications directory not found at {APPLICATIONS_PATH}"

    @pytest.mark.unit
    def test_applications_has_apps_directory(self):
        """Verify apps directory exists for application manifests"""
        apps_path = APPLICATIONS_PATH / "apps"
        assert apps_path.exists(), \
            "Applications must have an 'apps' directory"

    @pytest.mark.unit
    def test_applications_has_projects_directory(self):
        """Verify projects directory exists for ArgoCD projects"""
        projects_path = APPLICATIONS_PATH / "projects"
        assert projects_path.exists(), \
            "Applications must have a 'projects' directory for ArgoCD projects"

    @pytest.mark.unit
    def test_all_expected_applications_exist(self):
        """Verify all expected MLOps applications have directories"""
        apps_path = APPLICATIONS_PATH / "apps"
        existing_apps = {d.name for d in apps_path.iterdir() if d.is_dir()}
        
        missing_apps = EXPECTED_APPLICATIONS - existing_apps
        assert len(missing_apps) == 0, \
            f"Missing application directories: {missing_apps}"

    @pytest.mark.unit
    def test_each_application_has_base_directory(self):
        """Verify each application has a base directory for Kustomize"""
        apps_path = APPLICATIONS_PATH / "apps"
        
        for app in EXPECTED_APPLICATIONS:
            app_path = apps_path / app
            if app_path.exists():
                base_path = app_path / "base"
                assert base_path.exists(), \
                    f"Application {app} missing 'base' directory"

    @pytest.mark.unit
    def test_each_application_has_overlays_directory(self):
        """Verify each application has an overlays directory"""
        apps_path = APPLICATIONS_PATH / "apps"
        
        for app in EXPECTED_APPLICATIONS:
            app_path = apps_path / app
            if app_path.exists():
                overlays_path = app_path / "overlays"
                assert overlays_path.exists(), \
                    f"Application {app} missing 'overlays' directory"

    @pytest.mark.unit
    def test_each_application_has_all_environment_overlays(self):
        """Verify each application has overlays for all environments"""
        apps_path = APPLICATIONS_PATH / "apps"
        
        for app in EXPECTED_APPLICATIONS:
            overlays_path = apps_path / app / "overlays"
            if overlays_path.exists():
                existing_envs = {d.name for d in overlays_path.iterdir() if d.is_dir()}
                missing_envs = EXPECTED_ENVIRONMENTS - existing_envs
                assert len(missing_envs) == 0, \
                    f"Application {app} missing environment overlays: {missing_envs}"

    @pytest.mark.unit
    def test_argocd_project_definition_exists(self):
        """Verify ArgoCD project definition exists"""
        projects_path = APPLICATIONS_PATH / "projects"
        project_files = list(projects_path.glob("*.yaml"))
        
        assert len(project_files) > 0, \
            "No ArgoCD project definitions found in projects directory"


class TestHelmChartsRepository:
    """Tests for Helm charts repository structure (Requirement 2.4)"""

    @pytest.mark.unit
    def test_charts_directory_exists(self):
        """Verify charts directory exists"""
        assert CHARTS_PATH.exists(), \
            f"Charts directory not found at {CHARTS_PATH}"

    @pytest.mark.unit
    def test_all_expected_charts_exist(self):
        """Verify all expected Helm charts have directories"""
        existing_charts = {d.name for d in CHARTS_PATH.iterdir() if d.is_dir()}
        
        missing_charts = EXPECTED_CHARTS - existing_charts
        assert len(missing_charts) == 0, \
            f"Missing Helm chart directories: {missing_charts}"

    @pytest.mark.unit
    def test_each_chart_has_chart_yaml(self):
        """Verify each chart has a Chart.yaml file"""
        for chart in EXPECTED_CHARTS:
            chart_path = CHARTS_PATH / chart
            if chart_path.exists():
                chart_yaml_path = chart_path / "Chart.yaml"
                assert chart_yaml_path.exists(), \
                    f"Chart {chart} missing Chart.yaml"

    @pytest.mark.unit
    def test_each_chart_has_values_yaml(self):
        """Verify each chart has a values.yaml file"""
        for chart in EXPECTED_CHARTS:
            chart_path = CHARTS_PATH / chart
            if chart_path.exists():
                values_yaml_path = chart_path / "values.yaml"
                assert values_yaml_path.exists(), \
                    f"Chart {chart} missing values.yaml"

    @pytest.mark.unit
    def test_each_chart_has_templates_directory(self):
        """Verify each chart has a templates directory"""
        for chart in EXPECTED_CHARTS:
            chart_path = CHARTS_PATH / chart
            if chart_path.exists():
                templates_path = chart_path / "templates"
                assert templates_path.exists(), \
                    f"Chart {chart} missing templates directory"

    @pytest.mark.unit
    def test_chart_index_exists(self):
        """Verify Helm chart index.yaml exists"""
        index_path = CHARTS_PATH / "index.yaml"
        assert index_path.exists(), \
            "Helm chart repository index.yaml not found"

    @pytest.mark.unit
    def test_chart_yaml_has_required_fields(self):
        """Verify each Chart.yaml has required fields"""
        for chart in EXPECTED_CHARTS:
            chart_yaml_path = CHARTS_PATH / chart / "Chart.yaml"
            if chart_yaml_path.exists():
                chart_data = load_yaml_file(chart_yaml_path)
                assert chart_data is not None, \
                    f"Failed to parse Chart.yaml for {chart}"
                
                missing_fields = REQUIRED_CHART_FIELDS - set(chart_data.keys())
                assert len(missing_fields) == 0, \
                    f"Chart {chart} missing required fields: {missing_fields}"

    @pytest.mark.unit
    def test_chart_versions_are_valid(self):
        """Verify chart versions follow semantic versioning"""
        import re
        semver_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'
        
        for chart in EXPECTED_CHARTS:
            chart_yaml_path = CHARTS_PATH / chart / "Chart.yaml"
            if chart_yaml_path.exists():
                chart_data = load_yaml_file(chart_yaml_path)
                if chart_data and 'version' in chart_data:
                    version = chart_data['version']
                    assert re.match(semver_pattern, version), \
                        f"Chart {chart} has invalid version format: {version}"


class TestKustomizeOverlayConfigurations:
    """Tests for Kustomize overlay configurations (Requirement 2.5)"""

    @pytest.mark.unit
    def test_base_kustomizations_are_valid(self):
        """Verify base kustomization.yaml files are valid"""
        apps_path = APPLICATIONS_PATH / "apps"
        
        for app in EXPECTED_APPLICATIONS:
            base_kustomization = apps_path / app / "base" / "kustomization.yaml"
            if base_kustomization.exists():
                data = load_yaml_file(base_kustomization)
                assert data is not None, \
                    f"Failed to parse base kustomization for {app}"
                
                missing_fields = REQUIRED_KUSTOMIZATION_FIELDS - set(data.keys())
                assert len(missing_fields) == 0, \
                    f"Base kustomization for {app} missing fields: {missing_fields}"

    @pytest.mark.unit
    def test_overlay_kustomizations_reference_base(self):
        """Verify overlay kustomizations reference their base"""
        apps_path = APPLICATIONS_PATH / "apps"
        
        for app in EXPECTED_APPLICATIONS:
            for env in EXPECTED_ENVIRONMENTS:
                overlay_kustomization = apps_path / app / "overlays" / env / "kustomization.yaml"
                if overlay_kustomization.exists():
                    data = load_yaml_file(overlay_kustomization)
                    assert data is not None, \
                        f"Failed to parse overlay kustomization for {app}/{env}"
                    
                    # Check that resources include base reference
                    resources = data.get('resources', [])
                    has_base_ref = any('base' in str(r) for r in resources)
                    assert has_base_ref, \
                        f"Overlay {app}/{env} does not reference base directory"

    @pytest.mark.unit
    def test_overlay_kustomizations_have_environment_labels(self):
        """Verify overlay kustomizations include environment labels"""
        apps_path = APPLICATIONS_PATH / "apps"
        
        for app in EXPECTED_APPLICATIONS:
            for env in EXPECTED_ENVIRONMENTS:
                overlay_kustomization = apps_path / app / "overlays" / env / "kustomization.yaml"
                if overlay_kustomization.exists():
                    data = load_yaml_file(overlay_kustomization)
                    if data:
                        # Check for labels or commonLabels
                        has_labels = 'labels' in data or 'commonLabels' in data
                        has_name_prefix = 'namePrefix' in data
                        
                        # At least one environment identifier should be present
                        assert has_labels or has_name_prefix, \
                            f"Overlay {app}/{env} should have environment labels or namePrefix"

    @pytest.mark.unit
    def test_kustomization_api_version_is_correct(self):
        """Verify kustomization files use correct API version"""
        valid_api_versions = {
            "kustomize.config.k8s.io/v1beta1",
            "kustomize.config.k8s.io/v1"
        }
        
        kustomization_files = find_yaml_files(APPLICATIONS_PATH, "kustomization.yaml")
        
        for kust_file in kustomization_files:
            data = load_yaml_file(kust_file)
            if data and 'apiVersion' in data:
                assert data['apiVersion'] in valid_api_versions, \
                    f"Invalid apiVersion in {kust_file}: {data['apiVersion']}"


class TestFluxConfigurations:
    """Tests for Flux-specific configurations"""

    @pytest.mark.unit
    def test_flux_kustomization_files_exist(self):
        """Verify Flux kustomization configurations exist"""
        flux_config_path = INFRASTRUCTURE_PATH / "flux-config"
        assert flux_config_path.exists(), \
            "Flux configuration directory not found"
        
        kustomization_files = list(flux_config_path.glob("*.yaml"))
        assert len(kustomization_files) > 0, \
            "No Flux kustomization files found"

    @pytest.mark.unit
    def test_flux_source_controller_config_exists(self):
        """Verify Flux source controller configuration exists"""
        flux_system_path = INFRASTRUCTURE_PATH / "controllers" / "flux-system"
        source_controller = flux_system_path / "source-controller.yaml"
        
        assert source_controller.exists(), \
            "Flux source-controller.yaml not found"

    @pytest.mark.unit
    def test_flux_kustomize_controller_config_exists(self):
        """Verify Flux kustomize controller configuration exists"""
        flux_system_path = INFRASTRUCTURE_PATH / "controllers" / "flux-system"
        kustomize_controller = flux_system_path / "kustomize-controller.yaml"
        
        assert kustomize_controller.exists(), \
            "Flux kustomize-controller.yaml not found"

    @pytest.mark.unit
    def test_flux_helm_controller_config_exists(self):
        """Verify Flux helm controller configuration exists"""
        flux_system_path = INFRASTRUCTURE_PATH / "controllers" / "flux-system"
        helm_controller = flux_system_path / "helm-controller.yaml"
        
        assert helm_controller.exists(), \
            "Flux helm-controller.yaml not found"


class TestArgocdConfigurations:
    """Tests for ArgoCD-specific configurations"""

    @pytest.mark.unit
    def test_argocd_namespace_config_exists(self):
        """Verify ArgoCD namespace configuration exists"""
        argocd_path = INFRASTRUCTURE_PATH / "controllers" / "argocd"
        namespace_file = argocd_path / "namespace.yaml"
        
        assert namespace_file.exists(), \
            "ArgoCD namespace.yaml not found"

    @pytest.mark.unit
    def test_argocd_rbac_config_exists(self):
        """Verify ArgoCD RBAC configuration exists"""
        argocd_path = INFRASTRUCTURE_PATH / "controllers" / "argocd"
        rbac_file = argocd_path / "rbac-config.yaml"
        
        assert rbac_file.exists(), \
            "ArgoCD rbac-config.yaml not found"

    @pytest.mark.unit
    def test_argocd_project_has_valid_structure(self):
        """Verify ArgoCD project definitions have valid structure"""
        projects_path = APPLICATIONS_PATH / "projects"
        
        for project_file in projects_path.glob("*.yaml"):
            data = load_yaml_file(project_file)
            if data:
                # Check for AppProject or Application kind
                kind = data.get('kind', '')
                valid_kinds = {'AppProject', 'Application', 'ApplicationSet', 'HelmRepository'}
                assert kind in valid_kinds, \
                    f"Invalid kind in {project_file.name}: {kind}"


class TestSecurityConfigurations:
    """Tests for security-related configurations"""

    @pytest.mark.unit
    def test_security_directory_exists(self):
        """Verify security directory exists"""
        security_path = INFRASTRUCTURE_PATH / "security"
        assert security_path.exists(), \
            "Security directory not found in infrastructure"

    @pytest.mark.unit
    def test_rbac_policies_exist(self):
        """Verify RBAC policies configuration exists"""
        rbac_path = INFRASTRUCTURE_PATH / "security" / "rbac-policies.yaml"
        assert rbac_path.exists(), \
            "RBAC policies configuration not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
