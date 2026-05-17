#!/bin/bash

# MLOps Stack Setup Script
# Configurable deployment of MLOps tools

set -e

# Configuration
ENVIRONMENT=${ENVIRONMENT:-"dev"}
CI_PROVIDER=${CI_PROVIDER:-"github"}
MLOPS_TOOLS=${MLOPS_TOOLS:-"mlflow,kubeflow,kserve,monitoring"}
AWS_REGION=${AWS_REGION:-"us-west-2"}
CLUSTER_NAME=${CLUSTER_NAME:-"mlops-${ENVIRONMENT}-cluster"}

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
        "gitlab")
            log_info "GitLab CI configuration already present"
            ;;
        "circleci")
            log_info "CircleCI configuration already present"
            ;;
        "jenkins")
            log_info "Jenkins configuration available in ci-cd/providers/jenkins/"
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

# Deploy KServe via Helm
deploy_kserve() {
    log_info "Deploying KServe via Helm..."

    helm upgrade --install kserve \
      gitops/charts/kserve/ \
      --namespace kserve --create-namespace \
      --wait --timeout 600s

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
    
    # Deploy monitoring stack
    kubectl apply -f k8s/mlops-stack/monitoring/prometheus-stack.yaml
    
    # Wait for deployments
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring
    kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring
    
    log_success "Monitoring stack deployed successfully"
    
    # Get Grafana URL
    log_info "Grafana password managed by External Secrets Operator"
    log_info "See k8s/mlops-stack/secrets/ for configuration"
    log_info "Access Grafana via port-forward: kubectl port-forward svc/grafana 3000:3000 -n monitoring"
}

# Setup IRSA roles for MLOps tools
setup_irsa_roles() {
    log_info "Setting up IRSA roles for MLOps tools..."
    
    # Get OIDC issuer URL
    OIDC_ISSUER=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} --query "cluster.identity.oidc.issuer" --output text)
    OIDC_ID=$(echo $OIDC_ISSUER | cut -d '/' -f 5)
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Create trust policy inline (avoid predictable temp files)
    create_trust_policy() {
        local ns=$1
        local sa=$2
        cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_ISSUER#https://}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_ISSUER#https://}:sub": "system:serviceaccount:${ns}:${sa}",
          "${OIDC_ISSUER#https://}:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF
    }

    # Create MLflow role with least-privilege S3 policy (specific buckets should be attached separately)
    mlflow_trust=$(create_trust_policy "mlflow" "mlflow-sa")
    aws iam create-role --role-name mlops-${ENVIRONMENT}-mlflow-role --assume-role-policy-document "$mlflow_trust" 2>/dev/null || true
    # NOTE: Attach a custom policy scoped to mlops S3 buckets instead of AmazonS3FullAccess
    log_warning "mlops-${ENVIRONMENT}-mlflow-role created. Attach a least-privilege S3 policy manually."

    # Create KServe role (replaces legacy Seldon)
    kserve_trust=$(create_trust_policy "kserve" "kserve-sa")
    aws iam create-role --role-name mlops-${ENVIRONMENT}-kserve-role --assume-role-policy-document "$kserve_trust" 2>/dev/null || true
    log_warning "mlops-${ENVIRONMENT}-kserve-role created. Attach a least-privilege S3 read policy manually."

    log_success "IRSA roles configured"
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
    setup_irsa_roles
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
        echo "  CI_PROVIDER     - CI/CD provider (github|gitlab|circleci|jenkins)"
        echo "  MLOPS_TOOLS     - Comma-separated tools (mlflow,kubeflow,kserve,monitoring)"
        echo "  AWS_REGION      - AWS region (default: us-west-2)"
        echo "  CLUSTER_NAME    - EKS cluster name"
        echo ""
        echo "Examples:"
        echo "  $0 install"
        echo "  MLOPS_TOOLS=mlflow,monitoring $0 install"
        echo "  CI_PROVIDER=gitlab $0 install"
        exit 1
        ;;
esac