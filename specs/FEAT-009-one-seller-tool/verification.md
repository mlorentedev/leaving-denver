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
- [x] AC11 -> held until PR 2 (the assistant stayed out of the public build); PR 2's AC12 removes it
  (`tests/test_mobile_poster.py::test_the_local_assistant_is_gone_and_its_pin_with_it`)

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

## PR 2 evidence (ADR-007; criteria in `pr2-encrypted-private-data.md`)

- [x] AC1 -> `tests/test_sealed_build.py::test_no_built_file_holds_a_private_value_or_the_phone`,
  `::test_the_envelope_opens_to_the_allow_list_and_nothing_else`;
  `tests/test_private_isolation.py::test_no_private_fixture_value_reaches_a_public_build`
- [x] AC2 -> `tests/test_sealed_build.py::test_a_build_without_the_secret_has_no_sealed_block_and_says_so`,
  `::test_an_empty_secret_reads_as_unset`, `::test_a_malformed_envelope_fails_the_build_without_echoing_it`;
  `tests/test_sealed_browser.py::test_a_build_without_the_secret_has_no_unlock_and_the_public_half_works`;
  `tests/test_cd_workflow.py` (the deploy job requires `SELLER_SEALED`)
- [x] AC3 -> `tests/test_sealed_browser.py` (before unlocking; wrong passphrase; right passphrase;
  Lock and pagehide; the storage spy, and a test that the spy notices a storage call)
- [x] AC4 -> `tests/test_seal_command.py` (weak, repeated, off-list and mismatched passphrases; no TTY;
  argv refused; exactly two `secret set`, envelope on stdin; the first prompt reads "Passphrase
  (Enter to generate one): "; Enter generates five hyphenated listed words. With a stub `dotf` on
  PATH (it records argv, stdin and environment): `dotf secrets set SELLER_PASSPHRASE` gets the value
  on stdin and nothing reaches stdout or stderr, even when the stub echoes it, only "Saved to
  Bitwarden as SELLER_PASSPHRASE" is printed; a failed save, or no `dotf`, falls back to `tell` (which
  writes to `/dev/tty` and nothing else) and the type-back, and a wrong confirmation calls no `gh`;
  a typed passphrase is offered "Save it to Bitwarden? [y/N]" only when `dotf` exists, and a save
  asked for that fails seals nothing)
- [x] AC5 -> `tests/test_seal_command.py::test_the_worst_case_envelope_is_under_the_secret_budget`
  (measured 33,014 bytes against the 40,000 budget; ADR-007 estimated about 32 KB),
  `::test_an_envelope_over_the_budget_is_refused_and_nothing_is_set`
- [x] AC6 -> `tests/test_sealed_envelope.py`; `tests/test_sealed_build.py::test_the_real_envelope_passes_validation_and_is_only_in_the_seller_page`
  (skipped everywhere but a job that has `SELLER_SEALED`, that is the deploy job)
- [x] AC7 -> `tests/test_sealed_envelope.py::test_the_page_code_opens_what_the_node_sealer_wrote`,
  `tests/test_sealed_browser.py::test_the_right_passphrase_opens_the_views_the_node_seal_wrote`
- [x] AC8 -> `tests/test_sealed_build.py::test_the_envelope_is_in_the_seller_page_only`;
  `tests/test_private_isolation.py::test_the_build_fails_when_the_envelope_is_anywhere_but_the_seller_page`
- [x] AC9 (repository half) -> `tests/test_seller_csp.py`: the middleware sets the policy on every
  `/seller` response and no other path, and the page unlocks under it in headless Chrome served over
  HTTP with no violation; `tests/test_ops_runbook.py::test_no_csp_stops_the_cloudflare_beacon`
  covers every other path. **Owner slot, not done:** the header on the served response after an
  Access login (below).
- [x] AC10 -> `tests/test_seal_command.py::test_the_python_side_hands_the_node_child_stdin_and_nothing_else`,
  `::test_the_command_without_a_terminal_exits_non_zero_and_touches_nothing`,
  `::test_the_workflows_hold_no_age_key_and_never_mention_sops`
- [ ] AC11 -> **owner slot**: unlock time on the phone (below).
- [x] AC12 -> `tests/test_private_isolation.py::test_nothing_in_src_or_the_build_refers_to_the_retired_workspace`
  and the plaintext-marker and stray-envelope tests in the same file
- [x] AC13 -> `tests/test_ops_runbook.py::test_the_runbook_covers_the_sealed_private_data`
- [x] AC14 -> `tests/test_update_offer.py` (including: yes then an empty passphrase aborts with the
  "make ci-secrets" hint, shows nothing and calls no `gh`; mutation-checked) and
  `tests/test_seal_command.py::test_a_resealing_never_generates_and_an_empty_entry_aborts`
