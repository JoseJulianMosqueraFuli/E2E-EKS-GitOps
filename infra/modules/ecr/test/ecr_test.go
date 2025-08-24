package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestECRModule(t *testing.T) {
	t.Parallel()

	// Define the Terraform options
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		// Path to the Terraform code that will be tested
		TerraformDir: "../",

		// Variables to pass to our Terraform code using -var options
		Vars: map[string]interface{}{
			"kms_key_arn": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
			"repositories": map[string]interface{}{
				"test_trainer": map[string]interface{}{
					"name":                 "test-trainer",
					"image_tag_mutability": "MUTABLE",
					"scan_on_push":         true,
					"tags": map[string]interface{}{
						"Purpose": "ml-training",
					},
				},
				"test_inference": map[string]interface{}{
					"name":                 "test-inference",
					"image_tag_mutability": "IMMUTABLE",
					"scan_on_push":         true,
					"tags": map[string]interface{}{
						"Purpose": "ml-inference",
					},
				},
			},
			"allowed_principals": []string{
				"arn:aws:iam::123456789012:root",
			},
			"enable_registry_scanning": true,
		},

		// Disable colors in Terraform commands so its easier to parse stdout/stderr
		NoColor: true,
	})

	// Clean up resources with "terraform destroy" at the end of the test
	defer terraform.Destroy(t, terraformOptions)

	// Run "terraform init" and "terraform apply"
	terraform.InitAndApply(t, terraformOptions)

	// Run basic validation tests
	t.Run("ECR Repository Creation", func(t *testing.T) {
		repositoryUrls := terraform.OutputMap(t, terraformOptions, "repository_urls")
		repositoryArns := terraform.OutputMap(t, terraformOptions, "repository_arns")
		repositoryNames := terraform.OutputMap(t, terraformOptions, "repository_names")
		
		assert.Contains(t, repositoryUrls, "test_trainer", "Trainer repository should be created")
		assert.Contains(t, repositoryUrls, "test_inference", "Inference repository should be created")
		
		assert.Contains(t, repositoryArns["test_trainer"], "test-trainer", "Trainer repository ARN should contain repository name")
		assert.Contains(t, repositoryArns["test_inference"], "test-inference", "Inference repository ARN should contain repository name")
		
		assert.Equal(t, "test-trainer", repositoryNames["test_trainer"], "Repository name should match")
		assert.Equal(t, "test-inference", repositoryNames["test_inference"], "Repository name should match")
	})

	t.Run("Repository URLs Format", func(t *testing.T) {
		repositoryUrls := terraform.OutputMap(t, terraformOptions, "repository_urls")
		
		assert.Contains(t, repositoryUrls["test_trainer"], ".dkr.ecr.", "Repository URL should contain ECR domain")
		assert.Contains(t, repositoryUrls["test_inference"], ".dkr.ecr.", "Repository URL should contain ECR domain")
	})
}

func TestECRModuleMinimalConfig(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"kms_key_arn": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
			"repositories": map[string]interface{}{
				"test_minimal": map[string]interface{}{
					"name":                 "test-minimal-repo",
					"image_tag_mutability": "MUTABLE",
					"scan_on_push":         false,
					"tags": map[string]interface{}{
						"Environment": "test",
					},
				},
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("Minimal Configuration", func(t *testing.T) {
		repositoryUrls := terraform.OutputMap(t, terraformOptions, "repository_urls")
		assert.Contains(t, repositoryUrls, "test_minimal", "Minimal repository should be created")
	})
}

func TestECRModuleWithReplication(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"kms_key_arn": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
			"repositories": map[string]interface{}{
				"test_replicated": map[string]interface{}{
					"name":                 "test-replicated-repo",
					"image_tag_mutability": "MUTABLE",
					"scan_on_push":         true,
					"tags": map[string]interface{}{
						"Replication": "enabled",
					},
				},
			},
			"replication_configuration": map[string]interface{}{
				"rules": []interface{}{
					map[string]interface{}{
						"destinations": []interface{}{
							map[string]interface{}{
								"region":      "us-east-1",
								"registry_id": "123456789012",
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
		repositoryUrls := terraform.OutputMap(t, terraformOptions, "repository_urls")
		assert.Contains(t, repositoryUrls, "test_replicated", "Replicated repository should be created")
	})
}