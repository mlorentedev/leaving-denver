---
id: "ADR-012-cloudflare-configuration-as-terraform-with-local-state"
type: adr
status: accepted
owner: manu
date: "2026-10-03"
issue: "mlorentedev/leaving-denver#178"
tags: [architecture, decision, cloudflare, infrastructure, secrets]
created: "2026-10-03"
---

# ADR-012: Cloudflare Configuration as Terraform, With Local State

## Status

Accepted (owner decision of 2026-10-03). It amends the manual steps of:

- **ADR-007**: the Cloudflare Access application, its identity provider and its allow policy are
  created by `make infra-apply`, not by dashboard clicks. The runtime bindings and the middleware
  are unchanged.
- **ADR-005**: nothing changes in the decision (Web Analytics is the Pages setting, the repo ships
  no beacon). This ADR records that Terraform does not manage that setting, and why.

ADR-008 is unchanged and is enforced: the Pages project is protected from destruction.

## Date

2026-10-03

## Context

Three things in this account were set up by clicking in the Cloudflare dashboard: the Pages
project, the Web Analytics setting on it, and the Access application that keeps `/seller/` owner-only.
Two of them carry weight. `functions/_middleware.js` answers 503 unless Access passes the right
audience, and ADR-008 keeps the Pages name for good. Nothing in the repository could say what was
configured, rebuild it after a mistake, or show drift.

What was observed on 2026-10-03, read-only, with the repo's own deploy token:

- The Pages API returns the project (`production_branch: main`, `destination_dir: build/public`).
  It also holds two secret variables, `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD`, in both environments.
- The Access lists (`/access/apps`, `/access/identity_providers`, `/access/policies`) answer `200`
  with `[]`, while `/seller/` really does redirect to the Access login. The deploy token has no
  Access scope, and Cloudflare filters such a list to empty instead of refusing. Only
  `/access/organizations` answers `403`. "The list is empty" therefore proves nothing here
  (lesson-030).
- `GET /rum/site_info/list` answers `403` too: the Web Analytics site behind the Pages setting
  cannot be read with that token either.

## Decision

### 1. Terraform, state local and gitignored

The configuration is `infra/terraform/cloudflare/`, Terraform with the `cloudflare/cloudflare`
provider pinned to the current major (`~> 5.26`; `.terraform.lock.hcl` is committed). State is a
local file, never committed: it holds the owner's email, and this repository is public. A remote
backend would put a second store, and a second credential, in a repo that has one owner and a
sale that ends in five weeks.

Losing the state is not losing the infrastructure. The import blocks stay in the configuration, so
the next `make infra-plan` adopts what exists again.

### 2. What is managed

| Resource | Managed | Notes |
|---|---|---|
| Pages project `leaving-denver` | its existence and `production_branch = main` | `prevent_destroy` (ADR-008) |
| Access one-time PIN identity provider | yes | `prevent_destroy` |
| Access application for `/seller` and `/seller/*` on `leaving-denver.pages.dev` and `*.leaving-denver.pages.dev` | yes | `prevent_destroy`; its `aud` is an output |
| Access Allow policy for the owner's address | yes | exactly one `email` rule, never a domain |

### 3. What is deliberately left alone

- **The Pages deployment configuration.** `wrangler.toml` is the source of truth for the build
  output, the compatibility date and the bindings (an Analytics Engine binding is being added
  there), and `wrangler pages deploy` rewrites `deployment_configs` on every deploy. The project's
  `build_config`, `deployment_configs` and `source` are `ignore_changes`: a copy in Terraform would
  be reverted by every deploy, and would revert the deploy's in turn.
- **`ACCESS_TEAM_DOMAIN` and `ACCESS_AUD`.** They live in the project's deployment configuration as
  secret variables. Terraform exposes the application's `aud` as a sensitive output so the owner
  can compare it with the binding, and never writes it. A recreated application has a new audience
  and closes `/seller/` until the binding is updated, which is why the application is protected
  from destruction.
- **Web Analytics.** The provider exposes the Pages setting only as the pair
  `build_config.web_analytics_tag` and `web_analytics_token`, which come from a Web Analytics
  site. Managing the setting means managing that site (`cloudflare_web_analytics_site`), whose
  `auto_install`, `lite` and `enabled` could not be read with an available token (`403`). A wrong
  guess would flip live injection, and a second site would count every visit twice. The setting
  stays the Pages dashboard toggle of ADR-005, ignored by Terraform with the rest of `build_config`.
  It can be added once a token that can read it exists (ticketed).
- **The Zero Trust organization** (the team domain) is a prerequisite of Access, not part of this
  site.
- **The read-only token for the n8n metrics digest** stays manual: a credential that grants read
  access is created and revoked by the owner, never in code.

### 4. Secrets and the email

- The Cloudflare token reaches Terraform as `CLOUDFLARE_API_TOKEN`, for one command, read from
  sops by the Makefile. It is a **new sops key, `cloudflare_terraform_token`**, not the deploy
  token: the deploy token is held by CI and must stay one that can only deploy Pages. The new one
  has Access and Pages Edit on this account, lives only in sops and on the owner's machine, and
  is revoked with the others (`decommission.md`).
