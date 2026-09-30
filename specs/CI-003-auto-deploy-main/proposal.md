---
id: "CI-003-auto-deploy-main"
type: spec
status: implementing # draft | implementing | verifying | archived
created: "2026-09-29"
issue: "mlorentedev/leaving-denver#82"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# CI-003: Auto-deploy tested main

## Why

<!-- from issue #82: CI-003: Auto-deploy tested main to Cloudflare Pages production -->

Production is stuck on an older commit that incorrectly advertises an elevator, even though
the corrected catalog and tests are merged into `main`. The owner explicitly wants every
tested merge to `main` to publish automatically, rather than depending on a manual dispatch.

## What

After a successful push to `main`, the workflow deploys the freshly built public catalog
to the production Cloudflare Pages branch with the real contact secret, then smoke-tests
the deployment. Pull requests still only test. Explicit workflow dispatch still supports
manual production redeploys from `main` and named preview branches.

## Out of scope

- Making preview deployments automatic or deploying the private seller workspace.
- Replacing Wrangler or changing Cloudflare Pages infrastructure.

## Risks / open questions

- The `production` GitHub environment has no required reviewers (verified via API);
  the existing CI secrets and Pages project were used successfully by prior manual deployments.
- A missing `SELLER_PHONE` must fail rather than deploy with the test placeholder. Keep
  `needs: test`, the `main` ref guard, and serialized deployments per Pages branch.
- A branch can rewrite its own manually dispatched workflow and bypass a shell ref
  check. Restrict both deployment environments to `main` and move the Pages token
  from repository-wide secrets to those environments before enabling CD.

## Acceptance criteria

- [ ] AC1: A `push` to `main` deploys to the `production` environment on Pages branch
  `main` only after `test` succeeds; a `pull_request` never deploys.
- [ ] AC2: Manual `workflow_dispatch` still deploys a validated preview branch and
  permits `branch=main` only from `refs/heads/main`.
- [ ] AC3: Deploy builds with the nonempty real `SELLER_PHONE`, runs the same test gate,
  and smoke-tests the deployed URL; no private workspace is uploaded.
- [ ] AC4: README and site operations document automatic production CD and manual previews.
- [ ] AC5: A workflow on a non-main ref cannot access the Pages token or deploy
  to either deployment environment; setup remains idempotent.

## References

- Bitácora: #82, prior manual deploy #4
- `docs/adr/adr-001-static-catalog-over-monolithic-attachment.md`
- `.github/workflows/ci.yml`, `docs/runbooks/ops.md`
