---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-009-one-seller-tool

## Evidence

`tests/test_seller_copy.py` unless noted.

- [x] AC1 -> `test_the_spanish_channels_write_the_listing_from_the_spanish_overlay[fb-es|cl-es]`,
  `test_the_spanish_overlay_is_complete_for_every_listable_item`,
  `test_the_english_channels_stay_english`
- [x] AC2 -> `test_the_cars_copy_names_the_bank_payments_from_the_data_on_every_channel`,
  `test_the_car_copy_is_vehicle_copy_not_furniture_copy`;
  `tests/test_inventory_ssot.py::test_no_copy_offers_cash_next_to_a_cashiers_check[seller.mjs|seller.html|seller-replies.yaml]`
  and `::test_no_unbacked_vehicle_claims[seller.mjs|seller-replies.yaml|index.html (built seller)]`
- [x] AC3 -> `test_household_copy_takes_the_catalogs_payment_wording`,
  `test_the_page_logic_hardcodes_no_payment_wording`
- [x] AC4 -> `test_flaws_come_after_every_positive_and_follow_the_language`,
  `test_no_flaws_line_without_flaws`; `tests/test_richer_item_fields.py::test_the_seller_copy_lists_the_flaws`
- [x] AC5 -> `test_the_copy_is_singular_plain_and_phone_free` (every item, every channel),
  `test_every_listing_says_no_holds_and_no_deposits`,
  `test_craigslist_replies_through_its_relay_and_chat_channels_through_chat`;
  `tests/test_poster_voice.py::test_the_seller_tool_uses_first_person_singular`
- [x] AC6 -> `test_every_listing_fits_its_platform_without_cutting_anything`,
  `test_an_overlong_listing_is_flagged_not_silently_cut`
- [x] AC7 -> `test_each_channel_gets_its_own_attribution_and_the_link_stays_out_of_the_listing`,
  `test_the_origin_the_page_links_to_is_the_builders`;
  `tests/test_mobile_poster.py::test_mobile_copy_links_to_each_public_item_with_platform_attribution`
- [x] AC8 -> `test_six_scam_replies_each_have_english_and_spanish_with_copy_buttons`,
  `test_the_replies_come_from_the_data_with_the_car_payment_filled_in`,
  `test_the_replies_are_singular_plain_and_phone_free`,
  `test_the_build_refuses_a_reply_with_no_spanish`,
  `test_the_build_refuses_a_reply_with_an_unfilled_placeholder`
- [x] AC9 -> `tests/test_mobile_poster.py::test_mobile_poster_uses_only_published_sanitized_inventory`
  (now checks the page and `seller.mjs` for 13 private markers, the phone's digits included),
  `tests/test_security_isolation.py` (template context is `items_json`, `config_json`,
  `replies`)
- [x] AC10 -> `tests/test_seller_browser.py` (Spanish channel rewrites the listing; counters,
  creator link and tags follow the channel; every copy button copies what is on screen,
  replies included; all six channels render for all 12 items; a count turns red past the limit)
- [x] AC11 -> `tests/test_mobile_poster.py::test_the_local_assistant_stays_out_of_the_public_build_until_it_moves`;
  `git diff origin/main -- src/leaving_denver/templates/poster_assistant.html` is empty

## Test status

- Before: `make check` -> 442 passed, 1 skipped.
- The new and extended tests were written first. Run against the old `src/`: 10 failed,
  17 errors (the page fixture finds no `CONFIG`), 79 passed (the tests that do not touch the
  new behaviour: the existing ones and the guards that hold before and after, such as the
  voice test).
- The class-coverage guard for `seller.mjs` failed (`text-red-700` has no CSS rule) until
  `public.css` scanned the script.
- After: `make check` -> 489 passed, 1 skipped (47 new tests; lint clean).
- Complexity: `uvx radon cc -s` on `site_builder.py`: the new functions are A or B (highest:
  `seller_replies`, B 8); `ruff` C901 (max 10) is clean. The functions in `seller.mjs` are
  small and flat; no JS complexity tool is configured.

## Decisions made during implementation

- **Payload.** `items_json` stays a list of items (the tests that parse it keep working);
  the page settings go in a second `CONFIG` and the replies are rendered by Jinja, so the
  template context grows by `config_json` and `replies` and the isolation test names them.
- **Replies in a data file, not the locales.** The locale files ship whole to the catalog
  page (`ui_json`), so seller-only text there would be published to buyers. `data/seller-replies.yaml`
  is read only by the `/seller/` build.
- **The car's payment appears twice.** Its pickup note already states the payment; the
  `Payment:` line is the tested, data-driven one. See the proposal's risks.
- **No link in any listing body**, Craigslist and Nextdoor included. The playbook's
  "include the full catalog link" row is about umbrella posts, not per-item listings.
- **Spanish links** point at `/es/i/<id>/` (the Spanish share pages exist).
- **Condition wording** comes from the catalog's localized item (`conditions` in the
  locales), not the raw data, so the listing says what the catalog says.
- **Dropped on purpose** (not ported): the retail anchor and "bought new" lines, the x1.15
  tax math, the hard-coded payment wording, the selling points no data backs, the phone in
  the copy, the PIN.
- **Not done:** Spanish for OfferUp and Nextdoor (the assistant has none); a JS complexity
  tool.

## Promotion candidates

- [ ] Lesson for the repo's `docs/lessons/`? no: the lesson (a class named only in a script is
  never compiled) is already lesson-015; this change extended its guard to the seller page.
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no for PR 1; PR 2 needs the ADR
  described in `proposal.md`.
- [ ] New pattern candidate for `00_meta/patterns/`? no.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-009-one-seller-tool/` -> `specs/archive/FEAT-009-one-seller-tool/`
  (only after PR 2: the spec covers both)
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
