provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Production-Grade-Rag"
      Environment = "development"
      ManagedBy   = "Terraform"
    }
  }
}