# NVIDIA GPU Operator

The [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html) automates the deployment and lifecycle management of NVIDIA software components on Kubernetes:

- NVIDIA drivers
- Container toolkit (docker/containerd runtime)
- Device plugin
- DCGM exporter (GPU metrics)
- Node feature discovery (NFD)
- GPU feature discovery (GFD)
- MIG manager (for A100/H100 Multi-Instance GPU)

## Prerequisites

1. **GPU Node Group enabled in Terraform:**
   Set `enable_gpu_node_group = true` in `infra/environments/<env>/terraform.tfvars`.

2. **GPU nodes must have taints** so only GPU workloads schedule there:
   The Terraform module already applies:
   ```yaml
   key: nvidia.com/gpu
   value: "true"
   effect: NoSchedule
   ```

3. **Your pods must tolerate the taint** to use GPUs:
   ```yaml
   tolerations:
     - key: "nvidia.com/gpu"
       operator: "Equal"
       value: "true"
       effect: "NoSchedule"
   ```

## Enabling GPU Operator

Deploy via ArgoCD or Helm:

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update
helm upgrade --install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator --create-namespace \
  --wait --timeout 600s
```

Or apply the ArgoCD Application provided in this directory.

## Verifying GPU Availability

```bash
# Check nodes with GPUs
kubectl get nodes -L nvidia.com/gpu.present

# Check GPU device plugin pods
kubectl get pods -n gpu-operator

# Check GPU metrics (requires DCGM + Prometheus)
kubectl get servicemonitor -n gpu-operator

# Request a GPU in a pod
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  tolerations:
    - key: "nvidia.com/gpu"
      operator: "Equal"
      value: "true"
      effect: "NoSchedule"
  containers:
    - name: cuda
      image: nvidia/cuda:12.0-base-ubuntu22.04
      command: ["nvidia-smi"]
      resources:
        limits:
          nvidia.com/gpu: 1
EOF
```

## MIG (Multi-Instance GPU) — A100/H100 only

Enable MIG partitioning to share a single A100 among multiple workloads:

```yaml
# Example: partition an A100 into 7x 1g.5gb instances
# Set via GPU Operator values or node labels
kubectl label nodes <gpu-node> nvidia.com/mig.config="all-1g.5gb"
```

See [NVIDIA MIG docs](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/) for profiles.

## Cost Considerations

| Instance | GPU | vCPUs | Mem | Spot $/hr | On-Demand $/hr |
|----------|-----|-------|-----|-----------|----------------|
| g4dn.xlarge | T4 | 4 | 16 GiB | ~$0.16 | ~$0.53 |
| p3.2xlarge | V100 | 8 | 61 GiB | ~$0.90 | ~$3.06 |
| p4d.24xlarge | A100 × 8 | 96 | 1.1 TiB | ~$13.0 | ~$32.8 |

Use **Spot instances** (`gpu_node_group_capacity_type = "SPOT"`) for non-critical training jobs.

## Monitoring

GPU metrics are exposed by DCGM exporter at `:9400/metrics`. The Prometheus scrape config and Grafana dashboard are in `k8s/mlops-stack/monitoring/dashboards/gpu-dashboard.json`.
