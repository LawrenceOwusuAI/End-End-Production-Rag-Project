# PUBLIC IPS
output "control_plane_public_ip" {
  description = "Elastic IP of the Kubernetes control plane"
  value       = aws_eip.control_plane.public_ip
}

output "worker_1_public_ip" {
  description = "Elastic IP of worker node 1"
  value       = aws_eip.worker_1.public_ip
}

output "worker_2_public_ip" {
  description = "Elastic IP of worker node 2"
  value       = aws_eip.worker_2.public_ip
}

# PRIVATE IPS
output "control_plane_private_ip" {
  value = aws_instance.control_plane.private_ip
}

output "worker_1_private_ip" {
  value = aws_instance.worker_1.private_ip
}

output "worker_2_private_ip" {
  value = aws_instance.worker_2.private_ip
}

# INSTANCE IDS
output "control_plane_instance_id" {
  value = aws_instance.control_plane.id
}

output "worker_1_instance_id" {
  value = aws_instance.worker_1.id
}

output "worker_2_instance_id" {
  value = aws_instance.worker_2.id
}