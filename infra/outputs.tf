output "public_ip" {
  description = "Public IP of the recipes server"
  value       = google_compute_instance.app.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh ubuntu@${google_compute_instance.app.network_interface[0].access_config[0].nat_ip}"
}
