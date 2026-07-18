# Bootstrap stack: the resources that grant CI its own access (WIF pool,
# github-ci service account, IAM bindings). Kept in a separate state from the
# app stack so the CI-applied state never contains IAM resources — github-ci
# has no IAM permissions and must never need to read or write these.
# Applied manually by an admin (locally, with GOOGLE_APPLICATION_CREDENTIALS).

terraform {
  backend "gcs" {
    bucket = "recipes-496402-tfstate"
    prefix = "bootstrap"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  required_version = ">= 1.5"
}

provider "google" {
  project = var.project_id
  region  = "us-east1"
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "recipes-496402"
}
