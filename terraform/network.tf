# VPC
resource "aws_vpc" "k8s_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "rag-kubernetes-vpc"
  }
}

# INTERNET GATEWAY
resource "aws_internet_gateway" "k8s_igw" {
  vpc_id = aws_vpc.k8s_vpc.id
  tags = {
    Name = "rag-kubernetes-igw"
  }
}

# PUBLIC SUBNET
resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.k8s_vpc.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "rag-kubernetes-public-subnet"
  }
}

# PUBLIC ROUTE TABLE
resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.k8s_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.k8s_igw.id
  }

  tags = {
    Name = "rag-kubernetes-public-route-table"
  }
}

# ASSOCIATE ROUTE TABLE WITH PUBLIC SUBNET
resource "aws_route_table_association" "public_subnet" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_route_table.id
}