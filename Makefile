# Makefile for MLOps Platform

.PHONY: help init plan apply destroy test clean mlops-install mlops-uninstall mlops-status

# Default environment
ENV ?= dev
REGION ?= us-west-2
CI_PROVIDER ?= github
MLOPS_TOOLS ?= mlflow,kubeflow,seldon,monitoring

help: ## Show this help message
	@echo 'Usage: make [target] [ENV=environment]'
	@echo ''
	@echo 'Infrastructure Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(init|plan|apply|destroy|test|clean)"
	@echo ''
	@echo 'MLOps Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "mlops-"
	@echo ''
	@echo 'CI/CD Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(setup-|validate-)"
	@echo ''
	@echo 'Variables:'
	@echo '  ENV=$(ENV)              Target environment'
	@echo '  CI_PROVIDER=$(CI_PROVIDER)      CI/CD provider (github|gitlab|circleci|jenkins)'
	@echo '  MLOPS_TOOLS=$(MLOPS_TOOLS)  MLOps tools to deploy'

# Infrastructure Targets
init: ## Initialize Terraform
	cd infra/environments/$(ENV) && terraform init

plan: ## Plan Terraform changes
	cd infra/environments/$(ENV) && terraform plan

apply: ## Apply Terraform changes
	cd infra/environments/$(ENV) && terraform apply

destroy: ## Destroy Terraform resources
	cd infra/environments/$(ENV) && terraform destroy

test: ## Run infrastructure tests
	@echo "Running Terraform tests..."
	cd infra/modules/vpc/test && go test -v -timeout 30m
	cd infra/modules/eks/test && go test -v -timeout 45m
	cd infra/modules/s3/test && go test -v -timeout 20m
	cd infra/modules/ecr/test && go test -v -timeout 15m
	cd infra/modules/glue/test && go test -v -timeout 25m

test-unit: ## Run unit tests only (faster)
	@echo "Running unit tests..."
	cd ml-platform && python -m pytest tests/unit/ -v

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	cd ml-platform && python -m pytest tests/integration/ -v

clean: ## Clean temporary files
	find . -name "*.tfplan" -delete
	find . -name ".terraform" -type d -exec rm -rf {} +
	find . -name "terraform.tfstate*" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

# MLOps Stack Targets
mlops-install: ## Install MLOps stack
	@echo "Installing MLOps stack with tools: $(MLOPS_TOOLS)"
	ENVIRONMENT=$(ENV) CI_PROVIDER=$(CI_PROVIDER) MLOPS_TOOLS=$(MLOPS_TOOLS) ./scripts/setup-mlops-stack.sh install

mlops-uninstall: ## Uninstall MLOps stack
	@echo "Uninstalling MLOps stack..."
	./scripts/setup-mlops-stack.sh uninstall

mlops-status: ## Check MLOps stack status
	@echo "Checking MLOps stack status..."
	./scripts/setup-mlops-stack.sh status

mlops-mlflow-only: ## Install only MLflow
	MLOPS_TOOLS=mlflow $(MAKE) mlops-install

mlops-monitoring-only: ## Install only monitoring stack
	MLOPS_TOOLS=monitoring $(MAKE) mlops-install

mlops-core: ## Install core MLOps tools (MLflow + Monitoring)
	MLOPS_TOOLS=mlflow,monitoring $(MAKE) mlops-install

mlops-full: ## Install full MLOps stack
	MLOPS_TOOLS=mlflow,kubeflow,seldon,monitoring $(MAKE) mlops-install

# CI/CD Setup Targets
setup-github: ## Setup GitHub Actions
	@echo "GitHub Actions configuration is already present in .github/workflows/"
	@echo "Configure secrets in GitHub repository settings:"
	@echo "  - AWS_ACCESS_KEY_ID"
	@echo "  - AWS_SECRET_ACCESS_KEY"
	@echo "  - KUBE_CONFIG_DATA"

setup-gitlab: ## Setup GitLab CI
	@echo "GitLab CI configuration is already present in .gitlab-ci.yml"
	@echo "Configure variables in GitLab project settings:"
	@echo "  - AWS_ACCESS_KEY_ID"
	@echo "  - AWS_SECRET_ACCESS_KEY"
	@echo "  - KUBE_CONFIG"

