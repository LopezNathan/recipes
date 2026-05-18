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

variable "database_url" {
  description = "Full Neon (or other) PostgreSQL connection string, e.g. postgresql://user:pass@host/db?sslmode=require"
  type        = string
  sensitive   = true
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token with Zone:DNS:Edit and Zero Trust:Edit permissions"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID (found on the right side of your domain's Overview page)"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID (found on your domain's Overview page in the Cloudflare dashboard)"
  type        = string
}

variable "subdomain" {
  description = "Subdomain for the public app (e.g. 'recipes' creates recipes.yourdomain.com)"
  type        = string
  default     = "recipes"
}

variable "private_subdomain" {
  description = "Subdomain for the private API via Cloudflare Tunnel (e.g. 'recipes-private')"
  type        = string
  default     = "recipes-private"
}

variable "tunnel_token" {
  description = "Cloudflare Tunnel token — get from dashboard after first apply: Zero Trust → Networks → Tunnels → [tunnel] → Configure"
  type        = string
  sensitive   = true
  default     = ""
}
