---
id: "lesson-wrangler-delegates-new-pages-projects-to-workers"
type: lesson
scope: local
tags: [cloudflare, wrangler, pages, workers, deploy]
created: "2026-09-26"
source: "Creating the leaving-denver Pages project (CI-001)"
---

# Lesson: Wrangler Hands New Pages Projects to Workers Unless Told Otherwise

## Context (The Problem/Error)
`wrangler pages project create leaving-denver --production-branch=main` (wrangler 4.141.0) did not
create a Pages project. Run from an agent session on an account with no Pages projects, it
delegated to a Workers static-assets deploy, which failed with "Missing entry-point to Worker
script or to assets directory". Nothing was deployed.

## The Finding (Root Cause/Solution)
Since wrangler 4.108 (extended to `project create` in 4.130), wrangler sends new, purely static
projects to Workers static assets when an AI agent runs `pages deploy` or `pages project create`.
Cloudflare now recommends Workers for new projects; Pages is in maintenance mode.

For this site Pages is still the better fit: it is static, lives until 2026-11-09, and uses Pages
branch previews, `_headers` and a token scoped to *Cloudflare Pages: Edit*. So `make cf-project`
passes `--force` to create the project on Pages. Once the project exists, later `pages deploy`
calls stay on Pages and need no `--force`.

A second trap in the same place: Pages' `wrangler.toml` does not accept `account_id`.
`pages project list` ignores it, but `pages deploy` validates the file and fails with
"Configuration file for Pages projects does not support account_id". The first CI deploy
failed on that, with nothing published. The account id goes in `CLOUDFLARE_ACCOUNT_ID`.

## Anti-Pattern (What NOT to do)
Assuming a `pages ...` command talks to Pages, or "fixing" the failure by adding an `[assets]`
block to `wrangler.toml`. That turns the deploy target into a Worker the Pages token cannot deploy.

## Golden Rule (The Pattern)
> **Pin the wrangler version, and create the Pages project explicitly with `--force`
> (`make cf-project`). Choose Workers on purpose, not because of a CLI default.**
