variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "Availability zone for the Kubernetes nodes"
  type        = string
  default     = "us-east-1a"
}

variable "vpc_cidr" {
  description = "CIDR block for the Kubernetes VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the Kubernetes public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "control_plane_instance_type" {
  description = "EC2 instance type for the Kubernetes control plane"
  type        = string
  default     = "t3.medium"
}

variable "worker_instance_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
  default     = "t3.large"
}

variable "key_name" {
  description = "Name of an EXISTING AWS EC2 key pair"
  type        = string
}

variable "admin_cidr" {
  description = "Your public IP address in CIDR notation, e.g. 70.20.30.40/32"
  type        = string
}

variable "private_key_path" {
  description = "Local path to the private key used to SSH into EC2"
  type        = string
}