#!/usr/bin/env bash
# validate-gitops.sh - Comprehensive GitOps validation script
# Validates controllers, applications, drift detection, and reconciliation
#
# Usage: ./validate-gitops.sh [environment]
#   environment: dev (default), staging, production

set -euo pipefail

ENVIRONMENT="${1:-dev}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0
WARN=0

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((PASS++)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAIL++)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARN++)); }
log_info() { echo -e "[INFO] $1"; }

echo "============================================="
echo " GitOps Validation Report"
echo " Environment: ${ENVIRONMENT}"
echo " Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
log_info "Checking prerequisites..."

if ! command -v kubectl &>/dev/null; then
    log_fail "kubectl not found in PATH"
    exit 1
fi
log_pass "kubectl is available"

if ! kubectl cluster-info &>/dev/null 2>&1; then
    log_fail "Cannot connect to Kubernetes cluster"
    exit 1
fi
log_pass "Connected to Kubernetes cluster"

# ---------------------------------------------------------------------------
# 2. Flux Controllers
# ---------------------------------------------------------------------------
echo ""
echo "--- Flux Controllers ---"

FLUX_NS="flux-system"
FLUX_CONTROLLERS=("source-controller" "kustomize-controller" "helm-controller" "notification-controller")

for controller in "${FLUX_CONTROLLERS[@]}"; do
    if kubectl get deployment "${controller}" -n "${FLUX_NS}" &>/dev/null 2>&1; then
        ready=$(kubectl get deployment "${controller}" -n "${FLUX_NS}" -o jsonpath='{.status.readyReplicas}')
        desired=$(kubectl get deployment "${controller}" -n "${FLUX_NS}" -o jsonpath='{.spec.replicas}')
        if [[ "${ready}" == "${desired}" ]]; then
            log_pass "Flux ${controller}: ${ready}/${desired} ready"
        else
            log_fail "Flux ${controller}: ${ready}/${desired} ready"
        fi
    else
        log_fail "Flux ${controller}: deployment not found"
    fi
done

# Check Flux GitRepository
if kubectl get gitrepository -n "${FLUX_NS}" &>/dev/null 2>&1; then
    repos=$(kubectl get gitrepository -n "${FLUX_NS}" -o name | wc -l)
    log_pass "Flux GitRepositories: ${repos} configured"
else
    log_warn "No Flux GitRepositories found"
fi

