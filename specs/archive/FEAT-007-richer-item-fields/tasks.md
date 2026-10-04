---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-007-richer-item-fields

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `feat/richer-item-fields` created from main
- [x] `proposal.md` states testable acceptance criteria

## Implementation

- [x] [AC1] [AC2] [AC3] [AC4] [AC5] [AC6] Write `tests/test_richer_item_fields.py` and
  `tests/test_richer_item_fields_browser.py`; run them (expected FAIL: 51 failed, 10 passed).
- [x] [AC1] Delete `current_asking` from the data; `list_price()` refuses it and a missing price.
- [x] [AC2] Normalize household conditions to the scale; labels in `locales/*.yaml`;
  `check_condition()` refuses off-scale values.
- [x] [AC3] Pass `flaws` through, overlay `es.flaws`, render on the sheet and in `/seller/` copy.
- [x] [AC4] Derive `discount_pct` in the builder; badge on card and sheet.
- [x] [AC5] Add `size_in` to the data where the owner's string is W x D x H; derive `size_flags`.
- [x] [AC6] Sort by ascending price, Sold last.
- [x] [AC7] Run `make check`; 390 px screenshot.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder
