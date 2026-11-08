variable "aws_region" {
  description = "Home region for the account baseline; the trail is multi-region."
  type        = string
  default     = "us-east-1"
}

variable "enable_guardduty" {
  description = "Enable GuardDuty with EKS audit log monitoring. Billed by analyzed events after the trial."
  type        = bool
  default     = true
}

variable "trail_retention_days" {
  description = "Days to keep CloudTrail log files in S3."
  type        = number
  default     = 365

  validation {
    condition     = var.trail_retention_days >= 90
    error_message = "Keep CloudTrail logs for at least 90 days."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget for the account, in USD."
  type        = number
  default     = 20
}

variable "budget_alert_emails" {
  description = "Addresses notified at 50% of the actual budget and 100% of the forecast. No budget is created when empty."
  type        = list(string)
  default     = []
}
