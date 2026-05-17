resource "google_compute_instance" "app" {
  name         = "recipes-server"
  machine_type = "e2-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30
    }
  }

  network_interface {
    network    = google_compute_network.main.id
    subnetwork = google_compute_subnetwork.main.id
    access_config {}
  }

  metadata = {
    ssh-keys  = "ubuntu:${var.ssh_public_key}"
    user-data = templatefile("${path.module}/cloud-init.yaml.tpl", {
      repo_url    = var.github_token != "" ? replace(var.repo_url, "https://", "https://${var.github_token}@") : var.repo_url
      db_password = var.db_password
    })
  }
}
