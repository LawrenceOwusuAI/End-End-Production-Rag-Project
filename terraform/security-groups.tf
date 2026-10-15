# SECURITY GROUP: INTERNAL KUBERNETES COMMUNICATION
resource "aws_security_group" "cluster_internal" {
  name        = "rag-k8s-cluster-internal"
  description = "Internal communication between Kubernetes nodes"
  vpc_id      = aws_vpc.k8s_vpc.id

  tags = {
    Name = "rag-k8s-cluster-internal"
  }
}

# Allow all traffic between nodes that use this SG
resource "aws_vpc_security_group_ingress_rule" "cluster_internal" {
  security_group_id            = aws_security_group.cluster_internal.id
  referenced_security_group_id = aws_security_group.cluster_internal.id
  ip_protocol                  = "-1"
  description                  = "Allow all internal Kubernetes node communication"
}

# Allow all outbound traffic
resource "aws_vpc_security_group_egress_rule" "cluster_internal_outbound" {
  security_group_id = aws_security_group.cluster_internal.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Allow outbound traffic"
}

# SECURITY GROUP: CONTROL PLANE PUBLIC ACCESS
resource "aws_security_group" "control_plane_public" {
  name        = "rag-k8s-control-plane-public"
  description = "Public access rules for Kubernetes control plane"
  vpc_id      = aws_vpc.k8s_vpc.id

  tags = {
    Name = "rag-k8s-control-plane-public"
  }
}

# SSH to control plane
resource "aws_vpc_security_group_ingress_rule" "control_plane_ssh" {
  security_group_id = aws_security_group.control_plane_public.id
  cidr_ipv4         = var.admin_cidr
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  description       = "SSH from administrator IP"
}

# Kubernetes API Server
resource "aws_vpc_security_group_ingress_rule" "kubernetes_api" {
  security_group_id = aws_security_group.control_plane_public.id
  cidr_ipv4         = var.admin_cidr
  from_port         = 6443
  to_port           = 6443
  ip_protocol       = "tcp"
  description       = "Kubernetes API access from administrator IP"
}

# SECURITY GROUP: WORKER NODE PUBLIC ACCESS
resource "aws_security_group" "worker_public" {
  name        = "rag-k8s-worker-public"
  description = "Public access rules for Kubernetes worker nodes"
  vpc_id      = aws_vpc.k8s_vpc.id
  tags = {
    Name = "rag-k8s-worker-public"
  }
}

# SSH to workers
resource "aws_vpc_security_group_ingress_rule" "worker_ssh" {
  security_group_id = aws_security_group.worker_public.id
  cidr_ipv4         = var.admin_cidr
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  description       = "SSH from administrator IP"
}

# HTTP
resource "aws_vpc_security_group_ingress_rule" "worker_http" {
  security_group_id = aws_security_group.worker_public.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "HTTP traffic"
}

# HTTPS
resource "aws_vpc_security_group_ingress_rule" "worker_https" {
  security_group_id = aws_security_group.worker_public.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "HTTPS traffic"
}

# Kubernetes NodePort range
resource "aws_vpc_security_group_ingress_rule" "worker_nodeport" {
  security_group_id = aws_security_group.worker_public.id
  cidr_ipv4         = var.admin_cidr
  from_port         = 30000
  to_port           = 32767
  ip_protocol       = "tcp"
  description       = "Kubernetes NodePort access from administrator IP"
}