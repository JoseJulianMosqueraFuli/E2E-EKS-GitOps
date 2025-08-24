package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestGlueModule(t *testing.T) {
	t.Parallel()

	// Define the Terraform options
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		// Path to the Terraform code that will be tested
		TerraformDir: "../",

		// Variables to pass to our Terraform code using -var options
		Vars: map[string]interface{}{
			"name_prefix": "test-glue",
			"databases": map[string]interface{}{
				"test_raw": map[string]interface{}{
					"name":        "test-raw-data",
					"description": "Test raw data database",
				},
				"test_curated": map[string]interface{}{
					"name":        "test-curated-data",
					"description": "Test curated data database",
				},
			},
			"tables": map[string]interface{}{
				"test_table": map[string]interface{}{
					"name":          "test_training_data",
					"database_name": "test-raw-data",
					"description":   "Test training data table",
					"table_type":    "EXTERNAL_TABLE",
					"storage_descriptor": map[string]interface{}{
						"location":      "s3://test-bucket/training-data/",
						"input_format":  "org.apache.hadoop.mapred.TextInputFormat",
						"output_format": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
						"columns": []interface{}{
							map[string]interface{}{
								"name": "feature_1",
								"type": "double",
							},
							map[string]interface{}{
								"name": "feature_2",
								"type": "double",
							},
						},
					},
				},
			},
			"crawlers": map[string]interface{}{
				"test_crawler": map[string]interface{}{
					"name":          "test-data-crawler",
					"database_name": "test-raw-data",
					"description":   "Test data crawler",
					"s3_targets": []interface{}{
						map[string]interface{}{
							"path": "s3://test-bucket/",
						},
					},
					"tags": map[string]interface{}{
						"Purpose": "testing",
					},
				},
			},
			"s3_bucket_arns": []string{
				"arn:aws:s3:::test-bucket",
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
	t.Run("Glue Database Creation", func(t *testing.T) {
		databaseNames := terraform.OutputMap(t, terraformOptions, "database_names")
		
		assert.Contains(t, databaseNames, "test_raw", "Raw database should be created")
		assert.Contains(t, databaseNames, "test_curated", "Curated database should be created")
		
		assert.Equal(t, "test-raw-data", databaseNames["test_raw"], "Database name should match")
		assert.Equal(t, "test-curated-data", databaseNames["test_curated"], "Database name should match")
	})

	t.Run("Glue Table Creation", func(t *testing.T) {
		tableNames := terraform.OutputMap(t, terraformOptions, "table_names")
		
		assert.Contains(t, tableNames, "test_table", "Test table should be created")
		assert.Equal(t, "test_training_data", tableNames["test_table"], "Table name should match")
	})

	t.Run("Glue Crawler Creation", func(t *testing.T) {
		crawlerNames := terraform.OutputMap(t, terraformOptions, "crawler_names")
		crawlerArns := terraform.OutputMap(t, terraformOptions, "crawler_arns")
		
		assert.Contains(t, crawlerNames, "test_crawler", "Test crawler should be created")
		assert.Equal(t, "test-data-crawler", crawlerNames["test_crawler"], "Crawler name should match")
		assert.Contains(t, crawlerArns["test_crawler"], "test-data-crawler", "Crawler ARN should contain crawler name")
	})

	t.Run("Crawler IAM Role", func(t *testing.T) {
		crawlerRoleArn := terraform.Output(t, terraformOptions, "crawler_role_arn")
		
		assert.NotEmpty(t, crawlerRoleArn, "Crawler role ARN should not be empty")
		assert.Contains(t, crawlerRoleArn, "test-glue-glue-crawler-role", "Role ARN should contain expected name")
	})
}

func TestGlueModuleWithDataQuality(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"name_prefix": "test-dq-glue",
			"databases": map[string]interface{}{
				"test_db": map[string]interface{}{
					"name":        "test-quality-db",
					"description": "Test database for data quality",
				},
			},
			"data_quality_rulesets": map[string]interface{}{
				"test_ruleset": map[string]interface{}{
					"name":        "test-quality-rules",
					"description": "Test data quality ruleset",
					"ruleset":     "[{\"Name\": \"Completeness\", \"Rules\": [\"ColumnCount > 0\"]}]",
					"target_table": map[string]interface{}{
						"database_name": "test-quality-db",
						"table_name":    "test_table",
					},
					"tags": map[string]interface{}{
						"Purpose": "data-quality",
					},
				},
			},
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("Data Quality Ruleset", func(t *testing.T) {
		rulesetNames := terraform.OutputMap(t, terraformOptions, "data_quality_ruleset_names")
		
		assert.Contains(t, rulesetNames, "test_ruleset", "Data quality ruleset should be created")
		assert.Equal(t, "test-quality-rules", rulesetNames["test_ruleset"], "Ruleset name should match")
	})
}

func TestGlueModuleMinimalConfig(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"name_prefix": "test-minimal-glue",
			"databases": map[string]interface{}{
				"minimal_db": map[string]interface{}{
					"name": "minimal-database",
				},
			},
			"create_crawler_role": false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("Minimal Configuration", func(t *testing.T) {
		databaseNames := terraform.OutputMap(t, terraformOptions, "database_names")
		crawlerRoleArn := terraform.Output(t, terraformOptions, "crawler_role_arn")
		
		assert.Contains(t, databaseNames, "minimal_db", "Minimal database should be created")
		assert.Empty(t, crawlerRoleArn, "Crawler role should not be created when disabled")
	})
}