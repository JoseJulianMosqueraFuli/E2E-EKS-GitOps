package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
)

func TestVPCModule(t *testing.T) {
	t.Parallel()

	// Define the Terraform options
	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		// Path to the Terraform code that will be tested
		TerraformDir: "../",

		// Variables to pass to our Terraform code using -var options
		Vars: map[string]interface{}{
			"name_prefix":           "test-vpc",
			"vpc_cidr":              "10.0.0.0/16",
			"public_subnet_count":   2,
			"private_subnet_count":  2,
			"enable_nat_gateway":    true,
		},

		// Disable colors in Terraform commands so its easier to parse stdout/stderr
		NoColor: true,
	})

	// Clean up resources with "terraform destroy" at the end of the test
	defer terraform.Destroy(t, terraformOptions)

	// Run "terraform init" and "terraform apply"
	terraform.InitAndApply(t, terraformOptions)

	// Run basic validation tests
	t.Run("VPC Creation", func(t *testing.T) {
		vpcId := terraform.Output(t, terraformOptions, "vpc_id")
		assert.NotEmpty(t, vpcId, "VPC ID should not be empty")
	})

	t.Run("Subnet Creation", func(t *testing.T) {
		publicSubnetIds := terraform.OutputList(t, terraformOptions, "public_subnet_ids")
		privateSubnetIds := terraform.OutputList(t, terraformOptions, "private_subnet_ids")
		
		assert.Len(t, publicSubnetIds, 2, "Should have 2 public subnets")
		assert.Len(t, privateSubnetIds, 2, "Should have 2 private subnets")
	})

	t.Run("Security Groups", func(t *testing.T) {
		eksClusterSgId := terraform.Output(t, terraformOptions, "eks_cluster_security_group_id")
		eksNodesSgId := terraform.Output(t, terraformOptions, "eks_nodes_security_group_id")
		vpcEndpointsSgId := terraform.Output(t, terraformOptions, "vpc_endpoints_security_group_id")
		
		assert.NotEmpty(t, eksClusterSgId, "EKS cluster security group ID should not be empty")
		assert.NotEmpty(t, eksNodesSgId, "EKS nodes security group ID should not be empty")
		assert.NotEmpty(t, vpcEndpointsSgId, "VPC endpoints security group ID should not be empty")
	})

	t.Run("VPC Endpoints", func(t *testing.T) {
		s3EndpointId := terraform.Output(t, terraformOptions, "s3_vpc_endpoint_id")
		ecrDkrEndpointId := terraform.Output(t, terraformOptions, "ecr_dkr_vpc_endpoint_id")
		ecrApiEndpointId := terraform.Output(t, terraformOptions, "ecr_api_vpc_endpoint_id")
		
		assert.NotEmpty(t, s3EndpointId, "S3 VPC endpoint ID should not be empty")
		assert.NotEmpty(t, ecrDkrEndpointId, "ECR DKR VPC endpoint ID should not be empty")
		assert.NotEmpty(t, ecrApiEndpointId, "ECR API VPC endpoint ID should not be empty")
	})
}

func TestVPCModuleWithoutNATGateway(t *testing.T) {
	t.Parallel()

	terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
		TerraformDir: "../",
		Vars: map[string]interface{}{
			"name_prefix":           "test-vpc-no-nat",
			"vpc_cidr":              "10.1.0.0/16",
			"public_subnet_count":   1,
			"private_subnet_count":  1,
			"enable_nat_gateway":    false,
		},
		NoColor: true,
	})

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	t.Run("NAT Gateway Disabled", func(t *testing.T) {
		natGatewayIds := terraform.OutputList(t, terraformOptions, "nat_gateway_ids")
		assert.Empty(t, natGatewayIds, "Should have no NAT gateways when disabled")
	})
}