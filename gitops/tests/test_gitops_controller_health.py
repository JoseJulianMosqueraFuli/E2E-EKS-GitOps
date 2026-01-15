"""
Property-Based Tests for GitOps Controller Health

Feature: gitops-implementation, Property 1: GitOps Controller Health
Validates: Requirements 1.1, 1.2

This module contains property-based tests to verify that GitOps controllers
(ArgoCD and Flux) are properly installed and maintain healthy status across
various deployment configurations.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time
from typing import Dict, List, Tuple


# Test configuration
FLUX_NAMESPACE = "flux-system"
ARGOCD_NAMESPACE = "argocd"

# Expected Flux controllers
FLUX_CONTROLLERS = [
    "source-controller",
    "kustomize-controller",
    "helm-controller",
    "notification-controller"
]

# Expected ArgoCD controllers
ARGOCD_CONTROLLERS = [
    "argocd-server",
    "argocd-repo-server",
    "argocd-application-controller",
    "argocd-dex-server",
    "argocd-redis"
]


class KubernetesClientWrapper:
    """Wrapper for Kubernetes client to handle connection and API calls"""
    
    def __init__(self):
        try:
            # Try to load in-cluster config first
            config.load_incluster_config()
        except config.ConfigException:
            # Fall back to kubeconfig
            try:
                config.load_kube_config()
            except config.ConfigException:
                raise RuntimeError(
                    "Could not configure Kubernetes client. "
                    "Ensure you have a valid kubeconfig or are running in-cluster."
                )
        
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
    
    def get_deployment(self, name: str, namespace: str) -> client.V1Deployment:
        """Get a deployment by name and namespace"""
        try:
            return self.apps_v1.read_namespaced_deployment(name, namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise
    
    def get_namespace(self, name: str) -> client.V1Namespace:
        """Get a namespace by name"""
        try:
            return self.core_v1.read_namespace(name)
        except ApiException as e:
            if e.status == 404:
                return None
            raise
    
    def list_deployments(self, namespace: str) -> List[client.V1Deployment]:
        """List all deployments in a namespace"""
        try:
            result = self.apps_v1.list_namespaced_deployment(namespace)
            return result.items
        except ApiException as e:
            if e.status == 404:
                return []
            raise


def check_deployment_health(deployment: client.V1Deployment) -> Tuple[bool, str]:
    """
    Check if a deployment is healthy
    
    Returns:
        Tuple of (is_healthy, reason)
    """
    if deployment is None:
        return False, "Deployment not found"
    
    status = deployment.status
    spec = deployment.spec
    
    # Check if deployment exists
    if status is None:
        return False, "Deployment status is None"
    
    # Check replicas
    desired_replicas = spec.replicas or 1
    ready_replicas = status.ready_replicas or 0
    available_replicas = status.available_replicas or 0
    
    if ready_replicas < desired_replicas:
        return False, f"Not all replicas ready: {ready_replicas}/{desired_replicas}"
    
    if available_replicas < desired_replicas:
        return False, f"Not all replicas available: {available_replicas}/{desired_replicas}"
    
    # Check conditions
    if status.conditions:
        for condition in status.conditions:
            if condition.type == "Available" and condition.status != "True":
                return False, f"Deployment not available: {condition.reason}"
            if condition.type == "Progressing" and condition.status != "True":
                return False, f"Deployment not progressing: {condition.reason}"
    
    return True, "Healthy"


def check_namespace_exists(k8s_client: KubernetesClientWrapper, namespace: str) -> bool:
    """Check if a namespace exists"""
    ns = k8s_client.get_namespace(namespace)
    return ns is not None


# Hypothesis strategies for generating test data
@st.composite
def controller_config(draw):
    """Generate a controller configuration for testing"""
    return {
        "namespace": draw(st.sampled_from([FLUX_NAMESPACE, ARGOCD_NAMESPACE])),
        "check_interval": draw(st.integers(min_value=1, max_value=10)),
        "timeout": draw(st.integers(min_value=30, max_value=300))
    }


# Property 1: GitOps Controller Health
# For any GitOps controller (ArgoCD or Flux), when the controller is deployed,
# all required components should be running and report healthy status

@pytest.mark.property
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(config=controller_config())
def test_gitops_controller_health_property(config: Dict):
    """
    Feature: gitops-implementation, Property 1: GitOps Controller Health
    Validates: Requirements 1.1, 1.2
    
    Property: For any GitOps controller namespace (flux-system or argocd),
    all expected controller deployments should exist and be in a healthy state.
    
    This property verifies that:
    1. The controller namespace exists
    2. All expected controller deployments are present
    3. All deployments have the desired number of replicas ready
    4. All deployments report healthy status conditions
    """
    k8s_client = KubernetesClientWrapper()
    namespace = config["namespace"]
    
    # Verify namespace exists
    assert check_namespace_exists(k8s_client, namespace), \
        f"Namespace {namespace} does not exist"
    
    # Determine which controllers to check based on namespace
    if namespace == FLUX_NAMESPACE:
        expected_controllers = FLUX_CONTROLLERS
    else:
        expected_controllers = ARGOCD_CONTROLLERS
    
    # Check each controller deployment
    unhealthy_controllers = []
    missing_controllers = []
    
    for controller_name in expected_controllers:
        deployment = k8s_client.get_deployment(controller_name, namespace)
        
        if deployment is None:
            missing_controllers.append(controller_name)
            continue
        
        is_healthy, reason = check_deployment_health(deployment)
        
        if not is_healthy:
            unhealthy_controllers.append({
                "name": controller_name,
                "reason": reason,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "desired_replicas": deployment.spec.replicas or 1
            })
    
    # Assert all controllers are present
    assert len(missing_controllers) == 0, \
        f"Missing controllers in {namespace}: {missing_controllers}"
    
    # Assert all controllers are healthy
    assert len(unhealthy_controllers) == 0, \
        f"Unhealthy controllers in {namespace}: {unhealthy_controllers}"


@pytest.mark.property
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(
    namespace=st.sampled_from([FLUX_NAMESPACE, ARGOCD_NAMESPACE]),
    min_replicas=st.integers(min_value=1, max_value=3)
)
def test_controller_replica_consistency(namespace: str, min_replicas: int):
    """
    Feature: gitops-implementation, Property 1: GitOps Controller Health
    Validates: Requirements 1.1, 1.2
    
    Property: For any GitOps controller deployment, the number of ready replicas
    should always equal or exceed the minimum required replicas for high availability.
    
    This ensures controllers maintain availability even under various configurations.
    """
    k8s_client = KubernetesClientWrapper()
    
    # Get all deployments in the namespace
    deployments = k8s_client.list_deployments(namespace)
    
    assert len(deployments) > 0, f"No deployments found in {namespace}"
    
    for deployment in deployments:
        ready_replicas = deployment.status.ready_replicas or 0
        desired_replicas = deployment.spec.replicas or 1
        
        # Property: ready replicas should match desired replicas
        assert ready_replicas == desired_replicas, \
            f"Deployment {deployment.metadata.name} has {ready_replicas} ready " \
            f"replicas but desires {desired_replicas}"
        
        # For production readiness, check minimum replicas
        if min_replicas > 1:
            assert ready_replicas >= min_replicas, \
                f"Deployment {deployment.metadata.name} has {ready_replicas} " \
                f"replicas but minimum required is {min_replicas} for HA"


@pytest.mark.property
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(
    check_count=st.integers(min_value=2, max_value=5),
    interval_seconds=st.integers(min_value=1, max_value=5)
)
def test_controller_health_stability(check_count: int, interval_seconds: int):
    """
    Feature: gitops-implementation, Property 1: GitOps Controller Health
    Validates: Requirements 1.1, 1.2
    
    Property: For any GitOps controller, health status should remain stable
    over multiple consecutive checks, demonstrating consistent availability.
    
    This property verifies that controllers don't flap between healthy and
    unhealthy states, which would indicate instability.
    """
    k8s_client = KubernetesClientWrapper()
    
    # Check both Flux and ArgoCD controllers
    for namespace, controllers in [
        (FLUX_NAMESPACE, FLUX_CONTROLLERS),
        (ARGOCD_NAMESPACE, ARGOCD_CONTROLLERS)
    ]:
        if not check_namespace_exists(k8s_client, namespace):
            continue
        
        for controller_name in controllers:
            health_checks = []
            
            # Perform multiple health checks
            for _ in range(check_count):
                deployment = k8s_client.get_deployment(controller_name, namespace)
                
                if deployment is not None:
                    is_healthy, _ = check_deployment_health(deployment)
                    health_checks.append(is_healthy)
                
                if _ < check_count - 1:  # Don't sleep after last check
                    time.sleep(interval_seconds)
            
            # Property: All health checks should return the same result (stability)
            if len(health_checks) > 0:
                first_status = health_checks[0]
                assert all(status == first_status for status in health_checks), \
                    f"Controller {controller_name} in {namespace} showed unstable " \
                    f"health status across {check_count} checks: {health_checks}"


# Unit tests for specific scenarios

@pytest.mark.unit
def test_flux_namespace_exists():
    """Unit test: Verify Flux namespace exists"""
    k8s_client = KubernetesClientWrapper()
    assert check_namespace_exists(k8s_client, FLUX_NAMESPACE), \
        f"Flux namespace {FLUX_NAMESPACE} does not exist"


@pytest.mark.unit
def test_argocd_namespace_exists():
    """Unit test: Verify ArgoCD namespace exists"""
    k8s_client = KubernetesClientWrapper()
    assert check_namespace_exists(k8s_client, ARGOCD_NAMESPACE), \
        f"ArgoCD namespace {ARGOCD_NAMESPACE} does not exist"


@pytest.mark.unit
def test_all_flux_controllers_present():
    """Unit test: Verify all Flux controllers are deployed"""
    k8s_client = KubernetesClientWrapper()
    
    for controller_name in FLUX_CONTROLLERS:
        deployment = k8s_client.get_deployment(controller_name, FLUX_NAMESPACE)
        assert deployment is not None, \
            f"Flux controller {controller_name} not found in {FLUX_NAMESPACE}"


@pytest.mark.unit
def test_all_argocd_controllers_present():
    """Unit test: Verify all ArgoCD controllers are deployed"""
    k8s_client = KubernetesClientWrapper()
    
    for controller_name in ARGOCD_CONTROLLERS:
        deployment = k8s_client.get_deployment(controller_name, ARGOCD_NAMESPACE)
        assert deployment is not None, \
            f"ArgoCD controller {controller_name} not found in {ARGOCD_NAMESPACE}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
