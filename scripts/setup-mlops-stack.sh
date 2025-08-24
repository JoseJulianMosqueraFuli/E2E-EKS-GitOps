#!/bin/bash

# MLOps Stack Setup Script
# Configurable deployment of MLOps tools

set -e

# Configuration
ENVIRONMENT=${ENVIRONMENT:-"dev"}
CI_PROVIDER=${CI_PROVIDER:-"github"}
MLOPS_TOOLS=${MLOPS_TOOLS:-"mlflow,kubeflow,seldon,monitoring"}
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
    
    # Deploy MLflow stack
    kubectl apply -f k8s/mlops-stack/mlflow/deployment.yaml
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=300s deployment/mlflow-server -n mlflow
    
    log_success "MLflow deployed successfully"
    
    # Get MLflow URL
    MLFLOW_URL=$(kubectl get ingress mlflow-ingress -n mlflow -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "localhost:5000")
    log_info "MLflow UI available at: http://${MLFLOW_URL}"
}

# Deploy Kubeflow Pipelines
deploy_kubeflow() {
    log_info "Deploying Kubeflow Pipelines..."
    
    # Create namespace
    kubectl create namespace kubeflow --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy using kustomize
    kubectl apply -k k8s/mlops-stack/kubeflow/
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=600s deployment/ml-pipeline -n kubeflow || true
    
    log_success "Kubeflow Pipelines deployed successfully"
}

# Deploy Seldon Core
deploy_seldon() {
    log_info "Deploying Seldon Core..."
    
    # Install Seldon Core CRDs first
    kubectl apply -f https://github.com/SeldonIO/seldon-core/releases/download/v1.17.1/seldon-core-crd.yaml
    
    # Deploy Seldon Core
    kubectl apply -f k8s/mlops-stack/seldon/seldon-core.yaml
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=300s deployment/seldon-controller-manager -n seldon-system
    
    log_success "Seldon Core deployed successfully"
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
    log_info "Grafana admin password: admin123 (change in production)"
    log_info "Access Grafana via port-forward: kubectl port-forward svc/grafana 3000:3000 -n monitoring"
}

# Setup IRSA roles for MLOps tools
setup_irsa_roles() {
    log_info "Setting up IRSA roles for MLOps tools..."
    
    # Get OIDC issuer URL
    OIDC_ISSUER=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} --query "cluster.identity.oidc.issuer" --output text)
    OIDC_ID=$(echo $OIDC_ISSUER | cut -d '/' -f 5)
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Create trust policy template
    cat > /tmp/trust-policy.json << EOF
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
          "${OIDC_ISSUER#https://}:sub": "system:serviceaccount:NAMESPACE:SERVICE_ACCOUNT",
          "${OIDC_ISSUER#https://}:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF

    # Create MLflow role
    sed "s/NAMESPACE/mlflow/g; s/SERVICE_ACCOUNT/mlflow-sa/g" /tmp/trust-policy.json > /tmp/mlflow-trust-policy.json
    aws iam create-role --role-name mlops-${ENVIRONMENT}-mlflow-role --assume-role-policy-document file:///tmp/mlflow-trust-policy.json || true
    aws iam attach-role-policy --role-name mlops-${ENVIRONMENT}-mlflow-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess || true
    
    # Create Seldon role
    sed "s/NAMESPACE/seldon-system/g; s/SERVICE_ACCOUNT/seldon-sa/g" /tmp/trust-policy.json > /tmp/seldon-trust-policy.json
    aws iam create-role --role-name mlops-${ENVIRONMENT}-seldon-role --assume-role-policy-document file:///tmp/seldon-trust-policy.json || true
    aws iam attach-role-policy --role-name mlops-${ENVIRONMENT}-seldon-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess || true
    
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
            "seldon")
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
    rm -f /tmp/*-trust-policy.json
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
        kubectl delete namespace mlflow kubeflow seldon-system monitoring --ignore-not-found=true
        log_success "MLOps stack uninstalled"
        ;;
    "status")
        log_info "Checking MLOps stack status..."
        kubectl get pods -n mlflow -n kubeflow -n seldon-system -n monitoring
        ;;
    *)
        echo "Usage: $0 {install|uninstall|status}"
        echo ""
        echo "Environment variables:"
        echo "  ENVIRONMENT     - Target environment (default: dev)"
        echo "  CI_PROVIDER     - CI/CD provider (github|gitlab|circleci|jenkins)"
        echo "  MLOPS_TOOLS     - Comma-separated tools (mlflow,kubeflow,seldon,monitoring)"
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