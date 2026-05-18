resource "cloudflare_zero_trust_tunnel_cloudflared" "private" {
  account_id = var.cloudflare_account_id
  name       = "recipes-private"
  config_src = "cloudflare"
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "private" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.private.id

  config = {
    ingress = [
      {
        hostname = "${var.private_subdomain}.${data.cloudflare_zone.domain.name}"
        service  = "http://localhost:8001"
      },
      {
        service = "http_status:404"
      }
    ]
  }
}

resource "cloudflare_dns_record" "private" {
  zone_id = var.cloudflare_zone_id
  name    = var.private_subdomain
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.private.id}.cfargotunnel.com"
  ttl     = 1
  proxied = true
}
