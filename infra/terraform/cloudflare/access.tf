# Cloudflare Access in front of the owner-only seller tool (ADR-007). functions/_middleware.js
# verifies the Access JWT against ACCESS_TEAM_DOMAIN and ACCESS_AUD and answers 503 when
# either is missing, so the application's audience (aud) is load-bearing: a recreated
# application has a new one and the tool is closed until ACCESS_AUD is set again. Hence the
# application is never replaced by accident (prevent_destroy) and its aud is an output to
# compare with the binding.

# The one-time PIN: a code sent by email, no external identity provider to depend on.
resource "cloudflare_zero_trust_access_identity_provider" "one_time_pin" {
  account_id = var.account_id
  name       = "One-time PIN"
  type       = "onetimepin"
  config     = {}

  lifecycle {
    prevent_destroy = true
  }
}

# Allow exactly one address. Never an email domain: a domain rule would let in everyone
# who can mint an address there.
resource "cloudflare_zero_trust_access_policy" "owner_only" {
  account_id = var.account_id
  name       = "Owner only"
  decision   = "allow"

  include = [{
    email = { email = var.owner_email }
  }]

  lifecycle {
    prevent_destroy = true
  }
}

# /seller and /seller/*, on production and on every preview hostname. A path ending /* does
# not cover its parent, so the bare path is listed too (ops.md).
resource "cloudflare_zero_trust_access_application" "seller" {
  account_id       = var.account_id
  name             = "leaving-denver seller"
  type             = "self_hosted"
  session_duration = "24h"

  destinations = [
    { type = "public", uri = "leaving-denver.pages.dev/seller" },
    { type = "public", uri = "leaving-denver.pages.dev/seller/*" },
    { type = "public", uri = "*.leaving-denver.pages.dev/seller" },
    { type = "public", uri = "*.leaving-denver.pages.dev/seller/*" },
  ]

  allowed_idps = [cloudflare_zero_trust_access_identity_provider.one_time_pin.id]

  policies = [{
    id         = cloudflare_zero_trust_access_policy.owner_only.id
    precedence = 1
  }]

  lifecycle {
    prevent_destroy = true
  }
}
