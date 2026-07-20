# Cost Estimation — E2E-EKS-GitOps on AWS

**Last updated**: 2026-07-13  
**Pricing basis**: on-demand, us-east-1 / us-west-2. Prices are approximate and may vary.  
**Monthly hours**: 730

---

## 1. Base infrastructure (per environment)

| Resource | Hour | Day | Month |
|---|---|---|---|
| EKS Control Plane | $0.10 | $2.40 | $73.00 |
| NAT Gateway (2 AZs) | $0.09 | $2.16 | $65.70 |
| 2 × t3.medium (EC2) | $0.0832 | $2.00 | $60.74 |
| EBS gp3 50GB ×2 | $0.011 | $0.26 | $8.00 |
| S3 (10GB artifacts) | — | — | $0.23 |
| ECR (5GB images) | — | — | $0.50 |
| KMS (1 key) | — | — | $1.00 |
| Glue (1 crawler/day) | — | $0.44 | $13.20 |
| CloudWatch | — | — | $10.00 |
| **TOTAL base** | **~$0.28** | **~$7.26** | **~$232** |

> MLflow, KServe, ArgoCD, Litmus, Prometheus, Grafana, and other pods run on the
> same EC2 nodes. They do not generate extra compute cost unless they trigger
> the cluster autoscaler.

---

## 2. Scenarios by environment count

| Scenario | Hour | Day | Month |
|---|---|---|---|
| **Only dev** | ~$0.28 | ~$7 | **~$232** |
| **dev + staging** | ~$0.56 | ~$14 | **~$464** |
| **dev + staging + prod** | ~$0.84 | ~$20 | **~$696** |

---

## 3. GPU nodes (optional, disabled by default)

| Instance | GPU | Hour | Day | Month |
|---|---|---|---|---|
| g4dn.xlarge | 1 × T4 | $0.526 | $12.62 | $384 |
| g4dn.2xlarge | 1 × T4 | $0.752 | $18.05 | $549 |
| p3.2xlarge | 1 × V100 | $3.06 | $73.44 | $2,234 |

> One g4dn.xlarge costs more than the entire base cluster. Enable GPU nodes only
> when training requires CUDA.

---

## 4. Chaos Engineering incremental cost

| Activity | Cost per experiment |
|---|---|
| Pod-delete (same node, no replacement) | $0 |
| CPU/memory hog (same node) | $0 |
| Node-drain / EC2 stop (1 replacement node for 1h) | ~$0.04 |
| **10 experiments/month** | **~$0.40/month** |

> Chaos engineering is effectively free for pod-level experiments. Node-level
> experiments pay only for the temporary replacement node.

---

## 5. Budget scenarios

| Budget | What it covers |
|---|---|
| **~$250/month** | Only dev, on-demand, shut down 16h/day |
| **~$350/month** | dev + staging with spot instances |
| **~$700/month** | dev + staging + prod, all on-demand 24/7 |
| **~$1,100/month** | Above + GPU in dev |

---

## 6. Cost optimization recommendations

### 6.1 Use spot instances for dev and staging

```hcl
# infra/environments/dev/variables.tf
node_group_capacity_type = "SPOT"
```

**Savings**: ~60–70% of EC2 compute cost.

### 6.2 Single NAT Gateway in dev

```hcl
# infra/environments/dev/main.tf
public_subnet_count = 1
private_subnet_count = 1
```

**Savings**: ~$33/month.

### 6.3 Shut down non-production clusters

Turn off dev/staging at night and weekends. If off 12h/day:

**Savings**: ~50% of EC2 + NAT Gateway data processing.

### 6.4 Use t3.small if workload allows

```hcl
node_group_instance_types = ["t3.small"]
```

**Savings**: ~$30/month per node.

### 6.5 Reduce NAT Gateway data processing

Keep most traffic inside the VPC. Use VPC endpoints for S3 and ECR.

---

## 7. Fixed vs variable costs

| Cost type | Resource | Monthly |
|---|---|---|
| **Fixed** | EKS Control Plane, NAT Gateway (per AZ), KMS key | ~$107–140 |
| **Variable** | EC2 nodes, EBS, S3/ECR storage, Glue runs, data transfer | Scales with usage |

The largest fixed cost is the NAT Gateway. If running multiple environments,
consider a shared VPC or NAT Instance for non-production.

---

## 8. E2E test cost reference

From the project README:

> Running the full E2E test on AWS incurs real costs. Here is what to expect:
>
> | Resource | Cost/Hour |
> |---|---|
> | EKS Control Plane | $0.10 |
> | NAT Gateway | $0.045 |
> | EC2 m5.large (x2 nodes) | $0.192 each |
> | **Total for a 3-hour E2E test** | **~$2.50 – $4.00 USD** |
>
> Tip: Always run `make destroy ENV=dev` immediately after testing to avoid ongoing charges.

---

## 9. Monitoring costs

Prometheus and Grafana run on the cluster nodes, so they do not add compute cost.
CloudWatch metrics/logs are the main additional expense:

- CloudWatch Logs: ~$0.50/GB ingested
- CloudWatch Metrics: ~$0.30/metric/month

---

## 10. Chaos Engineering cost safety

- Pod-delete and CPU-hog experiments do not create new nodes → **$0 extra**.
- Node-drain and EC2-stop experiments may trigger the autoscaler → pay only for the temporary replacement node.
- **Recommendation**: set a maximum experiment budget (e.g., 10 experiments/month) and alert if node hours exceed a threshold.

---

*Update this file when instance types, region, or pricing change.*
