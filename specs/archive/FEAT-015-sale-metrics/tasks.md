---
tags: [spec, tasks]
created: "2026-10-03"
---

# Tasks - FEAT-015-sale-metrics

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `feat/sale-metrics` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] No open questions left in `proposal.md` (the unverified ones are named under Risks and handed to the owner in the runbook)

## Implementation

- [x] [AC1] [AC2] Write `tests/test_hit_function.py` (Node, fake binding): validation, 400 vs 204, shape, nothing read of the request. Run it (expected FAIL: no function).
- [x] [AC1] [AC2] Add `functions/api/hit.js`.
- [x] [AC8] `wrangler.toml` binding, and the test that declares it and the middleware passing `/api/hit` through.
- [x] [AC3] [AC4] [AC5] [AC6] Write `tests/test_metrics_beacon_browser.py` (stubbed `sendBeacon`, plus the real one over HTTP under `connect-src 'self'`); add a `query` argument to the harness. Run it (expected FAIL: no beacon).
- [x] [AC3] [AC4] [AC5] Add the beacon to `index.html`'s script: landing, view, tap.
- [x] [AC7] Forward the query in `share.html`; update the link-preview assertion.
- [x] [AC9] Write `tests/test_sale_metrics_workflow.py` and generate `sale_metrics_daily_digest.json`; the Code node runs in Node on rows written by `hit.js`.
- [x] [AC10] ADR-011, amend ADR-005, runbook sections (ops, kubelab-integration), the teardown, lesson-029.
- [x] [AC11] New catalog tests in `CATALOG_TESTS`; `make check` with `seller.sale_over: true`.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [x] PR opened referencing this spec folder
