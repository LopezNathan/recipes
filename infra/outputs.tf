output "public_ip" {
  description = "Static public IP of the recipes server"
  value       = google_compute_address.static.address
  # The DNS record is Cloudflare-proxied, so the origin IP is not public
  # knowledge — keep it out of terraform output listings and CI logs.
  sensitive = true
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "gcloud compute ssh ${google_compute_instance.app.name} --zone=${var.zone}"
}

output "url" {
  description = "Public URL of the recipes app"
  value       = "https://${var.subdomain}.${data.cloudflare_zone.domain.name}"
}

output "private_url" {
  description = "Private API URL via Cloudflare Tunnel"
  value       = "https://${var.private_subdomain}.${data.cloudflare_zone.domain.name}"
}

