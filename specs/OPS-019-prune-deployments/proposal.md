---
id: "OPS-019-prune-deployments"
type: spec
status: implementing # draft | implementing | verifying | archived
created: "2026-11-10"
issue: "mlorentedev/leaving-denver#270"   # repo#NNN — GitHub Issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
owner: manu
---

# OPS-019-prune-deployments

## Why

The sale is over and the end page is live, but Cloudflare Pages keeps every deployment at its own
permanent URL, and each older one still serves the catalog with the phone number in it. The
production alias is one door; on 2026-11-11 the project held **242 deployments**, so 241 doors stay
open to anyone holding an old link — a shared item card, a `candidate` preview, a hashed
deployment URL.
ADR-008 already requires them deleted, and the deploy token is revoked on 2026-11-15: after that,
removing them needs a new token by hand.

Step 4 of `docs/runbooks/decommission.md` is the only step of the close-out with no command: it
asks the owner to click through the dashboard once per deployment, and a missed one looks exactly
like a finished one. This repository's rule is zero manual operations, and this is the step where
the omission is silent.

## What

`scripts/prune-deployments.sh` lists the project's deployments through the Cloudflare API and
deletes every one that is not serving production:

- **Dry run by default.** It prints `keep` for the deployment answering to `<project>.pages.dev`
  and `delete` for each other one, with counts, and issues no write.
- **`--apply` deletes them**, one call per deployment, and stops at the first failure with a
  non-zero exit rather than reporting success over a half-done list.
- **Every delete carries `?force=true`.** Cloudflare refuses a delete of a deployment that holds a
  branch alias (error 8000035), and every preview alias this run exists to close — `candidate`
  included — is one. The keeper is never reached by that loop, so the force cannot remove what
  production serves.
- **The keeper is Cloudflare's own answer.** It is the project's `canonical_deployment` — the
  deployment the canonical domain answers with — not "the newest" and not a match on `aliases`:
  measured on 2026-11-11, a production deployment comes back with `aliases: null`, so an alias
  match finds nothing at all. If the project names no canonical deployment, or names one that is
  not in the deployment list, the script exits non-zero and deletes nothing, including under
  `--apply`.
- **Never delete a deploy mid-build.** A deployment whose `latest_stage.status` is neither
  `success` nor `failure` (queued, uploading, deploying) is reported as `skip (build in progress)`
  and kept, so a deploy that started while the script ran survives.
- **The token never reaches argv or stdout.** It is read from the environment (`make` pipes it from
  sops the way `make deploy` does); the script's own output names deployments, never credentials.

`make prune-deployments` runs the dry run with the same token plumbing as `make deploy`, and
`make prune-deployments APPLY=1` deletes.

`docs/runbooks/decommission.md` step 4 becomes those two commands, with the dashboard path kept as
the fallback for a machine that has no sops key.

## Out of scope

- Deleting the project, the pages, the Terraform-managed Access application or the API token
  itself: that is step "By Nov 15" and the decommission runbook's own.
- The branch aliases (`candidate.leaving-denver.pages.dev` and per-branch previews): deleting
  their deployments removes what they serve, and Cloudflare drops an alias with its last
  deployment. The script does not create or remove aliases.
- Any change to what the site builds or serves.

## Risks / open questions

- **Destructive by construction.** Mitigated by: dry run as the default, `--apply` as the only
  write path, the keeper taken from the alias rather than from "the newest", refusal on an
  ambiguous keeper, and the newest-than-keeper skip. The dry run is the reviewed artefact: the
  owner sees the exact list before the first delete.
- **`aliases` cannot identify production.** Measured 2026-11-11: the production deployment
  returns `aliases: null`, while a preview carries its branch alias as a full URL. The keeper is
  therefore the project's `canonical_deployment`, and the fail-closed check is "that id appears in
  the list", which also catches the two calls disagreeing about the project.
- **The `candidate` deployment is deleted too.** It was created after the production one, so
  "newer than production" would have protected it; the guard is the build's stage instead, which
  is what actually distinguishes a deploy in flight from a finished preview.
- **The API's shape can drift.** The script reads `result[].id`, `.aliases`, `.created_on` and
  `result_info.total_pages`. A missing field would make it under-report rather than over-delete:
  a deployment whose aliases cannot be read never becomes the keeper, so the run refuses.
- **The local vault token does not authenticate against this account** (checked 2026-11-10:
  Cloudflare API error 10000). The run therefore goes through the repository's own sops key
  `cloudflare_pages_token`, which is the one `make deploy` already uses. A machine without the
  sops key can still read the dry run's output or use the dashboard fallback.

## Acceptance criteria

- [ ] AC1 — a dry run names every deployment exactly once, marks the production one `keep`, and
  issues no HTTP write (test: the stub records no `-X DELETE`).
- [ ] AC2 — `--apply` issues one DELETE per non-keeper and none for the keeper, each carrying
  `force=true`; the exit status is 0 only when every delete succeeded.
- [ ] AC3 — when the project names no canonical deployment, or names one that is absent from the
  deployment list, the script exits non-zero and issues no DELETE, even with `--apply`.
- [ ] AC4 — a deployment whose build has not settled is reported as skipped and never deleted.
- [ ] AC5 — pagination is followed: a project whose deployments span two pages is fully covered by
  the dry run.
- [ ] AC6 — the token is never printed and never appears in the process arguments; the script
  refuses to start when `CLOUDFLARE_API_TOKEN` or `CLOUDFLARE_ACCOUNT_ID` is missing.
- [ ] AC7 — `make prune-deployments` exists, defaults to the dry run, and takes `APPLY=1` to
  delete; the decommission runbook's step 4 names it and keeps the dashboard fallback.

## References

- Issue: `mlorentedev/leaving-denver#270` (bitácora).
- ADR: `docs/adr/adr-008-*` (the close-out order: end page first, old deployments deleted, then the
  credentials).
- Runbook: `docs/runbooks/decommission.md`, step 4 of "By Nov 9".
- Sibling shape: `scripts/audit-deploy.sh` (read-only, `gh api`, tested against a stub) and
  `scripts/infra-ids.sh` (same `curl` + `jq` + `CF_API` override used here for tests).
