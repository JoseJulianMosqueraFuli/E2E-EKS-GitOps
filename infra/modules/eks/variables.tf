# EKS Module Variables

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version. Must be a supported EKS version."
  type        = string
  default     = "1.32"

  validation {
    condition     = can(regex("^(1\\.(3[0-2]|[2-9][0-9]))$", var.kubernetes_version))
    error_message = "Kubernetes version must be 1.30 or higher. EKS no longer supports versions below 1.30."
  }
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "endpoint_public_access" {
  description = "Whether the EKS public API endpoint is enabled. WARNING: Disable (false) by default and use private endpoints or specific CIDRs."
  type        = bool
  default     = false
}

variable "public_access_cidrs" {
  description = "List of CIDR blocks for public API access. NEVER use 0.0.0.0/0. Use specific /32 IPs or leave empty when public endpoint is disabled."
  type        = list(string)
  default     = []

  validation {
    condition     = length(var.public_access_cidrs) == 0 || alltrue([for cidr in var.public_access_cidrs : cidr != "0.0.0.0/0"])
    error_message = "Public access CIDRs must not contain 0.0.0.0/0. Specify your exact IP ranges."
  }
}

variable "cluster_log_types" {
  description = "List of control plane logging types to enable"
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
}

variable "kms_key_arn" {
  description = "ARN of KMS key for EKS encryption"
  type        = string
}

variable "node_group_capacity_type" {
  description = "Type of capacity associated with the EKS Node Group"
  type        = string
  default     = "ON_DEMAND"
}

variable "node_group_instance_types" {
  description = "List of instance types for the EKS Node Group"
  type        = list(string)
  default     = ["m5.large"]
}

variable "node_group_ami_type" {
  description = "Type of Amazon Machine Image (AMI) associated with the EKS Node Group"
  type        = string
  default     = "AL2_x86_64"
}

variable "node_group_disk_size" {
  description = "Disk size in GiB for worker nodes"
  type        = number
  default     = 50
}

variable "node_group_desired_size" {
  description = "Desired number of nodes"
  type        = number
  default     = 2
}

variable "node_group_max_size" {
  description = "Maximum number of nodes"
  type        = number
  default     = 4
}

variable "node_group_min_size" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "node_group_max_unavailable" {
  description = "Maximum number of nodes unavailable at once during a version update"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "ebs_csi_driver_version" {
  description = "Version of the EBS CSI driver addon"
  type        = string
  default     = null
}

variable "vpc_cni_version" {
  description = "Version of the VPC CNI addon"
  type        = string
  default     = null
}

variable "coredns_version" {
  description = "Version of the CoreDNS addon"
  type        = string
  default     = null
}

variable "kube_proxy_version" {
  description = "Version of the kube-proxy addon"
  type        = string
  default     = null
}

# ------------------------------------------------------------------------------
# Optional GPU Node Group
# ------------------------------------------------------------------------------
variable "enable_gpu_node_group" {
  description = "Whether to create a GPU-enabled managed node group for NVIDIA workloads"
  type        = bool
  default     = false
}

variable "gpu_node_group_instance_types" {
  description = "Instance types for the GPU node group (e.g., p3.2xlarge, g4dn.xlarge, p4d.24xlarge)"
  type        = list(string)
  default     = ["g4dn.xlarge"]
}

variable "gpu_node_group_desired_size" {
  description = "Desired number of GPU nodes"
  type        = number
  default     = 1
}

variable "gpu_node_group_max_size" {
  description = "Maximum number of GPU nodes"
  type        = number
  default     = 2
}

variable "gpu_node_group_min_size" {
  description = "Minimum number of GPU nodes"
  type        = number
  default     = 0
}

variable "gpu_node_group_disk_size" {
  description = "Disk size in GiB for GPU worker nodes"
  type        = number
  default     = 100
}

variable "gpu_node_group_ami_type" {
  description = "AMI type for GPU nodes. Must be AL2_x86_64_GPU for NVIDIA GPUs"
  type        = string
  default     = "AL2_x86_64_GPU"
}

variable "gpu_node_group_capacity_type" {
  description = "Capacity type for GPU nodes (ON_DEMAND or SPOT)"
  type        = string
  default     = "ON_DEMAND"
}

variable "gpu_node_taints" {
  description = "Taints to apply to GPU nodes to prevent non-GPU workloads from scheduling"
  type = list(object({
    key    = string
    value  = string
    effect = string
  }))
  default = [
    {
      key    = "nvidia.com/gpu"
      value  = "true"
      effect = "NoSchedule"
    }
  ]
}