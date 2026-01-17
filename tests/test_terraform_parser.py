"""Tests for the Terraform HCL parser."""

import os
import tempfile
from pathlib import Path

import pytest

from infrastructure_diagram_mcp_server.parsers.terraform_parser import (
    TerraformParser,
    TerraformParseResult,
    TerraformResource,
    TerraformDataSource,
    TerraformModule,
    TerraformProvider,
)


# Get the path to test resources
RESOURCES_DIR = Path(__file__).parent / 'resources' / 'terraform'


class TestTerraformParserBasics:
    """Test basic Terraform parser functionality."""

    def test_parse_inline_hcl(self):
        """Test parsing inline HCL content."""
        hcl_content = """
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t3.micro"

  tags = {
    Name = "web-server"
  }
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert not result.errors
        assert len(result.resources) == 1
        assert result.resources[0].resource_type == 'aws_instance'
        assert result.resources[0].name == 'web'
        assert result.resources[0].provider == TerraformProvider.AWS

    def test_parse_file(self):
        """Test parsing a .tf file."""
        file_path = RESOURCES_DIR / 'main.tf'
        if not file_path.exists():
            pytest.skip('Test resource file not found')

        parser = TerraformParser()
        result = parser.parse(str(file_path))

        assert not result.errors
        assert len(result.resources) > 0

    def test_parse_directory(self):
        """Test parsing all .tf files in a directory."""
        if not RESOURCES_DIR.exists():
            pytest.skip('Test resources directory not found')

        parser = TerraformParser()
        result = parser.parse(str(RESOURCES_DIR))

        assert not result.errors
        assert len(result.resources) > 0

    def test_parse_directory_recursive(self):
        """Test recursive parsing of .tf files in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            subdir = os.path.join(tmpdir, 'modules', 'vpc')
            os.makedirs(subdir)

            # Create main.tf at root
            with open(os.path.join(tmpdir, 'main.tf'), 'w') as f:
                f.write('''
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
''')

            # Create module file in subdirectory
            with open(os.path.join(subdir, 'main.tf'), 'w') as f:
                f.write('''
resource "aws_subnet" "public" {
  vpc_id     = var.vpc_id
  cidr_block = "10.0.1.0/24"
}
''')

            parser = TerraformParser()
            result = parser.parse(tmpdir)

            assert not result.errors
            # Should find resources from both files
            assert len(result.resources) >= 2

            resource_types = {r.resource_type for r in result.resources}
            assert 'aws_vpc' in resource_types
            assert 'aws_subnet' in resource_types

    def test_parse_invalid_hcl(self):
        """Test parsing invalid HCL returns error."""
        invalid_hcl = """
this is not valid HCL {
  missing = proper
    structure
}
"""
        parser = TerraformParser()
        result = parser.parse(invalid_hcl)

        # Should have errors
        assert result.errors or len(result.resources) == 0

    def test_parse_empty_input(self):
        """Test parsing empty input returns no errors."""
        parser = TerraformParser()
        result = parser.parse('')

        # Empty input may parse cwd directory or return empty results
        # The important thing is no errors
        assert not result.errors


class TestTerraformProviderDetection:
    """Test provider detection from resource types."""

    @pytest.mark.parametrize('resource_type,expected_provider', [
        ('aws_instance', TerraformProvider.AWS),
        ('aws_s3_bucket', TerraformProvider.AWS),
        ('aws_lambda_function', TerraformProvider.AWS),
        ('google_compute_instance', TerraformProvider.GCP),
        ('google_storage_bucket', TerraformProvider.GCP),
        ('azurerm_virtual_machine', TerraformProvider.AZURE),
        ('azurerm_storage_account', TerraformProvider.AZURE),
        ('kubernetes_deployment', TerraformProvider.KUBERNETES),
        ('kubernetes_service', TerraformProvider.KUBERNETES),
    ])
    def test_provider_detection(self, resource_type, expected_provider):
        """Test correct provider detection from resource type prefix."""
        hcl_content = f"""
resource "{resource_type}" "test" {{
  name = "test"
}}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 1
        assert result.resources[0].provider == expected_provider
        assert expected_provider in result.providers_used

    def test_unknown_provider(self):
        """Test handling of unknown provider prefixes."""
        hcl_content = """
resource "unknown_resource" "test" {
  name = "test"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 1
        # Unknown providers default to GENERIC
        assert result.resources[0].provider == TerraformProvider.GENERIC

    def test_multiple_providers(self):
        """Test parsing resources from multiple providers."""
        hcl_content = """
resource "aws_instance" "web" {
  ami = "ami-12345"
}

resource "google_compute_instance" "server" {
  name = "server"
}

resource "azurerm_virtual_machine" "vm" {
  name = "vm"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 3
        providers = {r.provider for r in result.resources}
        assert TerraformProvider.AWS in providers
        assert TerraformProvider.GCP in providers
        assert TerraformProvider.AZURE in providers


class TestTerraformRelationshipDetection:
    """Test relationship detection between Terraform resources."""

    def test_explicit_depends_on(self):
        """Test explicit depends_on relationship detection."""
        hcl_content = """
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"

  depends_on = [aws_vpc.main]
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 2

        # Find subnet resource
        subnet = next(r for r in result.resources if r.resource_type == 'aws_subnet')
        # depends_on may include ${} wrapper
        assert any('aws_vpc.main' in dep for dep in subnet.depends_on)

    def test_implicit_reference_relationship(self):
        """Test implicit relationship via resource references."""
        hcl_content = """
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
}

resource "aws_instance" "web" {
  subnet_id = aws_subnet.public.id
  ami       = "ami-12345"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 3
        # Relationships should be detected
        assert len(result.relationships) >= 2

    def test_security_group_relationship(self):
        """Test security group to VPC relationship."""
        hcl_content = """
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_security_group" "web" {
  vpc_id = aws_vpc.main.id
  name   = "web-sg"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 2
        assert len(result.relationships) >= 1


class TestTerraformDataSources:
    """Test data source parsing."""

    def test_parse_data_source(self):
        """Test parsing data blocks."""
        hcl_content = """
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.data_sources) == 1
        assert result.data_sources[0].data_type == 'aws_ami'
        assert result.data_sources[0].name == 'ubuntu'
        assert result.data_sources[0].provider == TerraformProvider.AWS

    def test_multiple_data_sources(self):
        """Test parsing multiple data sources."""
        hcl_content = """
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "google_project" "project" {}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.data_sources) == 3


