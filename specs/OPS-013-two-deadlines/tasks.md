---
tags: [spec, tasks]
created: "2026-10-02"
---

# Tasks - OPS-013-two-deadlines

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `feat/two-deadlines` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] No open questions left in `proposal.md`

## Implementation

- [x] [AC1] [AC2] [AC6] `tests/test_two_deadlines.py`: explicit windows, `seller_drops`, `drops` output, every validation failure (expected FAIL: no such keys).
- [x] [AC1] [AC2] `sale_dates()`, `sale_schedule(seller)`, `seller_drops(seller)`; the data keys in `data/inventory.yaml`.
- [x] [AC3] [AC4] Countdown rule, hero and title variants, car card line, per-locale `date_format` (EN and ES).
- [x] [AC5] Flyer date line.
- [x] [AC7] Close-out step and snippet in `docs/runbooks/decommission.md`, run by a test against a copy of the data.
- [x] [AC8] Runbooks: seller playbook, backup exits, vehicle sale, decommission, ops, README, architecture.
- [x] Existing tests moved to the new keys (fixtures, the old single-date assertions).
- [x] Write lesson-027.
- [x] Run `make check` in catalog mode and in end mode.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
