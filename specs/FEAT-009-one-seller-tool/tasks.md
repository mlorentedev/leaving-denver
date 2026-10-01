---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-009-one-seller-tool

> TDD order. PR 1 only (the public-safe copy); PR 2 is described in `proposal.md` and is not
> tracked here.

## Setup

- [x] Branch `feat/one-seller-tool-copy` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] `dotf spec init` could not run (GitHub auth was invalid, so the issue gate failed);
  the folder was scaffolded by hand from FEAT-008's four files

## Implementation

- [x] [AC1-AC8] Write `tests/test_seller_copy.py`; run
  `uv run pytest -q tests/test_seller_copy.py` (expected FAIL: no `CONFIG`, no replies).
- [x] [AC9] [AC11] Extend `tests/test_mobile_poster.py` (private markers, the local assistant
  stays out of the public build), `tests/test_security_isolation.py` (template context),
  `tests/test_inventory_ssot.py` (the new files join the car-copy and unbacked-claim guards),
  `tests/test_poster_voice.py` (the seller tool, English and Spanish).
- [x] [AC10] Let the browser harness inline a page's module script (file:// blocks it) and
  write `tests/test_seller_browser.py`.
- [x] [AC8] Add `data/seller-replies.yaml` (six replies, English and Spanish).
- [x] [AC1-AC3] Build the payload in `site_builder.py` (`seller_items`, `seller_payment`,
  `seller_replies`, `write_seller_poster`): Spanish overlay, payment terms from data and
  locales, month and origin.
- [x] [AC1-AC7] Rewrite `assets/seller.mjs`: channel table, Spanish, vehicle copy, flaws
  last, limits, links, creator links, tags, price, full listing.
- [x] [AC8] [AC10] Rework `templates/seller.html`: six channels, counters, creator link,
  tags, photos, the replies section.
- [x] Guard the defect class the change exposed: a class written only in a script is never
  compiled. `public.css` scans `seller.mjs`, and `tests/test_class_coverage.py` now covers
  `seller.html` and `seller.mjs` (it failed without the `@source` line).
- [x] Update `docs/runbooks/seller-playbook.md` and `docs/runbooks/ops.md`.
- [x] Run `make check`.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder (GitHub auth was invalid when the branch was
  made: committed locally, not pushed)
