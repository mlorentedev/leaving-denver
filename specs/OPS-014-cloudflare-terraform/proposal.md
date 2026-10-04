---
id: "OPS-014-cloudflare-terraform"
type: spec
status: draft # draft | implementing | verifying | archived
created: "2026-10-03"
issue: "mlorentedev/leaving-denver#178"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
wip_override: "owner-requested infrastructure change; the open specs are verifying, not stalled (15 active, limit 10, 2026-10-03)"
---

# OPS-014-cloudflare-terraform

## Why

<!-- from issue #178: OPS-014: Manage the Cloudflare configuration with Terraform -->

The Pages project, its Web Analytics setting and the Access application in front of `/seller/` were
set up by clicking in the Cloudflare dashboard. `functions/_middleware.js` fails closed on the
Access audience and ADR-008 keeps the Pages name for good, yet nothing in the repository can show
what is configured, rebuild it, or tell when it drifts. Owner decision of 2026-10-03: manage it
with Terraform, local gitignored state (it holds the owner's email), driven from the Makefile.

## What

- `infra/terraform/cloudflare/`: the Pages project (existence and production branch only, not
  destroyable), the Access one-time PIN provider, the self-hosted application for `/seller` and
  `/seller/*` on production and preview hostnames, and the Allow policy for exactly the owner's
  email, each adopted by an `import` block.
- `make infra-init|infra-ids|infra-plan|infra-apply|infra-fmt`. The token and the email reach
  Terraform from sops through its environment. `infra-apply` applies only a saved plan and refuses
  in CI. `make check` runs fmt and validate when Terraform is installed; CI installs it.
- ADR-012, runbook (ops, decommission), README and architecture updates, and a lesson.

## Out of scope

- Web Analytics (the Pages setting stays ADR-005's; the site cannot be read with the available
  token), the Pages deployment configuration and the `ACCESS_*` bindings (wrangler and the
  dashboard own them), the Zero Trust organization, the n8n metrics token.
- Running `apply`, or creating or changing any Cloudflare resource.
- Moving `integrations/n8n/` (it is an import artifact, not infrastructure).

## Risks / open questions

- The repository's deploy token has no Access scope: the Access resources cannot be planned from
  here. The first plan is the owner's, with a new token (ADR-012). Resolved by stating it, by
  `make infra-ids` refusing a token that cannot read Access, and by the runbook's reconcile loop.
- Access lists are empty, not forbidden, for a token without scope (lesson-030).

## Acceptance criteria

- [ ] AC1: no email or token-looking string in any `.tf` or `tfvars` file, and state, plans,
  variable files, `.terraform/` and crash logs are ignored by git.
- [ ] AC2: `make infra-*` give Terraform the token and the email through its environment, never on
  argv or in the output, and stop before Terraform when a secret is missing.
- [ ] AC3: `infra-apply` applies only the saved plan, refuses in CI, applies an import-only plan,
  needs `CHANGES=1` for a real change (not for a sensitivity-only update), `DESTROY=1` for a plan that only deletes, and never applies a replacement.
- [ ] AC4: `make check` fails on Terraform that does not format or validate, and only skips, with a
  notice, when Terraform is not installed.
- [ ] AC5: every managed resource has an import block; the Pages project is protected from
  destruction and its deployment configuration is ignored.
- [ ] AC6: `make infra-ids` refuses a token that cannot read Access and stops unless each object is
  found exactly once.
- [ ] AC7: the Pages project plans as `1 to import, 0 to add, 0 to change, 0 to destroy` against
  the live one (read-only plan with the deploy token).
- [ ] AC8: ADR, runbooks and README say how to set it up, what stays manual, and how the sale ends.

## References

- Bitácora board: issue #178
- ADR-012, ADR-005, ADR-007, ADR-008; `docs/runbooks/ops.md`, `docs/runbooks/decommission.md`
