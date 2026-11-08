output "cloudtrail_arn" {
  description = "ARN of the multi-region account trail"
  value       = aws_cloudtrail.account.arn
}

output "cloudtrail_bucket" {
  description = "Bucket that stores the encrypted trail logs"
  value       = aws_s3_bucket.trail.id
}

output "guardduty_detector_id" {
  description = "GuardDuty detector ID, or null when disabled"
  value       = one(aws_guardduty_detector.account[*].id)
}

output "access_analyzer_arn" {
  description = "ARN of the account access analyzer"
  value       = aws_accessanalyzer_analyzer.account.arn
}
