# Critical Issues Report - E2E-EKS-GitOps

**Report Date**: 2026-06-06
**Project**: E2E MLOps Platform on Amazon EKS
**Reviewer**: OpenCode AI
**Status**: OPEN - Requires immediate action before production deployment

---

## Executive Summary

This document lists all **CRITICAL** and **HIGH** severity findings identified during the comprehensive project review. These issues **must be resolved** before deploying to production or any environment handling sensitive data.

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 4 | Open |
| HIGH | 12 | Open |

---

## CRITICAL Issues

### CRIT-001: Argo Workflows Server - TLS Disabled

- **File**: `k8s/mlops-stack/argo-workflows/server-deployment.yaml`
- **Line**: ~30
- **Issue**: The server starts with `--secure=false`, disabling TLS encryption.
- **Impact**: All traffic to the Argo Workflows server is unencrypted. Credentials, workflow definitions, and artifacts are transmitted in plaintext.
- **CVSS Estimate**: 7.5 (High)
- **Fix**:
  ```yaml
  args:
    - server
    - --secure=true
  ```
- **Owner**: Infrastructure / Platform Team

---

### CRIT-002: Argo Workflows Server - Basic Authentication

- **File**: `k8s/mlops-stack/argo-workflows/server-deployment.yaml`
- **Line**: ~31
- **Issue**: Uses `--auth-mode=server` (basic/local auth) instead of SSO/OAuth.
- **Impact**: Weak authentication mechanism. No MFA, no integration with corporate identity providers. Brute-force risk.
- **CVSS Estimate**: 7.0 (High)
- **Fix**:
  ```yaml
  args:
    - server
    - --auth-mode=sso  # or sso+client
  ```
