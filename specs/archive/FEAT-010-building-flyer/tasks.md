---
tags: [spec, tasks]
created: "2026-10-01"
---

# Tasks - FEAT-010-building-flyer

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Branch `feat/building-flyer` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] No open questions left in `proposal.md`
- [x] `segno` added to `pyproject.toml` and `uv.lock` (contract change, recorded in the proposal)

## Implementation

- [x] [AC2] Write `tests/test_flyer.py` for the URL and the QR: the module matrix parsed from the SVG equals `segno`'s for the literal UTM URL; the printed address is the host. Run it (expected FAIL: no flyer).
- [x] [AC2] Add `flyer_url`, `flyer_qr_svg` to `site_builder.py`.
- [x] [AC1] [AC3] [AC4] [AC5] Extend the tests with scratch builds: the page and its print rules, no phone/email/`$`, categories, car and date from the data, `noindex`, no link from the catalog. Run (expected FAIL).
- [x] [AC1] [AC3] [AC4] [AC5] Add `templates/flyer.html`, the `flyer_*` strings in `locales/*.yaml` and `write_flyer`, called once from `build_public_site`. Add the template to `public.css` sources and to `test_class_coverage.py`.
- [x] [AC7] Test the end build: no flyer, a stale one swept, `/flyer` and `/flyer/*` redirected. Then add the rule to `END_REDIRECTS`.
- [x] [AC6] Write the headless-Chrome print test (one Letter page, no vertical scroll at 816x1056). Make the harness accept a page with no script. Run (expected FAIL until the layout holds), then fix the layout.
- [x] [AC8] One line in `seller-playbook.md`, and a test that it names `/flyer/`.
- [x] Run `make check`; look at the screenshot at Letter size and fix anything ugly.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder
