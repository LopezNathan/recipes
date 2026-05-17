output "public_ip" {
  description = "Static public IP of the recipes server"
  value       = google_compute_address.static.address
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh ubuntu@${google_compute_address.static.address}"
}

output "url" {
  description = "Public URL of the recipes app"
  value       = "https://${var.subdomain}.${data.cloudflare_zone.domain.name}"
}