- **References**: [Argo Workflows SSO Setup](https://argoproj.github.io/argo-workflows/argo-server-sso/)
- **Owner**: Security / Platform Team

---

### CRIT-003: Argo Workflows - Deprecated Docker Executor & Docker Socket Mount

- **Files**:
  - `k8s/mlops-stack/argo-workflows/configmap.yaml` (line ~41)
  - `k8s/mlops-stack/argo-workflows/workflow-templates/model-deployment-template.yaml` (line ~103)
- **Issue**:
  1. `containerRuntimeExecutor: docker` is deprecated since Argo v3.1.
  2. Workflow template mounts `/var/run/docker.sock` via `hostPath`.
- **Impact**: Container escape vulnerability. Any workflow pod can access the host's Docker daemon, effectively gaining root access to the node.
- **CVSS Estimate**: 9.8 (Critical)
- **Fix**:
  1. In `configmap.yaml`:
     ```yaml
     containerRuntimeExecutor: emissary
     ```
  2. Remove all `hostPath` mounts of `/var/run/docker.sock` from workflow templates.
  3. Use Kaniko or BuildKit for image builds if needed.
- **Owner**: Infrastructure / DevSecOps Team

---

### CRIT-004: ArgoCD AppProject Excessively Permissive

- **File**: `gitops/applications/projects/mlops-core.yaml`
- **Issue**: The `mlops-core` AppProject allows:
  - `sourceRepos: "*"` (any Git repository)
  - `destinations: namespace: "*"` (any namespace)
  - `clusterResourceWhitelist: group: "*", kind: "*"` (any cluster-scoped resource)
  - `namespaceResourceWhitelist: group: "*", kind: "*"` (any namespace-scoped resource)
- **Impact**: If ArgoCD is compromised, an attacker can deploy any workload to any namespace, including privileged pods, new cluster roles, or modify existing infrastructure.
- **CVSS Estimate**: 9.1 (Critical)
- **Fix**: Restrict to specific repositories, namespaces, and resource types:
  ```yaml
  spec:
    sourceRepos:
      - "https://github.com/your-org/E2E-EKS-GitOps"
    destinations:
      - namespace: "mlflow"
        server: "https://kubernetes.default.svc"
      - namespace: "kserve"
        server: "https://kubernetes.default.svc"
      # ... etc
    clusterResourceWhitelist:
      - group: ""
        kind: "Namespace"
      - group: "rbac.authorization.k8s.io"
        kind: "ClusterRole"
      - group: "rbac.authorization.k8s.io"
        kind: "ClusterRoleBinding"
  ```
- **Owner**: GitOps / Security Team

---

## HIGH Issues

### HIGH-001: Backend Local Terraform (All Environments)

- **Files**: `infra/environments/*/main.tf`
- **Issue**: All three environments use local Terraform backend (S3 backend is commented out).
- **Impact**: Risk of state file loss, no state locking, no collaboration safety.
- **Fix**: Follow the activation checklist in each `main.tf` (requires AWS account):
  1. Run `aws configure`
  2. Run `./scripts/bootstrap-terraform-backend.sh <env> us-west-2`
  3. Uncomment the backend block
  4. Run `terraform init -migrate-state`
- **Status**: Procedure documented; pending AWS account setup.
- **Owner**: Infrastructure Team

---

### HIGH-002: Kubernetes Version 1.28 (Near End of Support) — FIXED

- **File**: `infra/modules/eks/variables.tf`
- **Issue**: Default Kubernetes version was `1.28` (EOL November 2024).
- **Impact**: No security patches after EOL, potential compatibility issues with newer addons.
- **Fix**: Updated default to `1.32` across all environments and added validation to prevent regressions below 1.30.
- **Status**: ✅ Fixed 2026-06-09
- **Owner**: Infrastructure Team

---

### HIGH-003: Unrestricted Node Egress in Dev/Staging

- **File**: `infra/modules/vpc/variables.tf`
- **Issue**: `node_egress_cidrs` defaults to `["0.0.0.0/0"]`.
- **Impact**: EKS nodes can initiate outbound connections to any IP on the internet.
- **Fix**: Restrict to VPC CIDR and required corporate ranges.
- **Owner**: Network / Infrastructure Team

---

### HIGH-004: Hardcoded CIDR in Production Egress

- **File**: `infra/environments/prod/main.tf`
- **Issue**: `node_egress_cidrs` hardcodes `"10.0.0.0/8"`.
- **Impact**: If VPC CIDR doesn't belong to `10.0.0.0/8`, the rule is inconsistent.
- **Fix**: Derive from a variable or `var.vpc_cidr`.
- **Owner**: Infrastructure Team

---

### HIGH-005: `latest` Image Tags in Feast Server

- **File**: `k8s/mlops-stack/feast/feast-server.yaml`
- **Issue**: Uses `feastdev/feature-server:latest`.
- **Impact**: Non-reproducible deployments, risk of breaking changes.
- **Fix**: Pin to a specific version (e.g., `feastdev/feature-server:0.40.1`).
- **Owner**: ML Platform Team

---

### HIGH-006: `latest` Image Tags in Monitoring Stack

- **File**: `gitops/charts/monitoring-stack/values.yaml`
- **Issue**: Uses `evidentlyai/evidently-service:latest`.
- **Impact**: Non-reproducible deployments.
- **Fix**: Pin to a specific version.
- **Owner**: ML Platform Team

---

### HIGH-007: `latest` Image Tags in Argo Workflow Templates

- **Files**: `k8s/mlops-stack/argo-workflows/workflow-templates/*.yaml`
- **Issue**: Multiple workflow templates use images like `mlops/feature-engineer:latest`, `mlops/model-trainer:latest`, etc.
- **Impact**: Non-reproducible ML pipelines, risk of training/inference inconsistencies.
- **Fix**: Pin all workflow images to immutable tags (SHA or semantic version).
- **Owner**: ML Platform / DevOps Team

---

### HIGH-008: KServe HTTP Without HTTPS Redirect

- **File**: `k8s/mlops-stack/kserve/istio-config.yaml`
- **Issue**: Gateway exposes port 80 HTTP without automatic redirect to HTTPS.
- **Impact**: Users may accidentally use unencrypted channels.
- **Fix**: Add HTTPS redirect in Istio Gateway configuration.
- **Owner**: Platform Team

---

### HIGH-009: Grafana Data Loss (`emptyDir`)

- **File**: `gitops/applications/apps/monitoring/base/grafana-deployment.yaml`
- **Issue**: Grafana uses `emptyDir` for `/var/lib/grafana`.
- **Impact**: All dashboards, users, and settings are lost on pod restart.
- **Fix**: Replace with a PVC.
- **Owner**: Platform Team

---

### HIGH-010: Prometheus Data Loss (Deployment vs StatefulSet)

- **File**: `gitops/applications/apps/monitoring/base/prometheus-deployment.yaml`
- **Issue**: Uses a `Deployment` instead of `StatefulSet` for Prometheus.
- **Impact**: Time-series data is lost on pod restart or reschedule.
- **Fix**: Convert to `StatefulSet` with PVC.
- **Owner**: Platform Team

---

### HIGH-011: Python Import Errors

- **Files**:
  - `ml-platform/src/main.py` line 210: `from utils.logging_config import ...` (missing `src.` prefix)
  - `ml-platform/src/main.py` line 298: `sys.exit(1)` without `import sys`
- **Impact**: Application crashes on startup or specific code paths.
- **Fix**: Correct imports.
- **Owner**: ML Platform Team

---

### HIGH-012: Missing Python Dependencies in pyproject.toml

- **File**: `ml-platform/pyproject.toml`
- **Issue**: `fastapi` and `uvicorn` are imported in `src/monitoring/monitoring_service.py` but not declared in `[project.dependencies]`.
- **Impact**: Application fails to start when installed via Poetry/pip.
- **Fix**: Add `fastapi>=0.100` and `uvicorn[standard]>=0.23` to dependencies.
- **Owner**: ML Platform Team

---

## CI/CD Issues

### HIGH-013: Tests Hiding Failures with `|| true`

- **Files**: `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`
- **Issue**: Multiple test/lint steps use `|| true`, causing pipelines to pass even when tests fail.
- **Impact**: Broken code can be merged unnoticed.
- **Fix**: Remove `|| true` from test and lint commands.
- **Owner**: DevOps Team

---

## Action Plan

| Priority | Issue | Estimated Effort | Assignee |
|----------|-------|-----------------|----------|
| P0 | CRIT-003: Docker executor & socket | 4h | DevSecOps |
| P0 | CRIT-004: ArgoCD AppProject | 2h | GitOps |
| P0 | CRIT-001 & CRIT-002: Argo Workflows TLS/Auth | 4h | Platform |
| P1 | HIGH-005 to HIGH-007: Pin all `latest` tags | 3h | ML Platform |
| P1 | HIGH-011 & HIGH-012: Python fixes | 1h | ML Platform |
| P1 | HIGH-013: Remove `\|\| true` from CI | 1h | DevOps |
| P2 | HIGH-001: Terraform S3 backend (requires AWS account) | 2h | Infrastructure |
| P2 | HIGH-002: Upgrade Kubernetes (requires AWS account + EKS testing) | 4h | Infrastructure |
| P2 | HIGH-009 & HIGH-010: Grafana/Prometheus persistence | 3h | Platform |
| P2 | HIGH-008: KServe HTTPS redirect | 2h | Platform |

---

## Verification Checklist

Before marking this report as resolved:

- [x] CRIT-001: Argo Workflows `--secure=true` (corregido 2026-06-07)
- [x] CRIT-002: Argo Workflows `--auth-mode=sso` (corregido 2026-06-07)
- [x] CRIT-003: No `docker.sock` mounts, executor = `emissary` (corregido 2026-06-07)
- [ ] CRIT-004: AppProject restricted to specific repos/namespaces/resources
- [x] HIGH-009: Grafana `emptyDir` replaced with PVC (corregido 2026-06-08)
- [x] HIGH-010: Prometheus converted to StatefulSet with PVC (corregido 2026-06-08)
- [x] HIGH-005: Feast `latest` tag pinned to `0.40.1` (corregido 2026-06-26)
- [ ] HIGH-006 to HIGH-007: Zero occurrences of `:latest` in Evidently and Argo workflow templates
- [x] HIGH-011: `python -c "import src.main"` succeeds without errors (corregido 2026-06-08)
- [x] HIGH-012: `poetry install` succeeds and `src.monitoring.monitoring_service` imports correctly (corregido 2026-06-08)
- [ ] HIGH-013: CI pipeline fails when tests fail (intentionally inject a failing test to verify)

---

*This report was generated by OpenCode AI. Update this file as issues are resolved.*
