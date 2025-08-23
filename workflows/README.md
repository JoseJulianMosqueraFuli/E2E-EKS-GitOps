# Argo Workflows

This directory contains Argo Workflow templates and configurations for ML pipeline orchestration.

## Structure

- `templates/` - Workflow template definitions
- `examples/` - Example workflow executions
- `scripts/` - Workflow management utilities

## Usage

1. Apply workflow templates: `kubectl apply -f templates/`
2. Submit workflow: `argo submit templates/training-pipeline.yaml`
3. Monitor workflows: `argo list`