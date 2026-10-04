# Cloudflare Access in front of the owner-only seller tool (ADR-007). functions/_middleware.js
# verifies the Access JWT against ACCESS_TEAM_DOMAIN and ACCESS_AUD and answers 503 when
# either is missing, so the application's audience (aud) is load-bearing: a recreated
# application has a new one and the tool is closed until ACCESS_AUD is set again. Hence the
# application is never replaced by accident (prevent_destroy) and its aud is an output to
# compare with the binding.

# The one-time PIN: a code sent by email, no external identity provider to depend on.
resource "cloudflare_zero_trust_access_identity_provider" "one_time_pin" {
  account_id = var.account_id
  name       = ""
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
  name       = "owner-only"
  decision   = "allow"

  include = [{
    email = { email = var.owner_email }
  }]

  # The API answers an empty rdp block for every policy; declaring it keeps the plan quiet.
  connection_rules = { rdp = {} }

  lifecycle {
    prevent_destroy = true
  }
}

# /seller and /seller/*, on production and on every preview hostname. A path ending /* does
# not cover its parent, so the bare path is listed too (ops.md).
#
# Known open exposure (issue #184): the dashboard allowed every identity provider
# (`allowed_idps` unset) and set the cookie without HttpOnly. They are left as they are so the
# first apply only imports. Tighten both in a separate apply (`make infra-apply CHANGES=1`):
# allowed_idps = [the one-time PIN provider above], http_only_cookie_attribute = true.
resource "cloudflare_zero_trust_access_application" "seller" {
  account_id       = var.account_id
  name             = "leaving-denver.pages.dev"
  type             = "self_hosted"
  session_duration = "24h"

  # The values the dashboard created; declared so the first plan imports without a change.
  auto_redirect_to_identity  = false
  enable_binding_cookie      = false
  http_only_cookie_attribute = false
  options_preflight_bypass   = false

  destinations = [
    { type = "public", uri = "leaving-denver.pages.dev/seller" },
    { type = "public", uri = "leaving-denver.pages.dev/seller/*" },
    { type = "public", uri = "*.leaving-denver.pages.dev/seller" },
    { type = "public", uri = "*.leaving-denver.pages.dev/seller/*" },
  ]

  policies = [{
    id         = cloudflare_zero_trust_access_policy.owner_only.id
    precedence = 1
  }]

  lifecycle {
    prevent_destroy = true
  }
}
