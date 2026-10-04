---
id: "lesson-a-token-without-access-scope-lists-access-as-empty"
type: lesson
scope: local
tags: [cloudflare, access, terraform, tokens, testing]
created: "2026-10-03"
source: "OPS-014 / issue #178"
---

# Lesson: A Token Without Access Scope Lists Access as Empty

## Context

OPS-014 moves the Cloudflare configuration into Terraform and needs the ids of the Access
application, policy and identity provider that were clicked in the dashboard. The repository's
deploy token reads the Pages project fine, so it was tried against Access first.

## Finding

- `GET /accounts/<id>/access/apps`, `/access/identity_providers` and `/access/policies` answered
  `200` with `"result": []` and `total_count: 0`. Meanwhile an anonymous `GET /seller/` redirected
  to the Access login and the Pages project held `ACCESS_AUD`. Access was configured; the token
  could not see it.
- Cloudflare evidently filters a list to what the token may read. A token with no Access scope gets an empty
  list, not a `403`. Only `/access/organizations` and `/rum/site_info/list` answered `403`.
- Read as "nothing is configured", the empty list would have led to creating a second application
  next to the one protecting `/seller/` now, with its own audience and a deploy that still checks the
  old one.
- A Pages-only token is also what the Terraform plan of an Access resource would use: it would plan
  `1 to add` for something that exists.

## Guard

`scripts/infra-ids.sh` probes `/access/organizations` first and refuses with "this token cannot read
Zero Trust Access" when it answers non-2xx, whatever the lists say, and it stops unless each object
is found exactly once. `tests/test_infra_terraform.py` runs it against a stubbed API in which the
lists are empty and the probe is refused: it must fail and print no ids.

Check an empty result from any API by asking an endpoint the token must be able to read, or one
that is known to exist, before believing it.
