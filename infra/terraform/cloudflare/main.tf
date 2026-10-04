provider "cloudflare" {
  # The API token comes from CLOUDFLARE_API_TOKEN, set by the Makefile from sops for one
  # command. It is never a variable, a file or an argument.
}

# The Pages project. Terraform owns that it exists and which branch is production.
#
# wrangler.toml owns what a deployment is made of (build output, compatibility date and
# the bindings, among them the Analytics Engine one), and the dashboard owns the secret
# variables (ACCESS_TEAM_DOMAIN, ACCESS_AUD). `wrangler pages deploy` rewrites
# deployment_configs on every deploy, so a copy here would be reverted by CI and would in
# turn revert CI's. Hence ignore_changes: Terraform must not fight either of them.
#
# build_config is ignored for the same reason, and because it carries the Web Analytics
# beacon pair (web_analytics_tag, web_analytics_token) that the Pages setting writes
# (ADR-005). Web Analytics stays that setting; see ADR-012 for why it is not managed here.
resource "cloudflare_pages_project" "site" {
  account_id        = var.account_id
  name              = var.project_name
  production_branch = "main"

  lifecycle {
    # ADR-008: a deleted pages.dev name is free for anyone to claim, and every flyer and
    # listing still points at it. Ending Terraform's management is `terraform state rm`.
    prevent_destroy = true
    ignore_changes  = [build_config, deployment_configs, source]
  }
}
