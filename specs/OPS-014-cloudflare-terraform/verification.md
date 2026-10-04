---
tags: [spec, verification]
created: "2026-10-03"
---

# Verification - OPS-014-cloudflare-terraform

## Evidence

- [x] AC1 -> `tests/test_infra_terraform.py` (scanner, `test_no_terraform_file_holds_an_email_or_a_token`, the ignore and tracked parametrized tests). Mutation checked: a planted email or token fails the scan.
- [x] AC2 -> `test_terraform_gets_the_token_and_email_in_its_environment_never_on_argv`, `test_a_missing_owner_email_stops_before_terraform_runs`. Mutation checked: `-var owner_email=...` on argv fails. Real run of `make infra-plan` without the `owner_email` key: `no owner_email in data/private.sops.yaml: make secrets`, exit 2.
- [x] AC3 -> `test_apply_applies_only_a_saved_plan_and_never_in_ci`.
- [x] AC4 -> `test_check_runs_terraform_fmt_and_validate_and_fails_when_they_do`, `test_check_skips_with_a_notice_when_terraform_is_not_installed`, `test_make_check_includes_the_terraform_check`; CI installs Terraform (`hashicorp/setup-terraform`, pinned by commit).
- [x] AC5 -> `test_every_managed_resource_is_adopted_by_an_import_block` (mutation checked: a removed import block fails), the Pages, Access and email-variable tests.
- [x] AC6 -> the `ids` tests against a stubbed API; real run with the deploy token: `make infra-ids TF_TOKEN_KEY=cloudflare_pages_token` -> `infra-ids: this token cannot read Zero Trust Access (...)`, exit 2, no file written.
- [x] AC7 -> read-only plan with the deploy token, `-target=cloudflare_pages_project.site`: `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.` (the `features.json` command re-runs it, exit 0).
- [x] AC8 -> `tests/test_ops_runbook.py`, `tests/test_decommission_runbook.py` (new test for the Terraform order).

Not verifiable from here, and said so: the Access objects. The deploy token has no Access scope, so their plan is the owner's, with the Terraform token. The owner's first real plan was 4 to import, 3 to change, 0 to destroy, only dashboard-made attribute differences; `access.tf` was reconciled to the live objects (d5e147b). Follow-up for two settings left as the dashboard made them (all identity providers allowed, cookie not HttpOnly): #184.
- [x] Owner evidence, 2026-10-04, with the Terraform token after d5e147b: `make infra-ids` OK; `make infra-plan` -> `Plan: 4 to import, 0 to add, 1 to change, 0 to destroy`. The one change is the policy `include` sensitivity marking only (`terraform show -json`: zero value differences). The `aud` of `cloudflare_zero_trust_access_application.seller` in the plan (`894b144e...b2060`) matches the dashboard's Application Audience (AUD) Tag (owner-confirmed), and `/seller/` loaded after an Access login the same day (FEAT-009 AC9), so the middleware accepted that audience. No apply has been run: it waits for review approval and the merge.
- [x] `infra-apply` reads the saved plan (`scripts/infra-plan-guard.py`): import-only applies, an update needs `CHANGES=1`, a sensitivity-only update (identical before/after, as in the owner's second real plan: 4 import, 1 change on the policy) applies without it, a plan that only deletes needs `DESTROY=1` (decommission), a replacement is never applied (tests in `tests/test_infra_terraform.py`).

## Test status

- `make check` -> exit 0: `1098 passed, 2 skipped`, then `terraform validate`: `Success! The configuration is valid.`
- No regressions in the existing suite: yes.
- Nothing was applied and no Cloudflare resource was created or changed.

## Decisions made during implementation

- Web Analytics is not managed (ADR-012): the provider exposes the Pages setting only through a RUM site that the available token cannot read (403). Follow-up #179.
- Access policy is a standalone, reusable `cloudflare_zero_trust_access_policy`; if `make infra-ids` shows the live one differs in shape, the plan will say so.
- A new sops key `cloudflare_terraform_token` instead of widening the deploy token.
- `infra-apply` applies the saved plan instead of prompting: the review is the plan.
- The import blocks stay after the first apply: they rebuild a lost local state.
- `integrations/n8n/` stays where it is: it is an import artifact, not infrastructure.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-030-a-token-without-access-scope-lists-access-as-empty.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? yes: docs/adr/adr-012-cloudflare-configuration-as-terraform-with-local-state.md
- [x] New pattern candidate for `00_meta/patterns/`? no: one project so far, no recurrence

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/OPS-014-cloudflare-terraform/` -> `specs/archive/OPS-014-cloudflare-terraform/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
