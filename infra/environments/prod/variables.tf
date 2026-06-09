# Production Environment Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_count" {
  description = "Number of public subnets"
  type        = number
  default     = 2
}

variable "private_subnet_count" {
  description = "Number of private subnets"
  type        = number
  default     = 2
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.32"
}

variable "node_group_instance_types" {
  description = "List of instance types for the EKS Node Group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_group_desired_size" {
  description = "Desired number of nodes"
  type        = number
  default     = 2
}

variable "node_group_max_size" {
  description = "Maximum number of nodes"
  type        = number
  default     = 3
}

variable "node_group_min_size" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

# ------------------------------------------------------------------------------
# Optional GPU Node Group Variables
# ------------------------------------------------------------------------------
variable "enable_gpu_node_group" {
  description = "Enable GPU node group for NVIDIA workloads (e.g., training with CUDA)"
  type        = bool
  default     = false
}

variable "gpu_node_group_instance_types" {
  description = "GPU instance types (g4dn.xlarge = cheapest with 1 GPU, p3.2xlarge = V100, p4d = A100)"
  type        = list(string)
  default     = ["g4dn.xlarge"]
}

variable "gpu_node_group_desired_size" {
  description = "Desired number of GPU nodes"
  type        = number
  default     = 0
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