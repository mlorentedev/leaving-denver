---
tags: [spec, tasks]
created: "2026-10-01"
---

# Tasks - OPS-011-end-of-sale

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `feat/end-of-sale-page` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] No open questions left in `proposal.md` (the `_redirects` check on a real deploy is a smoke check, not a blocker)

## Implementation

- [x] [AC5] Write `tests/test_end_of_sale.py`: `seller.sale_over` defaults to off, accepts only a boolean,
  and the committed `data/inventory.yaml` leaves it off. Run it (expected FAIL: no helper).
- [x] [AC5] Add `sale_over()` to `site_builder.py`.
- [x] [AC1] [AC2] [AC3] [AC4] Extend the tests with scratch end builds: no phone and no item anywhere, the
  end page in both languages, no `i/`, `es/i/`, `seller/`, `catalog/`, and `_redirects`; a build with no
  `SELLER_PHONE` and no private data; stale files from an earlier build are removed. Run (expected FAIL).
- [x] [AC1] [AC2] [AC3] [AC4] Add `templates/sale_over.html`, the `sale_over` copy in `locales/*.yaml`, and the
  end-build branch of `build_public_site` / `build_all`.
- [x] [AC6] Write `tests/test_smoke_script.py` cases: smoke passes on a served end build, fails when the end
  page carries `tel:`/`sms:` or its redirects do not answer (expected FAIL), then add the end-mode block to
  `scripts/smoke.sh`.
- [x] [AC7] Write `docs/runbooks/decommission.md`, link it from `ops.md`, and write ADR-008.
- [ ] Run `make check`.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder
