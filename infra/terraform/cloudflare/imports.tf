# Adopt what was clicked in the dashboard before Terraform existed. Once an object is in state
# its import block is a no-op, so these stay: they are also how a lost state file is rebuilt
# (`make infra-ids && make infra-plan`). They go with their resource when it is removed
# (docs/runbooks/decommission.md). The ids are variables (ids.auto.tfvars, from `make infra-ids`).

import {
  to = cloudflare_pages_project.site
  id = "${var.account_id}/${var.project_name}"
}

import {
  to = cloudflare_zero_trust_access_identity_provider.one_time_pin
  id = "accounts/${var.account_id}/${var.access_idp_id}"
}

import {
  to = cloudflare_zero_trust_access_policy.owner_only
  id = "${var.account_id}/${var.access_policy_id}"
}

import {
  to = cloudflare_zero_trust_access_application.seller
  id = "accounts/${var.account_id}/${var.access_app_id}"
}
