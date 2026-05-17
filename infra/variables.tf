variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region — must be us-west1, us-central1, or us-east1 for free tier"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone within the region (e.g. us-central1-a)"
  type        = string
  default     = "us-central1-a"
}

variable "credentials_file" {
  description = "Path to a GCP service account JSON key (optional; leave empty to use application default credentials)"
  type        = string
  default     = ""
}

variable "ssh_public_key" {
  description = "SSH public key string to authorize on the instance (e.g. contents of ~/.ssh/id_ed25519.pub)"
  type        = string
}

variable "repo_url" {
  description = "Git repo URL (e.g. https://github.com/you/recipes.git)"
  type        = string
}

variable "github_token" {
  description = "GitHub fine-grained PAT with Contents: read for the repo (needed if repo is private)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "db_password" {
  description = "Password for the PostgreSQL recipes user"
  type        = string
  sensitive   = true
}
