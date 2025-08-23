# MLOps Platform Makefile

.PHONY: help init plan apply destroy validate test clean

# Default target
help: ## Show this help message
	@echo "MLOps Platform Management"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Infrastructure commands
init: ## Initialize Terraform
	cd infra/environments/dev && terraform init

plan: ## Plan Terraform changes
	cd infra/environments/dev && terraform plan

apply: ## Apply Terraform changes
	cd infra/environments/dev && terraform apply

destroy: ## Destroy infrastructure
	cd infra/environments/dev && terraform destroy

# Validation commands
validate: ## Validate all configurations
	@echo "Validating Terraform..."
	terraform fmt -check -recursive infra/
	cd infra/environments/dev && terraform validate
	@echo "Validating Kubernetes manifests..."
	find k8s/ -name "*.yaml" -o -name "*.yml" | xargs -I {} kubectl --dry-run=client apply -f {}
	@echo "Validating workflows..."
	find workflows/templates/ -name "*.yaml" -o -name "*.yml" | xargs -I {} argo lint {}

# Testing commands
test: ## Run all tests
	@echo "Running infrastructure tests..."
	cd infra/environments/dev && terraform plan -detailed-exitcode
	@echo "Running application tests..."
	cd apps/trainer && python -m pytest tests/ -v
	cd apps/inference && python -m pytest tests/ -v

# Development commands
dev-setup: ## Set up development environment
	@echo "Setting up development environment..."
	cp infra/environments/dev/terraform.tfvars.example infra/environments/dev/terraform.tfvars
	@echo "Please edit infra/environments/dev/terraform.tfvars with your configuration"

build-images: ## Build Docker images
	cd apps/trainer && docker build -t mlops-trainer:latest .
	cd apps/inference && docker build -t mlops-inference:latest .

# Kubernetes commands
k8s-deploy: ## Deploy Kubernetes applications
	kubectl apply -k k8s/base/
	kubectl apply -k k8s/overlays/dev/

k8s-status: ## Check Kubernetes deployment status
	kubectl get pods -A
	kubectl get svc -A

# Cleanup commands
clean: ## Clean temporary files
	find . -name "*.tfstate.backup" -delete
	find . -name ".terraform.lock.hcl" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	terraform-docs markdown table infra/modules/vpc/ > infra/modules/vpc/README.md
	terraform-docs markdown table infra/modules/eks/ > infra/modules/eks/README.md
	terraform-docs markdown table infra/modules/s3/ > infra/modules/s3/README.md