# Check Flux Kustomizations
if kubectl get kustomizations -n "${FLUX_NS}" &>/dev/null 2>&1; then
    kustomizations=$(kubectl get kustomizations -n "${FLUX_NS}" -o name | wc -l)
    log_pass "Flux Kustomizations: ${kustomizations} configured"

    # Check reconciliation status
    for kust in $(kubectl get kustomizations -n "${FLUX_NS}" -o jsonpath='{.items[*].metadata.name}'); do
        ready=$(kubectl get kustomization "${kust}" -n "${FLUX_NS}" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
        if [[ "${ready}" == "True" ]]; then
            log_pass "Flux Kustomization ${kust}: Ready"
        else
            log_warn "Flux Kustomization ${kust}: status=${ready}"
        fi
    done
else
    log_warn "No Flux Kustomizations found"
fi

# ---------------------------------------------------------------------------
# 3. ArgoCD Controllers
# ---------------------------------------------------------------------------
echo ""
echo "--- ArgoCD Controllers ---"

ARGO_NS="argocd"
ARGO_CONTROLLERS=("argocd-server" "argocd-repo-server" "argocd-application-controller" "argocd-dex-server" "argocd-redis")

for controller in "${ARGO_CONTROLLERS[@]}"; do
    if kubectl get deployment "${controller}" -n "${ARGO_NS}" &>/dev/null 2>&1; then
        ready=$(kubectl get deployment "${controller}" -n "${ARGO_NS}" -o jsonpath='{.status.readyReplicas}')
        desired=$(kubectl get deployment "${controller}" -n "${ARGO_NS}" -o jsonpath='{.spec.replicas}')
        if [[ "${ready}" == "${desired}" ]]; then
            log_pass "ArgoCD ${controller}: ${ready}/${desired} ready"
        else
            log_fail "ArgoCD ${controller}: ${ready}/${desired} ready"
        fi
    else
        log_fail "ArgoCD ${controller}: deployment not found"
    fi
done

# ---------------------------------------------------------------------------
# 4. ArgoCD Applications
# ---------------------------------------------------------------------------
echo ""
echo "--- ArgoCD Applications ---"

APPS=("mlflow" "kubeflow" "kserve" "monitoring")

for app in "${APPS[@]}"; do
    app_name="${app}-${ENVIRONMENT}"
    if kubectl get application "${app_name}" -n "${ARGO_NS}" &>/dev/null 2>&1; then
        sync_status=$(kubectl get application "${app_name}" -n "${ARGO_NS}" -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
        health_status=$(kubectl get application "${app_name}" -n "${ARGO_NS}" -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")

        if [[ "${sync_status}" == "Synced" ]]; then
            log_pass "ArgoCD ${app_name}: Synced"
        else
            log_fail "ArgoCD ${app_name}: sync=${sync_status}"
        fi

        if [[ "${health_status}" == "Healthy" ]]; then
            log_pass "ArgoCD ${app_name}: Healthy"
        else
            log_warn "ArgoCD ${app_name}: health=${health_status}"
        fi
    else
        log_fail "ArgoCD ${app_name}: application not found"
    fi
done

# ---------------------------------------------------------------------------
# 5. MLOps Workloads
# ---------------------------------------------------------------------------
echo ""
echo "--- MLOps Workloads ---"

declare -A NAMESPACES=(
    ["mlflow"]="mlflow-server"
    ["kubeflow"]="ml-pipeline"
    ["kserve"]="kserve-controller-manager"
    ["monitoring"]="prometheus"
)

for ns in "${!NAMESPACES[@]}"; do
    workload="${NAMESPACES[$ns]}"
    if kubectl get deployment "${workload}" -n "${ns}" &>/dev/null 2>&1; then
        ready=$(kubectl get deployment "${workload}" -n "${ns}" -o jsonpath='{.status.readyReplicas}')
        desired=$(kubectl get deployment "${workload}" -n "${ns}" -o jsonpath='{.spec.replicas}')
        if [[ "${ready}" == "${desired}" ]]; then
            log_pass "${ns}/${workload}: ${ready}/${desired} ready"
        else
            log_warn "${ns}/${workload}: ${ready}/${desired} ready"
        fi
    else
        log_warn "${ns}/${workload}: deployment not found (may not be deployed yet)"
    fi
done

# ---------------------------------------------------------------------------
# 6. Drift Detection Test
# ---------------------------------------------------------------------------
echo ""
echo "--- Drift Detection ---"

log_info "Testing drift detection by temporarily modifying a ConfigMap..."

TEST_NS="mlflow"
TEST_CM="mlflow-config"

if kubectl get configmap "${TEST_CM}" -n "${TEST_NS}" &>/dev/null 2>&1; then
    # Get current value
    original=$(kubectl get configmap "${TEST_CM}" -n "${TEST_NS}" -o jsonpath='{.data.log_level}' 2>/dev/null || echo "")

    if [[ -n "${original}" ]]; then
        # Apply drift
        kubectl patch configmap "${TEST_CM}" -n "${TEST_NS}" -p "{\"data\":{\"log_level\":\"drift-test\"}}" &>/dev/null
        log_warn "Applied drift to ${TEST_NS}/${TEST_CM}"

        log_info "Waiting 60s for Flux/ArgoCD to detect and reconcile..."
        sleep 60

        # Check if reconciled
        current=$(kubectl get configmap "${TEST_CM}" -n "${TEST_NS}" -o jsonpath='{.data.log_level}' 2>/dev/null || echo "")
        if [[ "${current}" != "drift-test" ]]; then
            log_pass "Drift detected and reconciled automatically"
        else
            log_fail "Drift NOT reconciled after 60s"
        fi

        # Restore original
        kubectl patch configmap "${TEST_CM}" -n "${TEST_NS}" -p "{\"data\":{\"log_level\":\"${original}\"}}" &>/dev/null
    else
        log_warn "ConfigMap ${TEST_NS}/${TEST_CM} has no log_level key, skipping drift test"
    fi
else
    log_warn "ConfigMap ${TEST_NS}/${TEST_CM} not found, skipping drift test"
fi

# ---------------------------------------------------------------------------
# 7. Infrastructure Addons
# ---------------------------------------------------------------------------
echo ""
echo "--- Infrastructure Addons ---"

ADDONS=(
    "kube-system/aws-load-balancer-controller"
    "kube-system/ebs-csi-controller"
    "kube-system/cluster-autoscaler"
)

for addon in "${ADDONS[@]}"; do
    ns="${addon%%/*}"
    name="${addon##*/}"
    if kubectl get deployment "${name}" -n "${ns}" &>/dev/null 2>&1; then
        ready=$(kubectl get deployment "${name}" -n "${ns}" -o jsonpath='{.status.readyReplicas}')
        desired=$(kubectl get deployment "${name}" -n "${ns}" -o jsonpath='{.spec.replicas}')
        if [[ "${ready}" == "${desired}" ]]; then
            log_pass "Addon ${name}: ${ready}/${desired} ready"
        else
            log_warn "Addon ${name}: ${ready}/${desired} ready"
        fi
    else
        log_warn "Addon ${name}: deployment not found"
    fi
done

# ---------------------------------------------------------------------------
# 8. Networking
# ---------------------------------------------------------------------------
echo ""
echo "--- Networking ---"

if kubectl get deployment istiod -n istio-system &>/dev/null 2>&1; then
    log_pass "Istio istiod: running"
else
    log_warn "Istio istiod: not found"
fi

if kubectl get ingressclass alb &>/dev/null 2>&1; then
    log_pass "ALB IngressClass: configured"
else
    log_warn "ALB IngressClass: not found"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo " Validation Summary"
echo "============================================="
echo -e " ${GREEN}PASS: ${PASS}${NC}"
echo -e " ${RED}FAIL: ${FAIL}${NC}"
echo -e " ${YELLOW}WARN: ${WARN}${NC}"
echo ""

if [[ ${FAIL} -eq 0 ]]; then
    echo -e " ${GREEN}Overall: HEALTHY${NC}"
    exit 0
else
    echo -e " ${RED}Overall: UNHEALTHY - ${FAIL} failures detected${NC}"
    exit 1
fi
