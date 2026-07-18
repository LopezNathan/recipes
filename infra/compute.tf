resource "google_compute_address" "static" {
  name   = "recipes-ip"
  region = var.region
}

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
    access_config {
      nat_ip = google_compute_address.static.address
    }
  }

  metadata = {
    ssh-keys = "ubuntu:${var.ssh_public_key}"
    # Guest agent publishes SSH host keys to guest attributes at boot so
    # `gcloud compute ssh` can verify the host via the API instead of a
    # pinned known_hosts entry that would go stale on every rebuild.
    enable-guest-attributes = "TRUE"
    user-data = templatefile("${path.module}/cloud-init.yaml.tpl", {
      repo_url     = var.repo_url
      database_url = var.database_url
      tunnel_token = var.tunnel_token
    })
  }
}
