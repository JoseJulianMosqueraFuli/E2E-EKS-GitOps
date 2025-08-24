package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestEKSModule(t *testing.T) {
	t.Parallel()

	// Define the Terraform options
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		// Path to the Terraform code that will be tested
		TerraformDir: "../",

		// Variables to pass to our Terraform code using -var options
		Vars: map[string]interface{}{
			"cluster_name":              "test-eks-cluster",
			"kubernetes_version":        "1.28",
			"public_subnet_ids":         []string{"subnet-12345", "subnet-67890"},
			"private_subnet_ids":        []string{"subnet-abcde", "subnet-fghij"},
			"kms_key_arn":              "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
			"node_group_instance_types": []string{"m5.large"},
			"node_group_desired_size":   2,
			"node_group_max_size":       4,
			"node_group_min_size":       1,
		},

		// Disable colors in Terraform commands so its easier to parse stdout/stderr
		NoColor: true,
	})

	// Clean up resources with "terraform destroy" at the end of the test
	defer terraform.Destroy(t, terraformOptions)

	// Run "terraform init" and "terraform apply"
	terraform.InitAndApply(t, terraformOptions)

	// Run basic validation tests
	t.Run("EKS Cluster Creation", func(t *testing.T) {
		clusterId := terraform.Output(t, terraformOptions, "cluster_id")
		clusterArn := terraform.Output(t, terraformOptions, "cluster_arn")
		clusterEndpoint := terraform.Output(t, terraformOptions, "cluster_endpoint")
		
		assert.NotEmpty(t, clusterId, "Cluster ID should not be empty")
		assert.NotEmpty(t, clusterArn, "Cluster ARN should not be empty")
		assert.NotEmpty(t, clusterEndpoint, "Cluster endpoint should not be empty")
		assert.Contains(t, clusterArn, "test-eks-cluster", "Cluster ARN should contain cluster name")
	})

	t.Run("OIDC Provider", func(t *testing.T) {
		oidcProviderArn := terraform.Output(t, terraformOptions, "oidc_provider_arn")
		oidcProviderUrl := terraform.Output(t, terraformOptions, "oidc_provider_url")
		
		assert.NotEmpty(t, oidcProviderArn, "OIDC provider ARN should not be empty")
		assert.NotEmpty(t, oidcProviderUrl, "OIDC provider URL should not be empty")
	})

	t.Run("IRSA Roles", func(t *testing.T) {
		clusterAutoscalerRoleArn := terraform.Output(t, terraformOptions, "cluster_autoscaler_role_arn")
		awsLbControllerRoleArn := terraform.Output(t, terraformOptions, "aws_load_balancer_controller_role_arn")
		ebsCsiDriverRoleArn := terraform.Output(t, terraformOptions, "ebs_csi_driver_role_arn")
		
		assert.NotEmpty(t, clusterAutoscalerRoleArn, "Cluster autoscaler role ARN should not be empty")
		assert.NotEmpty(t, awsLbControllerRoleArn, "AWS LB controller role ARN should not be empty")
		assert.NotEmpty(t, ebsCsiDriverRoleArn, "EBS CSI driver role ARN should not be empty")
		
		assert.Contains(t, clusterAutoscalerRoleArn, "cluster-autoscaler-role", "Role ARN should contain expected name")
		assert.Contains(t, awsLbControllerRoleArn, "aws-load-balancer-controller-role", "Role ARN should contain expected name")
		assert.Contains(t, ebsCsiDriverRoleArn, "ebs-csi-driver-role", "Role ARN should contain expected name")
	})

	t.Run("Node Group", func(t *testing.T) {
		nodeGroupArn := terraform.Output(t, terraformOptions, "node_group_arn")
		nodeGroupStatus := terraform.Output(t, terraformOptions, "node_group_status")
		
		assert.NotEmpty(t, nodeGroupArn, "Node group ARN should not be empty")
		assert.Equal(t, "ACTIVE", nodeGroupStatus, "Node group should be active")
	})
}

func TestEKSModuleMinimalConfig(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"cluster_name":       "test-minimal-eks",
			"public_subnet_ids":  []string{"subnet-12345"},
			"private_subnet_ids": []string{"subnet-abcde"},
			"kms_key_arn":        "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012",
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("Default Values", func(t *testing.T) {
		clusterId := terraform.Output(t, terraformOptions, "cluster_id")
		assert.NotEmpty(t, clusterId, "Cluster should be created with default values")
	})
}