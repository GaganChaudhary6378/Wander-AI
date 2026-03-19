output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Elastic IP attached to the instance (use this for SSH and deploy)"
  value       = aws_eip.app.public_ip
}

output "ssh_command" {
  description = "Example SSH command (use your private key path)"
  value       = "ssh -i ~/.ssh/verifact-key ec2-user@${aws_eip.app.public_ip}"
}

output "app_url" {
  description = "WanderAI Streamlit app URL"
  value       = "http://${aws_eip.app.public_ip}:8501"
}
