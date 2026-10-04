---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-004-private-control-panel

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `feat/private-control-panel` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] Fake-number fixture `tests/fixtures/private.example.yaml` (the real file is never read by tests)

## Implementation

- [x] [AC1] [AC2] [AC3] [AC4] [AC8] Write `tests/test_panel.py` against the fixture
  (expected FAIL: no `panel` or `pricing` module).
- [x] [AC2] [AC3] `pricing.py`: `price_tiers` (lifted out of `cmd_drops`) and `next_drop`.
- [x] [AC1] [AC4] `panel.py` rows, `templates/panel.html`, `write_panel`; `cmd_panel`; `make panel`.
- [x] [AC5] [AC6] Write `tests/test_panel_records.py` (expected FAIL: no `record_post`,
  `record_price`, `cmd_post`; `record_sale` takes no date).
- [x] [AC5] [AC6] `private_data.set_private`/`record_*`/`decrypt_private`; `cmd_post`,
  `cmd_reprice`, `cmd_sold` with take-down steps; `make post`, `make reprice`.
- [x] [AC7] Write `tests/test_panel_isolation.py` (expected FAIL: the build tolerates a panel
  file in the public dist); add the guard to `verify_security_guarantees`.
- [x] [AC9] Runbooks (seller playbook, ops, architecture), ADR-006, lesson-019.
- [x] Run `make check`.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [x] PR opened referencing this spec folder
