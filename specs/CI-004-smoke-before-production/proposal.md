---
id: "CI-004-smoke-before-production"
type: spec
status: implementing # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#102"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# CI-004: Smoke a candidate before production

## Why

<!-- from issue #102: CI-004: smoke a preview before production, and tighten the deploy trust surface -->

The deploy job publishes to production first and smoke-tests it afterwards, so a broken build is live before anything notices it, and rolling back is a manual dashboard step. The independent CI-003 review also found the trust surface around the deploy wider than it needs to be: the contact secret is readable by any same-repo workflow, the actions next to the Cloudflare token float on tags, the branch policies are checked only by grepping files, and the deploy gate accepts the test placeholder phone.

## What

- A production deploy (a push to `main`, or a dispatch with `branch=main`) first publishes the build to the Pages branch `candidate` and smoke-tests that deployment. Only then does it publish to `main`, and it smoke-tests the canonical `https://leaving-denver.pages.dev`. A failed candidate smoke stops the job, and production keeps serving the previous deployment. A dispatched preview is still one deploy and one smoke.
- `make ci-secrets` sets `SELLER_PHONE` in the `production` and `preview` environments and removes the repository-level secret, as it already does for the Cloudflare token.
- Every action in `ci.yml` is pinned to a commit SHA, with the release in a comment so Dependabot keeps updating it.
- `scripts/audit-deploy.sh` reads the live environment settings: both environments exist, they allow custom branch policies only, and each has exactly one policy, the branch `main`. It runs weekly, on dispatch, and on PRs that touch it, and locally as `make audit-deploy`. When the caller can list secrets (the owner's `gh`), it also checks that neither secret is left at the repository level.
- The deploy gate refuses the test placeholder `+15555550100` as well as an empty phone.
- The Deploy steps in `docs/runbooks/ops.md` are numbered in order and describe the candidate step.

## Out of scope

- `pr-agent.yml`: it does not handle the Cloudflare token or the phone. Pinning it is a separate change.
- Running `make ci-secrets`: it needs the age key, so the owner runs it. Until then the deploy reads the repository-level secret, which works as before.
- Automatic rollback: the candidate smoke keeps a bad build out of production, and a manual rollback is still documented for anything the smoke cannot see.

## Risks / open questions

- A Pages preview deployment adds `X-Robots-Tag: noindex`. The smoke checks `robots.txt`, not that header, so a candidate passes the same checks production does.
- The canonical URL can briefly serve the previous deployment. The smoke checks invariants (contact, stylesheet, robots, previews, private paths), not the new content, so a stale edge still passes it. The candidate smoke is the one that checks this build.
- Whether `GITHUB_TOKEN` with `actions: read` may read environments and branch policies is checked by the PR run of the audit workflow itself. If it cannot, the audit stays local (`make audit-deploy`) and the scheduled run is dropped with the reason recorded.
- Two uploads per production deploy. Wrangler skips assets the project already has, so the second upload is small.

## Acceptance criteria

- [ ] AC1: in the deploy job, the candidate deploy and its smoke come before the production deploy, and both run only for production. A dispatched preview deploys once. `tests/test_cd_workflow.py` asserts the step order, not only that the steps exist.
- [ ] AC2: after the production deploy, the canonical `https://leaving-denver.pages.dev` is smoke-tested.
- [ ] AC3: `make ci-secrets` sets `SELLER_PHONE` per environment and deletes the repository-level secret, after the per-environment set.
- [ ] AC4: every `uses:` in `ci.yml` is a 40-character SHA followed by a `# vX.Y.Z` comment.
- [ ] AC5: `scripts/audit-deploy.sh` fails on a missing environment, an extra or wrong branch policy, or a leftover repository-level secret, and passes on the expected settings. A stubbed `gh` tests every case.
- [ ] AC6: the deploy gate exits non-zero for `+15555550100`.
- [ ] AC7: the ops runbook's Deploy steps are numbered 1 to N and mention the candidate.

## References

- Issue #102, from the independent CI-003 review (`specs/archive/CI-003-auto-deploy-main/`)
- `docs/runbooks/ops.md`