class TestTerraformModules:
    """Test module block parsing."""

    def test_parse_module(self):
        """Test parsing module blocks."""
        hcl_content = """
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "my-vpc"
  cidr = "10.0.0.0/16"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.modules) == 1
        assert result.modules[0].name == 'vpc'
        assert result.modules[0].source == 'terraform-aws-modules/vpc/aws'

    def test_local_module(self):
        """Test parsing local module references."""
        hcl_content = """
module "network" {
  source = "./modules/network"

  vpc_cidr = "10.0.0.0/16"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.modules) == 1
        assert result.modules[0].source == './modules/network'

    def test_multiple_modules(self):
        """Test parsing multiple module blocks."""
        hcl_content = """
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
}

module "eks" {
  source = "terraform-aws-modules/eks/aws"
}

module "rds" {
  source = "./modules/rds"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.modules) == 3


class TestTerraformResourceTypes:
    """Test parsing of various AWS resource types."""

    @pytest.mark.parametrize('resource_type', [
        'aws_instance',
        'aws_vpc',
        'aws_subnet',
        'aws_security_group',
        'aws_s3_bucket',
        'aws_lambda_function',
        'aws_rds_cluster',
        'aws_dynamodb_table',
        'aws_iam_role',
        'aws_ecs_cluster',
    ])
    def test_aws_resources(self, resource_type):
        """Test parsing various AWS resource types."""
        hcl_content = f"""
resource "{resource_type}" "test" {{
  name = "test"
}}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 1
        assert result.resources[0].resource_type == resource_type
        assert result.resources[0].provider == TerraformProvider.AWS


class TestTerraformVariablesAndOutputs:
    """Test handling of variables and outputs."""

    def test_variables_not_parsed_as_resources(self):
        """Test that variable blocks are not parsed as resources."""
        hcl_content = """
variable "region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "environment" {
  type = string
}

resource "aws_instance" "web" {
  ami = "ami-12345"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        # Only the aws_instance should be a resource
        assert len(result.resources) == 1
        assert result.resources[0].resource_type == 'aws_instance'

    def test_outputs_not_parsed_as_resources(self):
        """Test that output blocks are not parsed as resources."""
        hcl_content = """
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "vpc_cidr" {
  value = aws_vpc.main.cidr_block
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        # Only the aws_vpc should be a resource
        assert len(result.resources) == 1


class TestTerraformParserEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_resource_block(self):
        """Test handling empty resource blocks."""
        hcl_content = """
resource "aws_instance" "empty" {
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 1

    def test_nested_blocks(self):
        """Test parsing resources with nested blocks."""
        hcl_content = """
resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = "vpc-12345"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 1
        assert result.resources[0].resource_type == 'aws_security_group'

    def test_heredoc_strings(self):
        """Test parsing HCL with heredoc strings."""
        hcl_content = """
resource "aws_iam_role" "lambda" {
  name = "lambda-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Action": "sts:AssumeRole",
    "Effect": "Allow",
    "Principal": {
      "Service": "lambda.amazonaws.com"
    }
  }]
}
EOF
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        assert len(result.resources) == 1
        assert result.resources[0].resource_type == 'aws_iam_role'

    def test_qualified_name_format(self):
        """Test that qualified names are formatted correctly."""
        hcl_content = """
resource "aws_instance" "web" {
  ami = "ami-12345"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        resource = result.resources[0]
        assert resource.qualified_name == 'aws_instance.web'

    def test_provider_block_ignored(self):
        """Test that provider blocks don't create resources."""
        hcl_content = """
provider "aws" {
  region = "us-east-1"
}

provider "google" {
  project = "my-project"
}

resource "aws_instance" "web" {
  ami = "ami-12345"
}
"""
        parser = TerraformParser()
        result = parser.parse(hcl_content)

        # Only the aws_instance should be a resource
        assert len(result.resources) == 1


class TestTerraformParserIntegration:
    """Integration tests with the test resources."""

    def test_parse_full_terraform_config(self):
        """Test parsing the full test Terraform configuration."""
        file_path = RESOURCES_DIR / 'main.tf'
        if not file_path.exists():
            pytest.skip('Test resource file not found')

        parser = TerraformParser()
        result = parser.parse(str(file_path))

        assert not result.errors

        # Should have multiple resources
        assert len(result.resources) >= 5

        # Should detect relationships
        assert len(result.relationships) >= 1

        # Should have data sources
        assert len(result.data_sources) >= 1

        # Should have modules
        assert len(result.modules) >= 1

        # Should detect AWS provider
        assert TerraformProvider.AWS in result.providers_used
