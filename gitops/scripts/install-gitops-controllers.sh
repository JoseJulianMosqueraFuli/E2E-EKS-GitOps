#!/bin/bash

set -euo pipefail

# GitOps Controllers Installation Script
# This script installs ArgoCD and Flux v2 controllers for the MLOps platform

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITOPS_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if helm is available
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Install Flux v2 controllers
install_flux() {
    log_info "Installing Flux v2 controllers..."
    
    # Apply Flux system namespace and controllers
    kubectl apply -k "${GITOPS_DIR}/infrastructure/controllers/flux-system"
    
    # Wait for Flux controllers to be ready
    log_info "Waiting for Flux controllers to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/source-controller -n flux-system
    kubectl wait --for=condition=available --timeout=300s deployment/kustomize-controller -n flux-system
    kubectl wait --for=condition=available --timeout=300s deployment/helm-controller -n flux-system
    kubectl wait --for=condition=available --timeout=300s deployment/notification-controller -n flux-system
    
    log_success "Flux v2 controllers installed successfully"
}

# Install ArgoCD
install_argocd() {
    log_info "Installing ArgoCD..."
    
    # Apply ArgoCD namespace and controllers
    kubectl apply -k "${GITOPS_DIR}/infrastructure/controllers/argocd"
    
    # Wait for ArgoCD controllers to be ready
    log_info "Waiting for ArgoCD controllers to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-repo-server -n argocd
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-application-controller -n argocd
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-dex-server -n argocd
    
    log_success "ArgoCD installed successfully"
}

# Configure initial Git repositories
configure_repositories() {
    log_info "Configuring initial Git repositories..."
    
    # Create GitRepository for infrastructure
    cat <<EOF | kubectl apply -f -
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: infrastructure-repo
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps
  ref:
    branch: main
  secretRef:
    name: flux-system
EOF

    # Create Kustomization for infrastructure
    cat <<EOF | kubectl apply -f -
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 10m
  timeout: 5m
  sourceRef:
    kind: GitRepository
    name: infrastructure-repo
  path: "./gitops/infrastructure"
  prune: true
  wait: true
EOF
    
    log_success "Git repositories configured"
}

# Get ArgoCD admin password
get_argocd_password() {
    log_info "Retrieving ArgoCD admin password..."
    
    # Wait for the secret to be created
    kubectl wait --for=condition=complete --timeout=60s job/argocd-server -n argocd 2>/dev/null || true
    
    # Get the password
    ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
    
    log_success "ArgoCD admin password: ${ARGOCD_PASSWORD}"
    log_info "You can access ArgoCD UI at: http://localhost:8080 (after port-forward)"
    log_info "Run: kubectl port-forward svc/argocd-server -n argocd 8080:443"
}

# Verify installation
verify_installation() {
    log_info "Verifying GitOps controllers installation..."
    
    # Check Flux controllers
    log_info "Checking Flux controllers status..."
    kubectl get pods -n flux-system
    
    # Check ArgoCD controllers
    log_info "Checking ArgoCD controllers status..."
    kubectl get pods -n argocd
    
    # Check if all controllers are ready
    FLUX_READY=$(kubectl get deployment -n flux-system -o jsonpath='{.items[*].status.readyReplicas}' | tr ' ' '+' | bc)
    FLUX_DESIRED=$(kubectl get deployment -n flux-system -o jsonpath='{.items[*].status.replicas}' | tr ' ' '+' | bc)
    
    ARGOCD_READY=$(kubectl get deployment -n argocd -o jsonpath='{.items[*].status.readyReplicas}' | tr ' ' '+' | bc)
    ARGOCD_DESIRED=$(kubectl get deployment -n argocd -o jsonpath='{.items[*].status.replicas}' | tr ' ' '+' | bc)
    
    if [[ "$FLUX_READY" -eq "$FLUX_DESIRED" ]] && [[ "$ARGOCD_READY" -eq "$ARGOCD_DESIRED" ]]; then
        log_success "All GitOps controllers are ready and healthy"
        return 0
    else
        log_error "Some controllers are not ready"
        return 1
    fi
}

# Main installation function
main() {
    log_info "Starting GitOps controllers installation..."
    
    check_prerequisites
    install_flux
    install_argocd
    configure_repositories
    
    # Wait a bit for everything to settle
    sleep 30
    
    get_argocd_password
    verify_installation
    
    log_success "GitOps infrastructure foundation setup completed!"
    log_info "Next steps:"
    log_info "1. Configure your Git repositories"
    log_info "2. Set up ArgoCD applications"
    log_info "3. Deploy MLOps applications"
}

# Handle script arguments
case "${1:-install}" in
    install)
        main
        ;;
    verify)
        verify_installation
        ;;
    password)
        get_argocd_password
        ;;
    *)
        echo "Usage: $0 [install|verify|password]"
        exit 1
        ;;
esac