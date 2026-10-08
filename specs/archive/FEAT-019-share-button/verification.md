---
tags: [spec, verification, templates]
created: "2026-10-06"
---

# Verification - FEAT-019-share-button

## Evidence

- [x] AC1 -> `tests/test_share_button_browser.py`: the five item-sheet cases now expect `i/<id>/?utm_source=share&utm_medium=referral&utm_campaign=moving-sale`, English and Spanish.
- [x] AC2 -> `test_the_hero_shares_the_catalog_as_word_of_mouth`, `test_the_hero_falls_back_like_the_item_sheet` (cancelled, failed share copies, refused clipboard shows it), `test_the_spanish_hero_shares_the_spanish_catalog`.
- [x] AC3 -> `tests/test_hit_function.py::test_every_channel_the_site_can_link_from_is_a_known_source` reads `utm_source=` from `index.html`; removing `share` from `hit.js` fails it (checked).
- [x] AC4 -> no change to `EVENTS` in `hit.js`; full suite below.

## Test status

- Test suite: `make build && uv run pytest -q` -> 1360 passed, 8 skipped.
- Manual: headless Chrome at 400x800, `/` and `/es/`: the button sits under the hero's pickup line, above the car card.
- After deploy: share from a phone, open the link on another, and see a `share` visit in the next digest.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? no: lesson-021 was amended for the catalog test it added; nothing else surprising
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: a new UTM source inside ADR-011's existing contract
- [x] New pattern candidate for `00_meta/patterns/`? no: specific to this sale's sources

## Independent review (2026-10-08)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer. It worked read-only on main at 077360f, checking each criterion against the code and the tests. The `features.json` commands were run again on 9659d65 before archiving, and all of them pass.

- Verdict: AC3 and AC4 hold, with no defects found in the code or on production.
- AC1 and AC2 (browser) were not run by the reviewer, because its sandbox refused `leaving-denver build`. They were run before archiving, on 9659d65: `test_share_button_browser.py -k 'not hero'` 6 passed, `-k hero` 5 passed.
