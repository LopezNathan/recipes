provider "google" {
  credentials = var.credentials_file != "" ? file(var.credentials_file) : null
  project     = var.project_id
  region      = var.region
  zone        = var.zone
}
