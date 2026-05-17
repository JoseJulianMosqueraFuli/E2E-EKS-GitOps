# Cost Monitoring Dashboard

This Grafana dashboard estimates Kubernetes workload costs based on **resource requests** (CPU and memory) using approximate AWS on-demand pricing.

## Prerequisites

- `kube-state-metrics` must be installed in the cluster (scraped by Prometheus).
- Prometheus data source configured in Grafana.

## Pricing Assumptions

The dashboard uses these **approximate** AWS on-demand prices (us-west-2) for estimation:

| Resource | Price | Notes |
|----------|-------|-------|
| vCPU | $0.0416 / hour | Based on m5.large on-demand |
| Memory (GiB) | $0.00405 / hour | Based on m5.large on-demand |

> These values are **estimates** and should be updated to match your actual negotiated rates, Reserved Instances, or Spot pricing.

## How to Update Prices

Edit the PromQL expressions in `cost-monitoring-dashboard.json` and replace the hardcoded multipliers:

- CPU: `* 0.0416`
- Memory: `/ (1024 * 1024 * 1024) * 0.00405`

For more accurate cost tracking, consider integrating with:
- [Kubecost](https://www.kubecost.com/)
- [OpenCost](https://www.opencost.io/)
- AWS Cost and Usage Reports (CUR) via Athena

## Import into Grafana

1. Copy the dashboard JSON to your Grafana instance.
2. Or mount the ConfigMap in the Grafana deployment under `/var/lib/grafana/dashboards`.

## Panels

1. **Estimated Daily Cost by Namespace** — Stacked line chart of daily cost per namespace.
2. **Total Estimated Daily Cluster Cost** — Single stat of total cluster daily cost.
3. **Top 10 Expensive Pods (CPU)** — Bar gauge of highest CPU-cost pods.
4. **Top 10 Expensive Pods (Memory)** — Bar gauge of highest memory-cost pods.
5. **Cost per Experiment / Run** — Table correlating MLflow namespaces with hourly averages.