setup-circleci: ## Setup CircleCI
	@echo "CircleCI configuration is already present in .circleci/config.yml"
	@echo "Configure environment variables in CircleCI project settings:"
	@echo "  - AWS_ACCESS_KEY_ID"
	@echo "  - AWS_SECRET_ACCESS_KEY"

setup-jenkins: ## Setup Jenkins
	@echo "Jenkins configuration is available in ci-cd/providers/jenkins/Jenkinsfile"
	@echo "Configure Jenkins credentials:"
	@echo "  - aws-credentials (AWS Access Key)"
	@echo "  - kubeconfig (Kubernetes config)"

# Validation Targets
validate-terraform: ## Validate Terraform configuration
	@echo "Validating Terraform configuration..."
	cd infra/environments/$(ENV) && terraform init -backend=false && terraform validate

validate-kubernetes: ## Validate Kubernetes manifests
	@echo "Validating Kubernetes manifests..."
	kubectl apply --dry-run=client -f k8s/mlops-stack/mlflow/deployment.yaml
	kubectl apply --dry-run=client -f k8s/mlops-stack/seldon/seldon-core.yaml
	kubectl apply --dry-run=client -f k8s/mlops-stack/monitoring/prometheus-stack.yaml

validate-python: ## Validate Python code
	@echo "Validating Python code..."
	cd ml-platform && python -m flake8 src/ tests/
	cd ml-platform && python -m black --check src/ tests/
	cd ml-platform && python -m isort --check-only src/ tests/

validate-all: validate-terraform validate-kubernetes validate-python ## Validate all configurations

# Development Targets
dev-setup: ## Setup development environment
	@echo "Setting up development environment..."
	pip install -r ml-platform/requirements.txt
	pip install -r ml-platform/requirements-dev.txt
	pre-commit install

dev-format: ## Format code
	cd ml-platform && python -m black src/ tests/
	cd ml-platform && python -m isort src/ tests/

dev-lint: ## Lint code
	cd ml-platform && python -m flake8 src/ tests/
	cd ml-platform && python -m mypy src/

# Quick Start Targets
quickstart-dev: ## Quick start for development environment
	$(MAKE) init ENV=dev
	$(MAKE) apply ENV=dev
	$(MAKE) mlops-core ENV=dev

quickstart-prod: ## Quick start for production environment
	$(MAKE) init ENV=prod
	$(MAKE) plan ENV=prod
	@echo "Review the plan above, then run: make apply ENV=prod"
	@echo "After infrastructure is ready, run: make mlops-full ENV=prod"

# Monitoring Targets
logs-mlflow: ## View MLflow logs
	kubectl logs -f deployment/mlflow-server -n mlflow

logs-seldon: ## View Seldon logs
	kubectl logs -f deployment/seldon-controller-manager -n seldon-system

logs-kubeflow: ## View Kubeflow logs
	kubectl logs -f deployment/ml-pipeline -n kubeflow

port-forward-mlflow: ## Port forward MLflow UI
	@echo "MLflow UI will be available at http://localhost:5000"
	kubectl port-forward svc/mlflow-server 5000:5000 -n mlflow

port-forward-grafana: ## Port forward Grafana UI
	@echo "Grafana UI will be available at http://localhost:3000 (admin/admin123)"
	kubectl port-forward svc/grafana 3000:3000 -n monitoring

port-forward-kubeflow: ## Port forward Kubeflow UI
	@echo "Kubeflow UI will be available at http://localhost:8080"
	kubectl port-forward svc/ml-pipeline-ui 8080:80 -n kubeflow

# Backup and Restore
backup-mlflow: ## Backup MLflow data
	@echo "Creating MLflow backup..."
	kubectl exec -n mlflow deployment/postgres -- pg_dump -U mlflow mlflow > mlflow-backup-$(shell date +%Y%m%d-%H%M%S).sql

restore-mlflow: ## Restore MLflow data (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Please specify BACKUP_FILE=path/to/backup.sql"; exit 1; fi
	@echo "Restoring MLflow from $(BACKUP_FILE)..."
	kubectl exec -i -n mlflow deployment/postgres -- psql -U mlflow mlflow < $(BACKUP_FILE)

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	@echo "Infrastructure documentation available in docs/"
	@echo "MLOps recommendations available in docs/mlops-enterprise-recommendations.md"