- [x] AC15 -> `tests/test_sealed_build.py::test_the_unlock_form_lets_a_password_manager_save_and_fill_the_passphrase`,
  `::test_the_hidden_username_reaches_neither_the_passphrase_nor_the_payload`
- [x] AC16 -> `tests/test_seal_command.py`: the environment value is used with no prompt (on both the
  generating and the re-seal path), refused when weak without echoing it, blank means none, the
  terminal rule still holds, a spy on `subprocess.run` shows Node and gh get no
  `SELLER_PASSPHRASE`, and the stub dotf logs the names in its own environment (none is it). Mutation-checked: a `child_env` that keeps it, and a `save_to_bitwarden` that
  prints dotf's output, each fail a test.
- [x] End of the sale (OPS-011, merged from main) -> `tests/test_sealed_end_of_sale.py`: an end build
  with `SELLER_SEALED` set emits no `seller/` and no envelope, sweeps one an earlier build left,
  `verify_security_guarantees` still validates a provided envelope and still finds one in any file;
  `tests/test_cd_workflow.py`: the deploy gate does not require `SELLER_SEALED` when
  `seller.sale_over` is true, requires it otherwise, and fails closed on an unreadable flag;
  `tests/test_update_offer.py`: with the sale over `post`/`sold`/`reprice` print "The sale is
  over: /seller/ is not built." and ask nothing. The sealed builds in `tests/sealed_helpers.py`
  build the catalog whatever the committed switch says; the isolation, stylesheet and smoke
  leak tests assert the end-mode guarantee instead of being skipped. `make check` passes in both
  modes (switch on, no `SELLER_PHONE`).
- [x] Review round 2 (F1-F9) -> `--yes` on the save (`tests/test_seal_command.py`, the fake dotf
  refuses a create without it); the order seal, save, set and the Bitwarden line when the upload
  fails; a fixed save-failure line and a Node failure that names only its exit code (canary and
  sentinel tests); sops children get no `SELLER_PASSPHRASE`; `iter` capped at 10,000,000
  (`tests/test_sealed_build.py`); an oracle independent of `seller.mjs` in node:crypto
  (`tests/test_sealed_oracle.py`, and the browser opens an oracle-sealed envelope at its own `iter`
  in `tests/test_sealed_browser.py`); `scripts/audit-deploy.sh` (no repository `SELLER_SEALED`,
  a warning when an environment lacks it) and `scripts/smoke.sh` (anonymous `/seller/` carries no
  envelope). `dotf secrets run` keeps stdin a terminal (PTY or inherited fd), so the `has_tty()`
  rule stands; ADR-007 records it with the accepted passphrase risk.

### Owner slots

- [ ] AC9: `curl -sI -H "cf-access-token: ..." https://leaving-denver.pages.dev/seller/` after an
  Access login shows `content-security-policy` with `script-src 'self'`, `connect-src 'none'`,
  `frame-ancestors 'none'`. Result: ____
- [ ] AC11: unlock time on the owner's phone, with 1,000,000 iterations, 3 s or less. Result: ____
  (over 3 s: lower `iter`, never below 600,000, and amend ADR-007)

### PR 2 test status

- `make clean && make check` -> 806 passed, 2 skipped, lint clean. The skips are the deploy-only
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
  `tests/test_seller_csp.py` serves the page over HTTP (lesson-023).
- **The key is dropped after one decryption.** The ADR says a non-extractable key is held in
  memory; the page keeps only the plaintext payload and derives again on the next unlock. Stricter,
  and no longer needs a key to be tracked.
- **Draft items** (private ids not in the public roster) show as id-only "unpublished" rows: their
  titles and prices are not public, and the sealed data does not carry them.
- **Hyphenated EFF words removed** (7,772 words left; five words are still about 64.6 bits): a hyphen
  is a separator, so those four words could not be typed back (lesson-022; ADR-007 notes it).
- **The update offer never generates a passphrase** (owner, 2026-10-01): it is a recording, not a
  rotation, so it asks for the existing passphrase twice, and an empty entry aborts with a hint.
- **`SELLER_PASSPHRASE` is accepted from the environment** (owner, 2026-10-01; ADR-007 decision 3
  amended). The target cannot tell a variable `dotf secrets run` injected from one set by hand, so it
  validates the value like a typed one, keeps the terminal rule, and strips the variable from every
  child. A failed save that the owner asked for on a typed passphrase aborts the seal (the generated
  path already did): a seal under a passphrase Bitwarden does not hold is the state to avoid.
- **A hidden username field** (owner, 2026-10-01) lets the phone's password manager keep one entry
  for the unlock; the key is still derived, used once and dropped.
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
