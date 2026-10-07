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
