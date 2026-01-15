#!/bin/bash

# Setup test environment for GitOps tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Setting up GitOps test environment...${NC}"

# Check if Poetry is installed
if command -v poetry &> /dev/null; then
    echo -e "${GREEN}✓ Poetry is installed${NC}"
    USE_POETRY=true
else
    echo -e "${YELLOW}⚠ Poetry not found, using pip${NC}"
    echo "To install Poetry: curl -sSL https://install.python-poetry.org | python3 -"
    USE_POETRY=false
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python test dependencies...${NC}"
if [ "$USE_POETRY" = true ]; then
    cd "${SCRIPT_DIR}"
    poetry install
else
    pip install -r "${SCRIPT_DIR}/requirements.txt"
fi

# Verify Kubernetes access
echo -e "${YELLOW}Verifying Kubernetes cluster access...${NC}"
if kubectl cluster-info &> /dev/null; then
    echo -e "${GREEN}✓ Kubernetes cluster is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Cannot connect to Kubernetes cluster${NC}"
    echo "Please ensure you have a valid kubeconfig and cluster access"
    exit 1
fi

# Check if GitOps controllers are installed
echo -e "${YELLOW}Checking GitOps controllers...${NC}"

FLUX_INSTALLED=false
ARGOCD_INSTALLED=false

if kubectl get namespace flux-system &> /dev/null; then
    echo -e "${GREEN}✓ Flux namespace exists${NC}"
    FLUX_INSTALLED=true
else
    echo -e "${YELLOW}⚠ Flux namespace not found${NC}"
fi

if kubectl get namespace argocd &> /dev/null; then
    echo -e "${GREEN}✓ ArgoCD namespace exists${NC}"
    ARGOCD_INSTALLED=true
else
    echo -e "${YELLOW}⚠ ArgoCD namespace not found${NC}"
fi

if [ "$FLUX_INSTALLED" = false ] || [ "$ARGOCD_INSTALLED" = false ]; then
    echo ""
    echo -e "${YELLOW}GitOps controllers are not fully installed.${NC}"
    echo "To install them, run:"
    echo "  cd ../scripts && ./install-gitops-controllers.sh"
    echo ""
    echo "Tests will fail without GitOps controllers installed."
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Test environment is ready!${NC}"
echo ""
echo "Run tests with:"
if [ "$USE_POETRY" = true ]; then
    echo "  poetry run pytest                   # Run all tests"
    echo "  poetry run pytest -m property       # Run property-based tests only"
    echo "  poetry run pytest -m unit           # Run unit tests only"
    echo "  poetry run pytest -v                # Verbose output"
else
    echo "  pytest                              # Run all tests"
    echo "  pytest -m property                  # Run property-based tests only"
    echo "  pytest -m unit                      # Run unit tests only"
    echo "  pytest -v                           # Verbose output"
fi
