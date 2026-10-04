---
tags: [spec, tasks]
created: "2026-10-01"
---

# Tasks - BUG-013-not-found-page

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `fix/not-found-page` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] No open questions left in `proposal.md` (the real Pages status is a smoke check, not a blocker)

## Implementation

- [x] [AC1] [AC2] [AC3] [AC4] [AC5] Write `tests/test_not_found.py` over scratch builds in both modes (expected FAIL: no page).
- [x] [AC1] [AC2] [AC3] [AC4] Add `locales/not_found.yaml`, `templates/not_found.html`, `write_not_found()`, and `404.html` in `END_SITE_FILES`; update `ALLOWED` in `tests/test_end_of_sale.py`.
- [x] [AC7] Add the template to `public.css` sources and to `tests/test_class_coverage.py`.
- [x] [AC6] Add the `not_found` check to `scripts/smoke.sh` (both branches); give the smoke tests' stubs Pages' missing-path behaviour (`tests/pages_stub.py`) and cases for a 200 and for a foreign 404 body.
- [x] Write lesson-026.
- [x] Run `make check` in catalog mode and in end mode.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [x] PR opened referencing this spec folder
