---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-008-verify-the-car

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `feat/verify-the-car` created from main
- [x] `proposal.md` states testable acceptance criteria

## Implementation

- [x] [AC1] [AC2] [AC3] [AC4] [AC5] [AC6] Write `tests/test_verify_the_car.py` against the
  built pages and the data; run `uv run pytest -q tests/test_verify_the_car.py`
  (expected FAIL: no section, no `verify:` data).
- [x] [AC6] Add `verify:` under the car in `data/inventory.yaml` with an `es:` overlay.
- [x] [AC2] [AC3] Pass `vin` and `verify` through `sanitize_public_inventory`; localize and
  validate them in `localize_public_inventory` (official hosts, existing photos).
- [x] [AC1] [AC4] Add the section strings to `locales/en.yaml` and `locales/es.yaml`.
- [x] [AC1] Render the section under the car's card in `templates/index.html`.
- [x] Run `make check`.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder
