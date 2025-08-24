package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestS3Module(t *testing.T) {
	t.Parallel()

	// Define the Terraform options
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		// Path to the Terraform code that will be tested
		TerraformDir: "../",

		// Variables to pass to our Terraform code using -var options
		Vars: map[string]interface{}{
			"kms_key_arn": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
			"buckets": map[string]interface{}{
				"test_raw_data": map[string]interface{}{
					"name":               "test-mlops-raw-data",
					"versioning_enabled": true,
					"force_destroy":      true,
					"tags": map[string]interface{}{
						"Purpose": "raw-data-storage",
					},
					"lifecycle_rules": []interface{}{
						map[string]interface{}{
							"id":      "test_lifecycle",
							"enabled": true,
							"transitions": []interface{}{
								map[string]interface{}{
									"days":          30,
									"storage_class": "STANDARD_IA",
								},
							},
						},
					},
				},
				"test_curated_data": map[string]interface{}{
					"name":               "test-mlops-curated-data",
					"versioning_enabled": true,
					"force_destroy":      true,
					"tags": map[string]interface{}{
						"Purpose": "curated-data-storage",
					},
				},
			},
		},

		// Disable colors in Terraform commands so its easier to parse stdout/stderr
		NoColor: true,
	})

	// Clean up resources with "terraform destroy" at the end of the test
	defer terraform.Destroy(t, terraformOptions)

	// Run "terraform init" and "terraform apply"
	terraform.InitAndApply(t, terraformOptions)

	// Run basic validation tests
	t.Run("S3 Bucket Creation", func(t *testing.T) {
		bucketIds := terraform.OutputMap(t, terraformOptions, "bucket_ids")
		bucketArns := terraform.OutputMap(t, terraformOptions, "bucket_arns")
		
		assert.Contains(t, bucketIds, "test_raw_data", "Raw data bucket should be created")
		assert.Contains(t, bucketIds, "test_curated_data", "Curated data bucket should be created")
		
		assert.Contains(t, bucketArns["test_raw_data"], "test-mlops-raw-data", "Raw data bucket ARN should contain bucket name")
		assert.Contains(t, bucketArns["test_curated_data"], "test-mlops-curated-data", "Curated data bucket ARN should contain bucket name")
	})

	t.Run("Bucket Domain Names", func(t *testing.T) {
		bucketDomainNames := terraform.OutputMap(t, terraformOptions, "bucket_domain_names")
		bucketRegionalDomainNames := terraform.OutputMap(t, terraformOptions, "bucket_regional_domain_names")
		
		assert.NotEmpty(t, bucketDomainNames["test_raw_data"], "Raw data bucket domain name should not be empty")
		assert.NotEmpty(t, bucketRegionalDomainNames["test_raw_data"], "Raw data bucket regional domain name should not be empty")
	})
}

func TestS3ModuleWithReplication(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"kms_key_arn": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
			"buckets": map[string]interface{}{
				"test_replicated": map[string]interface{}{
					"name":               "test-mlops-replicated",
					"versioning_enabled": true,
					"force_destroy":      true,
					"tags": map[string]interface{}{
						"Purpose": "replication-test",
					},
					"replication_config": map[string]interface{}{
						"role_arn": "arn:aws:iam::123456789012:role/replication-role",
						"rules": []interface{}{
							map[string]interface{}{
								"id":     "replicate_all",
								"status": "Enabled",
								"destination": map[string]interface{}{
									"bucket":        "arn:aws:s3:::destination-bucket",
									"storage_class": "STANDARD_IA",
								},
							},
						},
					},
				},
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("Replication Configuration", func(t *testing.T) {
		bucketIds := terraform.OutputMap(t, terraformOptions, "bucket_ids")
		assert.Contains(t, bucketIds, "test_replicated", "Replicated bucket should be created")
	})
}

func TestS3ModuleMinimalConfig(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"kms_key_arn": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
			"buckets": map[string]interface{}{
				"test_minimal": map[string]interface{}{
					"name":               "test-mlops-minimal",
					"versioning_enabled": false,
					"force_destroy":      true,
					"tags": map[string]interface{}{
						"Purpose": "minimal-test",
					},
				},
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("Minimal Configuration", func(t *testing.T) {
		bucketIds := terraform.OutputMap(t, terraformOptions, "bucket_ids")
		assert.Contains(t, bucketIds, "test_minimal", "Minimal bucket should be created")
	})
}