# VPC Module Variables

variable "name_prefix" {
  description = "Name prefix for all resources"
  type        = string
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

variable "node_egress_cidrs" {
  description = "Outbound CIDR blocks for EKS node security group. Use [aws_vpc.main.cidr_block] for restricted mode or [\"0.0.0.0/0\"] for open internet access (dev default)."
  type        = list(string)
  default     = ["0.0.0.0/0"]

  validation {
    condition     = length(var.node_egress_cidrs) > 0
    error_message = "At least one egress CIDR must be specified for EKS nodes."
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}