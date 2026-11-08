#!/bin/bash

# MLOps Stack Setup Script
# Configurable deployment of MLOps tools

set -e

# Configuration
ENVIRONMENT=${ENVIRONMENT:-"dev"}
CI_PROVIDER=${CI_PROVIDER:-"github"}
MLOPS_TOOLS=${MLOPS_TOOLS:-"mlflow,kubeflow,kserve,monitoring"}

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
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed"
        exit 1
    fi
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Setup CI/CD configuration
setup_cicd() {
    log_info "Setting up CI/CD for provider: ${CI_PROVIDER}"
    
    case $CI_PROVIDER in
        "github")
            log_info "GitHub Actions configuration already present"
            ;;
        "gitlab"|"circleci"|"jenkins")
            log_warning "${CI_PROVIDER} is inactive; see ci-cd/future/README.md"
            ;;
        *)
            log_warning "Unknown CI provider: ${CI_PROVIDER}"
            ;;
    esac
}

# Deploy MLflow
deploy_mlflow() {
    log_info "Deploying MLflow..."
    
    # Create namespace
    kubectl create namespace mlflow --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy MLflow stack from GitOps source of truth
    kubectl apply -k k8s/mlops-stack/mlflow/
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=300s deployment/mlflow-server -n mlflow
    
    log_success "MLflow deployed successfully"
    
    # Get MLflow URL
    MLFLOW_URL=$(kubectl get ingress mlflow-ingress -n mlflow -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "localhost:5000")
    log_info "MLflow UI available at: http://${MLFLOW_URL}"
}

# Deploy Kubeflow Pipelines via Helm
deploy_kubeflow() {
    log_info "Deploying Kubeflow Pipelines via Helm..."

    helm upgrade --install kubeflow-pipelines \
      gitops/charts/kubeflow-pipelines/ \
      --namespace kubeflow --create-namespace \
      --wait --timeout 600s

    log_success "Kubeflow Pipelines deployed successfully"
}

# Deploy KServe through Flux HelmReleases (Standard mode)
deploy_kserve() {
    log_info "Deploying cert-manager and KServe through Flux..."

    bash gitops/scripts/install-gitops-controllers.sh flux
    kubectl apply -f gitops/infrastructure/sources/helm-repository.yaml
    kubectl apply -k gitops/infrastructure/addons/cert-manager
    kubectl -n flux-system wait --for=condition=Ready helmrelease/cert-manager --timeout=420s
    kubectl apply -k k8s/mlops-stack/kserve/
    kubectl -n kserve wait --for=condition=Ready helmrelease/kserve-crd helmrelease/kserve --timeout=600s

    log_success "KServe deployed successfully"
}

# Legacy Seldon Core (deprecated, redirects to kserve)
deploy_seldon() {
    log_warning "Seldon Core is deprecated. Use KServe instead."
    deploy_kserve
}

# Deploy Monitoring Stack
deploy_monitoring() {
    log_info "Deploying Monitoring Stack (Prometheus + Grafana)..."
    
    # Deploy monitoring stack from GitOps source of truth
    kubectl apply -k k8s/mlops-stack/monitoring/

    # Wait for workloads
    kubectl rollout status statefulset/prometheus -n monitoring --timeout=300s
    kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring
    
    log_success "Monitoring stack deployed successfully"
    
    # Get Grafana URL
    log_info "Grafana password managed by External Secrets Operator"
    log_info "See gitops/applications/apps/external-secrets/base/ for configuration"
    log_info "Access Grafana via port-forward: kubectl port-forward svc/grafana 3000:3000 -n monitoring"
}

check_workload_roles() {
    log_info "Checking the workload IAM roles managed by Terraform..."

    local missing=0
    for workload in mlflow argo secrets backup; do
        if ! aws iam get-role --role-name "mlops-${ENVIRONMENT}-${workload}" &> /dev/null; then
            log_error "IAM role mlops-${ENVIRONMENT}-${workload} not found; run 'make apply ENV=${ENVIRONMENT}' first"
            missing=1
        fi
    done
    if [ "$missing" -ne 0 ]; then
        exit 1
    fi

    log_success "Workload IAM roles found"
}

# Main deployment function
deploy_tools() {
    IFS=',' read -ra TOOLS <<< "$MLOPS_TOOLS"
    
    for tool in "${TOOLS[@]}"; do
        case $tool in
            "mlflow")
                deploy_mlflow
                ;;
            "kubeflow")
                deploy_kubeflow
                ;;
            "kserve")
                deploy_kserve
                ;;
            "seldon")
                log_warning "'seldon' is deprecated. Use 'kserve' instead."
                deploy_seldon
                ;;
            "monitoring")
                deploy_monitoring
                ;;
            *)
                log_warning "Unknown tool: $tool"
                ;;
        esac
    done
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    : # No temp files with predictable names are created anymore
}

# Main execution
main() {
    log_info "Starting MLOps Stack Setup"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "CI Provider: ${CI_PROVIDER}"
    log_info "Tools to deploy: ${MLOPS_TOOLS}"
    
    check_prerequisites
    setup_cicd
    check_workload_roles
    deploy_tools
    cleanup
    
    log_success "MLOps Stack setup completed!"
    
    # Print access information
    echo ""
    log_info "=== Access Information ==="
    log_info "MLflow: kubectl port-forward svc/mlflow-server 5000:5000 -n mlflow"
    log_info "Grafana: kubectl port-forward svc/grafana 3000:3000 -n monitoring"
    log_info "Kubeflow: kubectl port-forward svc/ml-pipeline-ui 8080:80 -n kubeflow"
    echo ""
}

# Handle script arguments
case "${1:-}" in
    "install")
        main
        ;;
    "uninstall")
        log_info "Uninstalling MLOps stack..."
        kubectl delete namespace mlflow kubeflow kserve monitoring --ignore-not-found=true
        log_success "MLOps stack uninstalled"
        ;;
    "status")
        log_info "Checking MLOps stack status..."
        for ns in mlflow kubeflow kserve monitoring; do
            echo "=== Namespace: $ns ==="
            kubectl get pods -n "$ns" 2>/dev/null || echo "Namespace $ns not found or no pods"
            echo ""
        done
        ;;
    *)
        echo "Usage: $0 {install|uninstall|status}"
        echo ""
        echo "Environment variables:"
        echo "  ENVIRONMENT     - Target environment (default: dev)"
        echo "  CI_PROVIDER     - CI/CD provider (default: github; others are inactive in ci-cd/future/)"
        echo "  MLOPS_TOOLS     - Comma-separated tools (mlflow,kubeflow,kserve,monitoring)"
        echo ""
        echo "Examples:"
        echo "  $0 install"
        echo "  MLOPS_TOOLS=mlflow,monitoring $0 install"
        exit 1
        ;;
esac