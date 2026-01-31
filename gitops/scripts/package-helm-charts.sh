#!/bin/bash
# Script to package Helm charts and update repository index
# Usage: ./package-helm-charts.sh [chart-name]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHARTS_DIR="${SCRIPT_DIR}/../charts"
PACKAGES_DIR="${CHARTS_DIR}/packages"
REPO_URL="${HELM_REPO_URL:-https://org.github.io/mlops-helm-charts}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if helm is installed
if ! command -v helm &> /dev/null; then
    log_error "Helm is not installed. Please install Helm first."
    exit 1
fi

# Create packages directory if it doesn't exist
mkdir -p "${PACKAGES_DIR}"

# Function to package a single chart
package_chart() {
    local chart_name=$1
    local chart_path="${CHARTS_DIR}/${chart_name}"
    
    if [ ! -d "${chart_path}" ]; then
        log_error "Chart directory not found: ${chart_path}"
        return 1
    fi
    
    log_info "Packaging chart: ${chart_name}"
    
    # Lint the chart first
    log_info "Linting ${chart_name}..."
    if ! helm lint "${chart_path}"; then
        log_warn "Lint warnings for ${chart_name}, continuing..."
    fi
    
    # Update dependencies
    log_info "Updating dependencies for ${chart_name}..."
    helm dependency update "${chart_path}" 2>/dev/null || true
    
    # Package the chart
    log_info "Creating package for ${chart_name}..."
    helm package "${chart_path}" --destination "${PACKAGES_DIR}"
    
    log_info "Successfully packaged ${chart_name}"
}

# Function to update repository index
update_index() {
    log_info "Updating Helm repository index..."
    helm repo index "${PACKAGES_DIR}" --url "${REPO_URL}"
    
    # Copy index to charts root for GitHub Pages
    cp "${PACKAGES_DIR}/index.yaml" "${CHARTS_DIR}/index.yaml"
    
    log_info "Repository index updated"
}

# Main execution
main() {
    local chart_name=$1
    
    log_info "Starting Helm chart packaging..."
    log_info "Charts directory: ${CHARTS_DIR}"
    log_info "Packages directory: ${PACKAGES_DIR}"
    log_info "Repository URL: ${REPO_URL}"
    
    if [ -n "${chart_name}" ]; then
        # Package specific chart
        package_chart "${chart_name}"
    else
        # Package all charts
        log_info "Packaging all charts..."
        
        for chart in mlflow kserve kubeflow-pipelines monitoring-stack; do
            if [ -d "${CHARTS_DIR}/${chart}" ]; then
                package_chart "${chart}"
            else
                log_warn "Chart directory not found: ${chart}"
            fi
        done
    fi
    
    # Update repository index
    update_index
    
    log_info "Helm chart packaging complete!"
    log_info "Packages available in: ${PACKAGES_DIR}"
    
    # List packaged charts
    echo ""
    log_info "Packaged charts:"
    ls -la "${PACKAGES_DIR}"/*.tgz 2>/dev/null || log_warn "No packages found"
}

# Run main function
main "$@"
