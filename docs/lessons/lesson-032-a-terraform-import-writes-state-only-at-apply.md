---
id: "lesson-a-terraform-import-writes-state-only-at-apply"
type: lesson
scope: local
tags: [terraform, cloudflare, access, testing]
created: "2026-10-04"
source: "OPS-014 / PR #180"
---

# Lesson: A Terraform Import Writes State Only at Apply

## Context

PR #180 brings the existing Pages project and the Access objects in front of `/seller/` under
Terraform with `import` blocks. The runbook told the owner to plan, then compare
`terraform output -raw access_aud` with the `ACCESS_AUD` binding, then apply. The owner's first real
plan also reported changes nobody had written.

## Finding

- `plan` with `import` blocks writes no state. Before the first apply, `terraform output` has
  nothing to read: it exits 0 and prints an empty string. A check placed there compares against
  nothing and cannot stop anything. The `aud` is visible before the apply only inside the plan's
  import block. The output is only meaningful after the import-only apply.
- A `sensitive` variable marks the whole attribute that contains it. `owner_email` sits inside the
  policy's `include` list, so the plan reported `1 to change` on the policy with identical before
  and after values. Terraform's own note says "The value is unchanged". In `terraform show -json`,
  the only difference is `before_sensitive.include = [{"email": {}}]` against
  `after_sensitive.include = true`.
- Objects made in a dashboard carry values a hand-written resource leaves out: an empty
  identity-provider name, explicit `false` cookie flags, an empty `rdp` block. The first plan wanted
  to change three of the four imported objects until `access.tf` declared what was live.
- A test of `make infra-apply` wrote and deleted `plan.tfplan` in the real Terraform directory. An
  owner with a saved plan therefore failed `make check`, and the test would have deleted that plan.

## Guard

- `scripts/infra-plan-guard.py` reads `terraform show -json` of the saved plan before
  `make infra-apply` runs it:
  - it applies an import-only plan, including an `update` whose values are identical (a change in
    sensitivity only);
  - it refuses a real change without `CHANGES=1`;
  - it refuses a replacement always, and a delete of the Pages project always.
- `tests/test_infra_terraform.py` covers each case with a stub `terraform`, in a scratch `TF_DIR`.

## Rule

Gate an import on the plan's own content, read as JSON, and run state checks after the apply that
creates the state. Reconcile the code to the live object, never the reverse. A test that drives a
real tool's working directory gets a scratch directory.
