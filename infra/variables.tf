variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "recipes-496402"
}

variable "region" {
  description = "GCP region — must be us-west1, us-central1, or us-east1 for free tier"
  type        = string
  default     = "us-east1"
}

variable "zone" {
  description = "GCP zone within the region (e.g. us-east1-c)"
  type        = string
  default     = "us-east1-c"
}

variable "credentials_file" {
  description = "Path to a GCP service account JSON key (optional; leave empty to use application default credentials)"
  type        = string
  default     = ""
}

variable "repo_url" {
  description = "Git repo URL (e.g. https://github.com/you/recipes.git)"
  type        = string
  default     = "https://github.com/LopezNathan/recipes.git"
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
  default     = "c403778a850d9f61a15dd8e7caf4646d"
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID (found on your domain's Overview page in the Cloudflare dashboard)"
  type        = string
  default     = "049d1b5391e9644e85d480bb94ce8054"
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

variable "owner_email" {
  description = "Email address allowed through Cloudflare Access (one-time PIN sent here)"
  type        = string
  default     = "contact@nathanlopez.com"
}
