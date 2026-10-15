
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name = "name"

    values = [
      "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
    ]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# CONTROL PLANE NODE
resource "aws_instance" "control_plane" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.control_plane_instance_type

  subnet_id = aws_subnet.public_subnet.id

  vpc_security_group_ids = [
    aws_security_group.cluster_internal.id,
    aws_security_group.control_plane_public.id
  ]

  key_name = var.key_name

  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "control-plane-node"
    Role = "control-plane"
  }
}

# COPY SCRIPTS TO CONTROL PLANE
resource "null_resource" "copy_control_plane_scripts" {

  depends_on = [
    aws_instance.control_plane,
    aws_eip_association.control_plane
  ]

  connection {
    type        = "ssh"
    user        = "ubuntu"
    host        = aws_eip.control_plane.public_ip
    private_key = file(var.private_key_path)
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/scripts/common-scripts.sh"
    destination = "/home/ubuntu/common-scripts.sh"
  }

  provisioner "file" {
    source      = "${path.module}/scripts/control-plane-node.sh"
    destination = "/home/ubuntu/control-plane-node.sh"
  }

  provisioner "file" {
    source      = "${path.module}/scripts/control-plane-post-setup.sh"
    destination = "/home/ubuntu/control-plane-post-setup.sh"
  }
}

# WORKER NODE 1
resource "aws_instance" "worker_1" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.worker_instance_type
  subnet_id = aws_subnet.public_subnet.id

  vpc_security_group_ids = [
    aws_security_group.cluster_internal.id,
    aws_security_group.worker_public.id
  ]

  key_name = var.key_name

  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 40
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "worker-node-1"
    Role = "worker"
  }
}

# COPY COMMON SCRIPT TO WORKER NODE 1
resource "null_resource" "copy_worker_1_script" {

  depends_on = [
    aws_instance.worker_1,
    aws_eip_association.worker_1
  ]

  connection {
    type        = "ssh"
    user        = "ubuntu"
    host        = aws_eip.worker_1.public_ip
    private_key = file(var.private_key_path)
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/scripts/common-scripts.sh"
    destination = "/home/ubuntu/common-scripts.sh"
  }
}

# WORKER NODE 2
resource "aws_instance" "worker_2" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.worker_instance_type

  subnet_id = aws_subnet.public_subnet.id

  vpc_security_group_ids = [
    aws_security_group.cluster_internal.id,
    aws_security_group.worker_public.id
  ]

  key_name = var.key_name

  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 40
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "worker-node-2"
    Role = "worker"
  }
}

# COPY COMMON SCRIPT TO WORKER NODE 2
resource "null_resource" "copy_worker_2_script" {

  depends_on = [
    aws_instance.worker_2,
    aws_eip_association.worker_2
  ]

  connection {
    type        = "ssh"
    user        = "ubuntu"
    host        = aws_eip.worker_2.public_ip
    private_key = file(var.private_key_path)
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/scripts/common-scripts.sh"
    destination = "/home/ubuntu/common-scripts.sh"
  }
}