- The owner's email is the sops key `owner_email`, passed as `TF_VAR_owner_email`. It is never
  written to a `.tf` file, a `tfvars`, a command line or the output: the variable is `sensitive`.
  `tests/test_infra_terraform.py` fails on an email or a token-looking string in any `.tf` or
  `tfvars` file and on a tracked state or variable file.
- The account id is not a secret: `CF_ACCOUNT_ID` in the Makefile, passed as `TF_VAR_account_id`.

### 5. Commands

`make infra-init`, `infra-ids`, `infra-plan`, `infra-apply`, `infra-fmt`.

- `infra-ids` finds the ids of the Access objects read-only, for the import blocks, and writes
  them to the gitignored `ids.auto.tfvars`. It stops unless each object is found exactly once and
  unless the token can read Access (the organization endpoint is the probe, see Context).
- `infra-plan` saves the plan; `infra-apply` applies **that saved plan** and nothing else, with no
  prompt, and refuses to run when `CI` is set. CI never applies. The review is the plan the owner
  read, not a keystroke. Before applying it reads the plan (`terraform show -json`,
  `scripts/infra-plan-guard.py`): an import-only plan goes through, a create or an update needs
  `CHANGES=1`, a plan that only deletes needs `DESTROY=1` (the decommission step), and a
  replacement is refused always (a replaced Access application has a new audience and closes
  `/seller/`). Deleting the Pages project is refused with every switch (ADR-008), so that does not rest on
  `prevent_destroy` alone. An `update` whose before and after are identical, with nothing unknown, is a
  change in sensitivity marking only (the sensitive owner email marks the whole policy
  `include`) and counts as the import it is: the owner's real first plan showed exactly that.
- `infra-fmt` (format check and `validate`) needs no credential. `make check` runs it when
  Terraform is installed and prints a notice when it is not. CI installs Terraform, so a malformed
  module fails the build.

## Consequences

### Positive

- The Access application, its audience rule and its single allowed address are written down and
  reviewable, and `terraform plan` shows drift.
- A rebuilt machine or a lost state file is recovered by `make infra-ids && make infra-plan`.
- The deploy token stays narrow: nothing about Access or the email reaches CI.

### Negative

- **The Access objects could not be planned from the repository's own token.** It has no Access
  scope, so the first real plan was the owner's, with the new token: 4 to import, 3 to change, 0
  to destroy. Every difference was an attribute the dashboard had set (names, an empty `rdp` rule,
  cookie options), and `access.tf` was reconciled to the live objects before the first apply. The
  Pages project had been planned with the deploy token: `1 to import, 0 to add, 0 to change, 0 to
  destroy`.
- **Two settings stay as the dashboard made them** so the first apply is import-only: every
  identity provider is allowed (`allowed_idps` unset) and the Access cookie is not HttpOnly.
  Tightening both is a separate, deliberate apply (issue #184, `CHANGES=1`).
- The audience can only be read from state after the first apply, since a plan writes none: before
  applying it is compared from the plan's import block with the dashboard's AUD tag, after
  applying with `terraform output -raw access_aud` against `ACCESS_AUD`.
- A second token exists, with a wider scope. It is a credential to hold and to revoke.
- State is one file on one machine. Its backup is the automatic `terraform.tfstate.backup` beside
  it and the import blocks.
- `prevent_destroy` makes removal an edit: the decommission runbook says which blocks to delete, then `make infra-apply DESTROY=1`.

### Neutral

- The three Cloudflare resources Terraform manages are free at the account's current limits.

## Alternatives considered

- **Remote state** (an R2 or Terraform Cloud backend): rejected. A second store and a second
  credential for a single-owner repository that is wound down in five weeks.
- **Committed state, or an encrypted state in git** (sops): rejected. The email lives in it, and
  history in a public repository is permanent (lesson-006).
- **Managing `deployment_configs` too:** rejected, see Decision 3.
- **Widening the deploy token:** rejected, see Decision 4.
- **Moving `integrations/n8n/` under `infra/`:** not done. That directory holds a workflow to
  import into n8n, not state or code Terraform runs, and the move would change every reference
  for no gain.

## Revisit when

- **A token that can read Web Analytics exists:** manage the site and tie it to `build_config`.
- **The sale ends:** follow `docs/runbooks/decommission.md`. The Access resources are removed from
  the configuration and destroyed; the Pages project stays (ADR-008).

## References

- ADR-005, ADR-007, ADR-008
- Issue: `mlorentedev/leaving-denver#178`; spec `specs/OPS-014-cloudflare-terraform/`
- Runbook: `docs/runbooks/ops.md`, "Cloudflare configuration (Terraform)"
- `docs/lessons/lesson-030-a-token-without-access-scope-lists-access-as-empty.md`
- `infra/terraform/cloudflare/`, `scripts/infra-ids.sh`, `tests/test_infra_terraform.py`
