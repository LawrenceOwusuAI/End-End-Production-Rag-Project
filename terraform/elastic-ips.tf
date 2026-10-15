# CONTROL PLANE ELASTIC IP
resource "aws_eip" "control_plane" {
  domain = "vpc"
  tags = {
    Name = "control-plane-node-eip"
  }
}

resource "aws_eip_association" "control_plane" {
  instance_id   = aws_instance.control_plane.id
  allocation_id = aws_eip.control_plane.id
}


# ============================================================
# WORKER NODE 1 ELASTIC IP
# ============================================================

resource "aws_eip" "worker_1" {
  domain = "vpc"

  tags = {
    Name = "worker-node-1-eip"
  }
}


resource "aws_eip_association" "worker_1" {
  instance_id   = aws_instance.worker_1.id
  allocation_id = aws_eip.worker_1.id
}


# ============================================================
# WORKER NODE 2 ELASTIC IP
# ============================================================

resource "aws_eip" "worker_2" {
  domain = "vpc"

  tags = {
    Name = "worker-node-2-eip"
  }
}


resource "aws_eip_association" "worker_2" {
  instance_id   = aws_instance.worker_2.id
  allocation_id = aws_eip.worker_2.id
}