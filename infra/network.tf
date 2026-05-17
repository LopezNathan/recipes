resource "google_compute_network" "main" {
  name                    = "recipes-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "recipes-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.main.id
}

resource "google_compute_firewall" "ssh" {
  name    = "recipes-allow-ssh"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "http_https" {
  name    = "recipes-allow-http-https"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8001"]
  }

  source_ranges = ["0.0.0.0/0"]
}
