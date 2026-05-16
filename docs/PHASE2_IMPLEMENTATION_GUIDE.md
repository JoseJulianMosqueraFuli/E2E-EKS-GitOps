# 🚀 MLOps Platform: Next-Phase Implementation Guide

> **Date**: May 16, 2026  
> **Project**: E2E MLOps Platform on EKS  
> **Current State**: Core platform validated (9.2/10) — ready for advanced features

This document maps out the implementation plan for three advanced capabilities:
**GitOps for Infrastructure**, **Chaos Engineering**, and **Platform Administration & Monitoring**.

---

## 📋 Table of Contents

1. [GitOps for Infrastructure](#1-gitops-for-infrastructure)
2. [Chaos Engineering](#2-chaos-engineering)
3. [Platform Administration & Monitoring](#3-platform-administration--monitoring)
4. [Implementation Roadmap](#4-implementation-roadmap)
5. [Prerequisites](#5-prerequisites)

---

## 1. GitOps for Infrastructure

### 1.1 The Problem

Currently, infrastructure (Terraform in `infra/`) is applied manually or via CI. There is **no GitOps loop for AWS resources** — changes require running `terraform apply` by hand.

### 1.2 The Goal

Manage AWS infrastructure (VPC, EKS, S3, IAM, etc.) through the **same GitOps workflow** as applications:

```
Git commit → ArgoCD/Flux detects → Infrastructure applied → Status reported back
```

### 1.3 Options Evaluated

| Tool | Pros | Cons | Recommendation |
|------|------|------|----------------|
| **Crossplane** | Native K8s CRDs, unified GitOps flow, multi-cloud | Learning curve, new resource model | ⭐ **Recommended** |
| **terraform-controller** (Flux) | Reuses existing Terraform modules, easy migration | Less mature, depends on Terraform CLI | Good alternative |
| **Atlantis** | PR-based workflow, team collaboration | Requires separate server, not pure GitOps | Good for teams |

### 1.4 Proposed Architecture (Crossplane)

```
┌─────────────────────────────────────────────────────────────┐
│                      Git Repository                          │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ infra/compositions/│  │ infra/claims/  │                   │
│  │  (XRDs)         │  │  (dev/stg/prod) │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
└───────────┼────────────────────┼─────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Crossplane  │  │  ArgoCD/Flux │  │  Config Provider │  │
│  │  Controller  │  │  (sync)      │  │  (aws-provider)  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │             │
│         ▼                 ▼                    ▼             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Managed Resources (MRs)                 │    │
│  │  VPCNetwork, EKS Cluster, S3 Bucket, IAM Role, etc. │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                      AWS Cloud                               │
│  VPC │ EKS │ S3 │ ECR │ IAM │ RDS │ KMS                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.5 Implementation Steps

#### Step 1: Install Crossplane and AWS Provider

```bash
# Install Crossplane via Helm
helm repo add crossplane-stable https://charts.crossplane.io/stable
helm repo update
helm install crossplane crossplane-stable/crossplane \
  --namespace crossplane-system --create-namespace

# Install AWS Provider
kubectl crossplane install provider crossplane/provider-aws:v0.47.0

# Wait for provider to be ready
kubectl wait --for=condition=Healthy provider.pkg.crossplane.io/provider-aws --timeout=120s
```

**Files to create:**
- `gitops/infrastructure/crossplane/crossplane-install.yaml`
- `gitops/infrastructure/crossplane/aws-provider.yaml`

#### Step 2: Configure AWS Credentials (IRSA)

```yaml
# gitops/infrastructure/crossplane/provider-config.yaml
apiVersion: aws.crossplane.io/v1beta1
kind: ProviderConfig
metadata:
  name: default
spec:
  credentials:
    source: IRSA
    # Crossplane's service account will have an IAM role via IRSA
```

#### Step 3: Define Composite Resource Definitions (XRDs)

Create reusable infrastructure compositions:

```yaml
# gitops/infrastructure/compositions/vpc.yaml
apiVersion: apiextensions.crossplane.io/v1
kind: CompositeResourceDefinition
metadata:
  name: xvpcs.infrastructure.mlops.io
spec:
  group: infrastructure.mlops.io
  names:
    kind: XVpc
    plural: xvpcs
  versions:
    - name: v1alpha1
      served: true
      referenceable: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                cidrBlock:
                  type: string
                region:
                  type: string
```

```yaml
# gitops/infrastructure/compositions/vpc-composition.yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: aws-vpc-composition
  labels:
    provider: aws
spec:
  writeConnectionSecretsToNamespace: crossplane-system
  compositeTypeRef:
    apiVersion: infrastructure.mlops.io/v1alpha1
    kind: XVpc
  resources:
    - name: vpc
      base:
        apiVersion: ec2.aws.crossplane.io/v1beta1
        kind: VPC
        spec:
          forProvider:
            region: us-west-2
            cidrBlock: "10.0.0.0/16"
            enableDnsSupport: true
            enableDnsHostnames: true
```

#### Step 4: Create Environment Claims

```yaml
# gitops/infrastructure/claims/dev/vpc.yaml
apiVersion: infrastructure.mlops.io/v1alpha1
kind: XVpc
metadata:
  name: mlops-dev-vpc
  namespace: crossplane-system
spec:
  cidrBlock: "10.0.0.0/16"
  region: us-west-2
  compositionRef:
    name: aws-vpc-composition
```

#### Step 5: ArgoCD Application for Infrastructure

```yaml
# gitops/applications/projects/infrastructure-gitops.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: infrastructure-gitops
  namespace: argocd
spec:
  project: mlops-infra
  source:
    repoURL: https://github.com/YOUR_ORG/E2E-EKS-GitOps.git
    targetRevision: main
    path: gitops/infrastructure/claims/dev
  destination:
    server: https://kubernetes.default.svc
    namespace: crossplane-system
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### 1.6 Migration Strategy (Terraform → Crossplane)

| Phase | Action | Timeline |
|-------|--------|----------|
| **1** | Install Crossplane + AWS Provider | Week 1 |
| **2** | Migrate VPC and S3 to Crossplane compositions | Week 1-2 |
| **3** | Migrate EKS cluster (complex, keep Terraform temporarily) | Week 2-3 |
| **4** | Migrate IAM roles and IRSA bindings | Week 3 |
| **5** | Decommission Terraform (or keep for EKS only) | Week 4 |

### 1.7 Success Criteria

- [ ] Crossplane installed and AWS Provider healthy
- [ ] VPC created via Crossplane claim
- [ ] S3 buckets created via Crossplane claim
- [ ] ArgoCD syncs infrastructure claims automatically
- [ ] `kubectl get xvpcs` shows infrastructure status
- [ ] Terraform state migrated or decommissioned

---

## 2. Chaos Engineering

### 2.1 Why Chaos for MLOps?

MLOps platforms have **critical data flows** that must survive failures:
- ML training runs that last hours/days
- Model inference serving that must stay available
- Data pipelines that must not corrupt datasets
- Experiment tracking that must not lose run metadata

### 2.2 Tool Selection

| Tool | Pros | Cons | Recommendation |
|------|------|------|----------------|
| **Chaos Mesh** | Native K8s CRDs, rich experiment types, UI dashboard | Requires CRD installation | ⭐ **Recommended** |
| **LitmusChaos** | Large experiment library, CNCF project | More complex setup | Good alternative |
| **Gremlin** | Enterprise support, SaaS | Paid, external dependency | Not for this project |

### 2.3 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chaos Mesh Controller                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  PodChaos    │  │ NetworkChaos │  │  StressChaos     │  │
│  │  (kill/fail) │  │ (delay/loss) │  │  (cpu/mem/io)    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │             │
└─────────┼─────────────────┼────────────────────┼─────────────┘
          │                 │                    │
          ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Target Components                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ MLflow   │  │PostgreSQL│  │  MinIO   │  │  KServe    │  │
│  │ Server   │  │  (DB)    │  │ (S3 alt) │  │ (Inference)│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │                 │                    │
          ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Observability Stack                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │Prometheus│  │  Grafana │  │  Evidently│                   │
│  │ (metrics)│  │(dashboards)│ │ (drift)  │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 Implementation Steps

#### Step 1: Install Chaos Mesh

```bash
# Install via Helm
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-testing --create-namespace \
  --set dashboard.create=true \
  --set controllerManager.leaderElection.enabled=true
```

**Files to create:**
- `gitops/infrastructure/chaos-mesh/chaos-mesh-install.yaml`
- `gitops/infrastructure/chaos-mesh/rbac.yaml`

#### Step 2: Define Chaos Experiments

##### Experiment 1: PostgreSQL Pod Kill (Database Resilience)

```yaml
# gitops/chaos-experiments/mlflow-db-resilience.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: mlflow-postgres-pod-kill
  namespace: chaos-testing
spec:
  action: pod-kill
  mode: one
  duration: "60s"
  selector:
    namespaces:
      - mlflow
    labelSelectors:
      app: mlflow-postgresql
  scheduler:
    cron: "@every 2h"
```

**What this tests:** Does MLflow recover automatically when PostgreSQL crashes and restarts?

##### Experiment 2: Network Delay (MLflow ↔ S3 Latency)

```yaml
# gitops/chaos-experiments/mlflow-network-latency.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: mlflow-s3-latency
  namespace: chaos-testing
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - mlflow
    labelSelectors:
      app: mlflow-server
  delay:
    latency: "500ms"
    jitter: "200ms"
  duration: "120s"
  scheduler:
    cron: "@every 4h"
```

**What this tests:** Do MLflow experiments fail gracefully or timeout when S3 is slow?

##### Experiment 3: CPU Stress on KServe (Inference Autoscaling)

```yaml
# gitops/chaos-experiments/kserve-cpu-stress.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: kserve-cpu-stress
  namespace: chaos-testing
spec:
  mode: all
  selector:
    namespaces:
      - kserve
    labelSelectors:
      component: predictor
  stressors:
    cpu:
      workers: 2
      load: 80
  duration: "180s"
  scheduler:
    cron: "@every 6h"
```

**What this tests:** Does KServe's HPA scale up before inference requests fail?

##### Experiment 4: IO Chaos on MinIO (Artifact Corruption)

```yaml
# gitops/chaos-experiments/minio-io-error.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: minio-io-error
  namespace: chaos-testing
spec:
  action: fault
  mode: one
  selector:
    namespaces:
      - mlflow
    labelSelectors:
      app: mlflow-minio
  volumePath: /data
  path: "/data/**/*.parquet"
  methods:
    - read
    - write
  errno: 5  # EIO (Input/Output error)
  duration: "30s"
```

**What this tests:** Are MLflow artifacts protected against disk failures?

#### Step 3: Create Chaos Dashboard

```yaml
# gitops/chaos-experiments/chaos-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chaos-mesh-grafana-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  chaos-mesh-dashboard.json: |
    {
      "dashboard": {
        "title": "Chaos Engineering - MLOps Platform",
        "panels": [
          {
            "title": "Active Chaos Experiments",
            "datasource": "Prometheus",
            "targets": [
              {
                "expr": "chaos_mesh_experiments_running",
                "legendFormat": "{{kind}}"
              }
            ]
          },
          {
            "title": "Experiment Success Rate",
            "datasource": "Prometheus",
            "targets": [
              {
                "expr": "chaos_mesh_experiments_total / chaos_mesh_experiments_failed",
                "legendFormat": "{{namespace}}"
              }
            ]
          }
        ]
      }
    }
```

#### Step 4: Integrate with CI/CD

```yaml
# .github/workflows/chaos-tests.yml (future)
name: Chaos Tests
on:
  schedule:
    - cron: "0 2 * * 1"  # Every Monday at 2 AM
  workflow_dispatch:

jobs:
  chaos-experiments:
    runs-on: ubuntu-latest
    steps:
      - name: Run Chaos Experiments
        run: |
          kubectl apply -f gitops/chaos-experiments/
          # Wait and collect results
          sleep 300
          # Generate report
          kubectl get podchaos,networkchaos,stresschaos -A
```

### 2.5 Success Criteria

- [ ] Chaos Mesh installed and dashboard accessible
- [ ] 4 chaos experiments defined and schedulable
- [ ] Experiments do not cause permanent data loss
- [ ] Recovery time measured and documented for each experiment
- [ ] Grafana dashboard shows experiment status
- [ ] Chaos tests integrated into CI/CD (weekly schedule)

---

## 3. Platform Administration & Monitoring

### 3.1 Current State

| Component | Status | Gap |
|-----------|--------|-----|
| Prometheus | ✅ Installed | No AlertManager configured |
| Grafana | ✅ Installed | No MLOps-specific dashboards |
| Evidently | ✅ Installed | Drift detection only, no platform health |
| Logs | ❌ Missing | No centralized log aggregation |
| Cost Monitoring | ❌ Missing | No visibility into AWS spend per component |
| Health Checks | ❌ Missing | No single endpoint to check platform status |

### 3.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Platform Admin Layer                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  AlertManager│  │    Loki      │  │   OpenCost/      │  │
│  │  (alerts)    │  │  (logs)      │  │   Kubecost       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │             │
│         ▼                 ▼                    ▼             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Grafana (Unified Dashboard)             │    │
│  │                                                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │Platform  │  │  MLOps   │  │  Cost    │          │    │
│  │  │Health    │  │Metrics   │  │Dashboard │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Health Check API (/healthz)             │    │
│  │  Checks: MLflow, PostgreSQL, MinIO, KServe, ArgoCD  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Implementation Steps

#### Step 1: AlertManager Configuration

```yaml
# gitops/applications/apps/monitoring/base/alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m

    route:
      group_by: ['alertname', 'namespace']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'slack-notifications'
      routes:
        - match:
            severity: critical
          receiver: 'pagerduty-critical'
        - match:
            severity: warning
          receiver: 'slack-notifications'

    receivers:
      - name: 'slack-notifications'
        slack_configs:
          - channel: '#mlops-alerts'
            send_resolved: true
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

      - name: 'pagerduty-critical'
        pagerduty_configs:
          - service_key: "${PAGERDUTY_SERVICE_KEY}"
```

**Alert Rules to Create:**

```yaml
# gitops/applications/apps/monitoring/base/mlops-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: mlops-alerts
  namespace: monitoring
spec:
  groups:
    - name: mlflow.rules
      rules:
        - alert: MLflowDown
          expr: up{job="mlflow-server"} == 0
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "MLflow server is down"
            description: "MLflow has been unreachable for more than 2 minutes."

        - alert: MLflowHighLatency
          expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="mlflow-server"}[5m])) > 2
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "MLflow high latency detected"
            description: "95th percentile latency is above 2 seconds."

    - name: postgresql.rules
      rules:
        - alert: PostgreSQLDown
          expr: up{job="mlflow-postgresql"} == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "PostgreSQL is down"
            description: "PostgreSQL has been unreachable for more than 1 minute."

        - alert: PostgreSQLHighConnections
          expr: pg_stat_activity_count{datname="mlflow"} > 80
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "PostgreSQL high connection count"
            description: "More than 80 active connections to MLflow database."

    - name: kserve.rules
      rules:
        - alert: KServeHighErrorRate
          expr: rate(http_requests_total{job="kserve", status=~"5.."}[5m]) / rate(http_requests_total{job="kserve"}[5m]) > 0.05
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "KServe high error rate"
            description: "More than 5% of inference requests are failing."

    - name: drift.rules
      rules:
        - alert: ModelDriftDetected
          expr: evidently_drift_score > 0.1
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Model drift detected"
            description: "Data drift score has exceeded threshold of 0.1."
```

#### Step 2: Loki for Log Aggregation

```yaml
# gitops/applications/apps/monitoring/base/loki-values.yaml
loki:
  enabled: true
  config:
    limits_config:
      retention_period: 720h  # 30 days

promtail:
  enabled: true
  config:
    clients:
      - url: http://loki:3100/loki/api/v1/push

grafana:
  additionalDataSources:
    - name: Loki
      type: loki
      url: http://loki:3100
```

#### Step 3: OpenCost for Cost Monitoring

```yaml
# gitops/applications/apps/monitoring/base/opencost-values.yaml
opencost:
  enabled: true
  prometheus:
    internal:
      url: http://prometheus:9090
  cloudCost:
    enabled: true
    provider: aws
    billingIntegration:
      enabled: true
```

#### Step 4: Platform Health Check API

```yaml
# gitops/applications/apps/monitoring/base/health-check.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: platform-health
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: platform-health
  template:
    metadata:
      labels:
        app: platform-health
    spec:
      serviceAccountName: platform-health-sa
      containers:
        - name: health-checker
          image: python:3.11-slim
          command:
            - /bin/bash
            - -c
            - |
              pip install --no-cache-dir kubernetes requests
              exec python /app/health_check.py
          ports:
            - containerPort: 8080
              name: http
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
          volumeMounts:
            - name: health-script
              mountPath: /app
      volumes:
        - name: health-script
          configMap:
            name: health-check-script

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: health-check-script
  namespace: monitoring
data:
  health_check.py: |
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    from kubernetes import client, config
    import requests

    config.load_incluster_config()
    v1 = client.CoreV1Api()

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/healthz':
                status = self.check_platform_health()
                self.send_response(200 if status['healthy'] else 503)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(status).encode())
            elif self.path == '/ready':
                self.send_response(200)
                self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

        def check_platform_health(self):
            checks = {}
            overall_healthy = True

            # Check MLflow
            try:
                resp = requests.get('http://mlflow-server.mlflow:5000/health', timeout=5)
                checks['mlflow'] = {'status': 'healthy' if resp.status_code == 200 else 'unhealthy'}
            except:
                checks['mlflow'] = {'status': 'unreachable'}
                overall_healthy = False

            # Check PostgreSQL
            try:
                pods = v1.list_namespaced_pod(namespace='mlflow', label_selector='app=mlflow-postgresql')
                ready = any(p.status.phase == 'Running' for p in pods.items)
                checks['postgresql'] = {'status': 'healthy' if ready else 'unhealthy'}
                if not ready:
                    overall_healthy = False
            except:
                checks['postgresql'] = {'status': 'unreachable'}
                overall_healthy = False

            # Check MinIO
            try:
                resp = requests.get('http://mlflow-minio.mlflow:9000/minio/health/ready', timeout=5)
                checks['minio'] = {'status': 'healthy' if resp.status_code == 200 else 'unhealthy'}
            except:
                checks['minio'] = {'status': 'unreachable'}

            # Check KServe
            try:
                pods = v1.list_namespaced_pod(namespace='kserve', label_selector='component=predictor')
                running = sum(1 for p in pods.items if p.status.phase == 'Running')
                checks['kserve'] = {'status': 'healthy', 'running_pods': running}
            except:
                checks['kserve'] = {'status': 'unreachable'}

            # Check ArgoCD
            try:
                pods = v1.list_namespaced_pod(namespace='argocd', label_selector='app.kubernetes.io/name=argocd-server')
                ready = any(p.status.phase == 'Running' for p in pods.items)
                checks['argocd'] = {'status': 'healthy' if ready else 'unhealthy'}
            except:
                checks['argocd'] = {'status': 'unreachable'}

            return {'healthy': overall_healthy, 'checks': checks}

    if __name__ == '__main__':
        server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
        server.serve_forever()
```

#### Step 5: Grafana Dashboards

Create MLOps-specific dashboards:

```yaml
# gitops/applications/apps/monitoring/base/grafana-mlops-dashboards.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-mlops-dashboards
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  platform-health-dashboard.json: |
    {
      "dashboard": {
        "title": "MLOps Platform Health",
        "panels": [
          {
            "title": "Platform Health Status",
            "type": "stat",
            "targets": [
              {
                "expr": "up{job=~'mlflow-server|mlflow-postgresql|mlflow-minio'}",
                "legendFormat": "{{job}}"
              }
            ]
          },
          {
            "title": "Active MLflow Experiments",
            "type": "timeseries",
            "targets": [
              {
                "expr": "mlflow_active_runs",
                "legendFormat": "Active Runs"
              }
            ]
          },
          {
            "title": "Model Inference Latency (p95)",
            "type": "timeseries",
            "targets": [
              {
                "expr": "histogram_quantile(0.95, rate(kserve_inference_duration_seconds_bucket[5m]))",
                "legendFormat": "{{model_name}}"
              }
            ]
          },
          {
            "title": "Data Drift Score",
            "type": "gauge",
            "targets": [
              {
                "expr": "evidently_drift_score",
                "legendFormat": "Drift"
              }
            ]
          }
        ]
      }
    }
```

### 3.4 Success Criteria

- [ ] AlertManager configured with Slack/PagerDuty integration
- [ ] 8+ alert rules defined (MLflow, PostgreSQL, KServe, drift)
- [ ] Loki installed and collecting logs from all namespaces
- [ ] OpenCost installed with AWS billing integration
- [ ] Health check API returns 200 with component status
- [ ] 3 Grafana dashboards created (Platform Health, MLOps Metrics, Cost)
- [ ] All alerts tested and verified

---

## 4. Implementation Roadmap

### Phase 1: GitOps for Infrastructure (Weeks 1-4)

| Week | Tasks | Deliverables |
|------|-------|--------------|
| **1** | Install Crossplane, AWS Provider, configure IRSA | Crossplane running, provider healthy |
| **2** | Create XRDs for VPC and S3, write compositions | VPC and S3 compositions ready |
| **3** | Create environment claims (dev), test sync | Dev VPC and S3 created via GitOps |
| **4** | Migrate EKS (or keep Terraform), document | Infrastructure fully GitOps-managed |

### Phase 2: Chaos Engineering (Weeks 5-7)

| Week | Tasks | Deliverables |
|------|-------|--------------|
| **5** | Install Chaos Mesh, configure RBAC | Chaos Mesh running, dashboard accessible |
| **6** | Create 4 chaos experiments (DB, network, CPU, IO) | Experiments defined and schedulable |
| **7** | Integrate with Grafana, test recovery | Dashboard shows experiments, recovery documented |

### Phase 3: Platform Administration (Weeks 8-10)

| Week | Tasks | Deliverables |
|------|-------|--------------|
| **8** | Install AlertManager, create alert rules | Alerts configured, tested |
| **9** | Install Loki, configure log aggregation | Logs centralized, searchable |
| **10** | Install OpenCost, create health check API, dashboards | Cost visibility, health endpoint, Grafana dashboards |

### Parallel Work (Ongoing)

- **Documentation**: Update guides as features are implemented
- **Testing**: Validate each component before moving to next phase
- **Security**: Review RBAC, secrets, and network policies for new components

---

## 5. Prerequisites

### Required Tools

```bash
# Already installed
terraform >= 1.0
kubectl >= 1.25
helm >= 3.0
aws-cli >= 2.0
python >= 3.9
make

# New tools needed
crossplane-cli >= 1.14    # For Crossplane management
chaosctl >= 2.5           # For Chaos Mesh CLI
```

### Required AWS Services

| Service | Purpose | Cost Estimate (dev) |
|---------|---------|---------------------|
| EKS | Kubernetes cluster | ~$73/month |
| VPC | Network infrastructure | Free |
| S3 | Artifact storage | ~$5/month |
| ECR | Container registry | ~$1/month |
| RDS (optional) | PostgreSQL (production) | ~$15/month |
| Secrets Manager | Secret storage | ~$0.40/month |
| ACM | TLS certificates | Free |
| CloudWatch | Metrics/logs | ~$3/month |

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "eks:*",
        "s3:*",
        "ecr:*",
        "iam:CreateRole",
        "iam:CreatePolicy",
        "iam:AttachRolePolicy",
        "secretsmanager:*",
        "kms:*",
        "rds:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Required Kubernetes Addons

| Addon | Purpose | Installation |
|-------|---------|--------------|
| cert-manager | TLS certificate management | Helm chart |
| metrics-server | HPA metrics | EKS addon |
| external-secrets | Secret synchronization | Helm chart |
| prometheus-operator | Monitoring stack | Helm chart |
| argocd | GitOps for applications | Helm chart |
| crossplane | GitOps for infrastructure | Helm chart |
| chaos-mesh | Chaos engineering | Helm chart |

---

## 📝 Notes

- **Start small**: Implement one component at a time, validate, then move to the next.
- **Test in dev first**: All chaos experiments should be tested in the dev environment before scheduling.
- **Document everything**: Keep this guide updated as you implement each phase.
- **Monitor costs**: Use OpenCost from day one to track spending as you add components.
- **Security first**: Review RBAC and network policies for every new component before deploying.

---

**Last Updated**: May 16, 2026  
**Maintained By**: MLOps Platform Team  
**Status**: 📋 Planning Phase
