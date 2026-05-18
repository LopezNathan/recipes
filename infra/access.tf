resource "cloudflare_zero_trust_access_policy" "private" {
  account_id = var.cloudflare_account_id
  name       = "Allow owner"
  decision   = "allow"

  include = [
    {
      email = {
        email = var.owner_email
      }
    }
  ]
}

resource "cloudflare_zero_trust_access_application" "private" {
  account_id       = var.cloudflare_account_id
  name             = "Recipes Private API"
  domain           = "${var.private_subdomain}.${data.cloudflare_zone.domain.name}"
  type             = "self_hosted"
  session_duration = "24h"

  policies = [{
    id         = cloudflare_zero_trust_access_policy.private.id
    precedence = 1
  }]
}
