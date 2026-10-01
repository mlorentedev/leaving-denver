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
- [x] AC10 -> `tests/test_seal_command.py::test_the_python_side_hands_the_node_child_stdin_and_nothing_else`,
  `::test_the_command_without_a_terminal_exits_non_zero_and_touches_nothing`,
  `::test_the_workflows_hold_no_age_key_and_never_mention_sops`
- [ ] AC11 -> **owner slot**: unlock time on the phone (below).
- [x] AC12 -> `tests/test_private_isolation.py::test_nothing_in_src_or_the_build_refers_to_the_retired_workspace`
  and the plaintext-marker and stray-envelope tests in the same file
- [x] AC13 -> `tests/test_ops_runbook.py::test_the_runbook_covers_the_sealed_private_data`
- [x] AC14 -> `tests/test_update_offer.py`

### Owner slots

- [ ] AC9: `curl -sI -H "cf-access-token: ..." https://leaving-denver.pages.dev/seller/` after an
  Access login shows `content-security-policy` with `script-src 'self'`, `connect-src 'none'`,
  `frame-ancestors 'none'`. Result: ____
- [ ] AC11: unlock time on the owner's phone, with 1,000,000 iterations, 3 s or less. Result: ____
  (over 3 s: lower `iter`, never below 600,000, and amend ADR-007)

### PR 2 test status

- `make clean && make check` -> 776 passed, 2 skipped, lint clean. The skips are the deploy-only
  envelope test and a Windows-only harness test. With a throwaway fixture
  envelope as `SELLER_SEALED` (the deploy job's condition) the deploy-only test runs too.
- Every test was written before its code. Mutation checks on the browser tests: removing the
  `pagehide` listener, a Lock that keeps the views, and a wrong passphrase that renders a view each
  fail a test. The tier parity test and the CSP browser test were mutation-checked earlier.
- Complexity: `uvx radon cc -s` on `seal.py`, `channels.py`, `cli.py` and `site_builder.py`: every
  function added or changed is A or B (highest: `envelope_problem` B 8, `takedown_steps` B 7);
  `ruff` C901 with max 10 is clean. `seller.mjs` has no complexity tool; its functions are short.

### PR 2 decisions

- **Row logic runs in the browser, not precomputed into the sealed payload.** AC1 fixes the sealed
  keys at `floors, targets, sales, tracking, notes, sealed_at`, so a precomputed table would add
  keys the criterion forbids; "due now" depends on today's date, which a payload sealed days ago
  cannot know; and the public inputs (roster, drops, renewal days) are already public, so the page
  gets them in its CONFIG block. `roundHalfEven` matches Python's rounding, and
  `tests/test_seller_private_logic.py` compares `priceTiers` with `pricing.price_tiers` over a grid
  that includes half cases.
- **No inline script, because of the CSP.** Data moved into `application/json` blocks and code into
  `seller.mjs`, which `script-src 'self'` allows. A `file://` test cannot see a header, so
  `tests/test_seller_csp.py` serves the page over HTTP (lesson-022).
- **The key is dropped after one decryption.** The ADR says a non-extractable key is held in
  memory; the page keeps only the plaintext payload and derives again on the next unlock. Stricter,
  and no longer needs a key to be tracked.
- **Draft items** (private ids not in the public roster) show as id-only "unpublished" rows: their
  titles and prices are not public, and the sealed data does not carry them.
- **Hyphenated EFF words removed** (7,772 words left; five words are still about 64.6 bits): a hyphen
  is a separator, so those four words could not be typed back (lesson-021; ADR-007 notes it).
- **The update offer skips the generate-a-passphrase prompt**: it is a recording, not a rotation,
  so it asks for the existing passphrase twice and nothing else.
- **`gh` gets no stdin unless it is passing a secret**, so a recording cannot hang on a prompt.

## Promotion candidates

- [ ] Lesson for the repo's `docs/lessons/`? no: the lesson (a class named only in a script is
  never compiled) is already lesson-015; this change extended its guard to the seller page.
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? PR 2 implements ADR-007 (already
  merged) and amends it for the 7,772-word list; lessons 021 and 022 added.
- [ ] New pattern candidate for `00_meta/patterns/`? no.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-009-one-seller-tool/` -> `specs/archive/FEAT-009-one-seller-tool/`
  (only after PR 2: the spec covers both)
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
