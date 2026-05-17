provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

data "cloudflare_zone" "domain" {
  zone_id = var.cloudflare_zone_id
}

resource "cloudflare_dns_record" "recipes" {
  zone_id = var.cloudflare_zone_id
  name    = var.subdomain
  type    = "A"
  content = google_compute_address.static.address
  ttl     = 1
  proxied = true
}

resource "cloudflare_zone_setting" "ssl" {
  zone_id    = var.cloudflare_zone_id
  setting_id = "ssl"
  value      = "flexible"
}
