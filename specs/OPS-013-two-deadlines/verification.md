---
tags: [spec, verification]
created: "2026-10-02"
---

# Verification - OPS-013-two-deadlines

## Evidence

- [x] AC1 (data) -> `tests/test_two_deadlines.py::test_the_real_data_holds_the_owners_two_deadlines_and_no_departure_date`, `::test_the_price_schedule_is_the_owners_explicit_dates` (the four windows, Oct 6-11, 12-15, 16-19, 20-22), `::test_the_schedule_is_written_down_not_computed_from_a_deadline` (moving a deadline moves no window); `tests/test_inventory_ssot.py::test_seller_metadata`.
- [x] AC2 (fail closed) -> `::test_a_missing_or_ill_ordered_schedule_fails_closed` (15 cases, the compact `20261109` included: each key missing, unknown window, unquoted date, non-ISO, impossible date, car before household, windows out of order or equal, giveaway on the deadline, a list), `::test_the_build_refuses_a_bad_schedule`, `::test_the_end_build_needs_no_dates`.
- [x] AC3 (countdown) -> `::test_while_household_items_are_for_sale_the_countdown_targets_their_deadline`, `::test_a_pending_household_item_still_counts_as_for_sale`, `::test_with_no_household_item_left_the_countdown_targets_the_car[hidden|sold]`, `::test_a_sold_car_does_not_move_the_household_deadline`, `::test_the_meta_description_month_follows_the_same_rule`; `tests/test_build_contract.py::test_locales_cover_every_deadline_month`, `::test_countdown_updates_in_browser_from_the_deadline_in_the_data`.
- [x] AC4 (copy) -> `::test_the_car_card_says_it_is_available_until_the_car_deadline`, `::test_a_car_that_is_not_available_does_not_claim_to_be[Pending|Sold]`, `::test_the_hero_names_what_is_still_for_sale`, `::test_the_page_without_the_car_still_says_furniture_and_tech`, `::test_the_hero_no_longer_claims_a_month_the_owner_is_not_leaving_in`; `tests/test_build_contract.py::test_spanish_ui_and_sms_are_localized`.
- [x] AC5 (flyer) -> `::test_the_flyer_states_both_dates_and_drops_the_everything_claim`, `::test_a_sold_car_leaves_only_the_household_date`, `::test_with_no_household_item_left_the_flyer_names_only_the_car`, `::test_the_flyer_dates_come_from_the_data`; `tests/test_flyer.py` (figures on the page are 23, 9 and the car's name).
- [x] AC6 (seller tool) -> `::test_the_seller_tool_page_carries_the_explicit_drop_days`, `::test_the_seller_tool_gets_the_days_the_windows_open`, `::test_drops_prints_the_explicit_windows`; `tests/test_seller_private_logic.py` (next drop on the explicit days; `test_no_next_drop_when_there_is_nothing_to_drop[2019-ford-escape-sel-awd]` for the car).
- [x] AC7 (close-out) -> `::test_the_closeout_snippet_hides_unsold_household_items_and_nothing_else` (the snippet is taken out of `docs/runbooks/decommission.md` and run on a copy of the real data), `::test_after_the_closeout_the_page_targets_the_car_and_the_old_share_page_is_gone`; `tests/test_decommission_runbook.py` (section order, Oct 23 does not end the sale, the sale is turned off with the car).
- [x] AC8 (gates) -> below.

## Test status

- `SELLER_PHONE=+13035550100 make check` -> `1034 passed, 2 skipped in 151.90s`, ruff clean (main before the change: `992 passed, 2 skipped`).
- The same gate with `seller.sale_over: true` added in a scratch edit (restored from a copy, never committed), run as `env -u SELLER_PHONE -u SELLER_SEALED make check` -> `872 passed, 164 skipped in 107.24s`. The first run failed on one new test that built the catalog from the data with the switch on; the test now removes the switch from its own copy.
- Screenshots of the built catalog (EN, ES) and the flyer were read in headless Chrome.
- Not run: a real deploy. The countdown, the car card and the flyer are read from a local build; check them on the first deploy after merge.

## Decisions made during implementation

- Windows are listed by their opening day. The owner gave the first two windows as opening days and the last two as ranges; the ranges are exactly "to the day before the next one opens", so one rule gives all four.
- The hero line lost "I am relocating in <month>": the month was the single deadline, and a household-only deadline in October would have been read as the owner moving then. The countdown line and the car card carry the dates.
- The page's title and hero depend on what is for sale (both, household only, car only), because the close-out leaves the car alone on the page.
- Listing copy in `/seller/` keeps "in November", from `vehicle_deadline`.
- The car gets no dated next-drop suggestion in `/seller/`; `leaving-denver drops` keeps printing its price tiers.
- Archived specs and lessons, and ADR-007/008, keep the single date (history).

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-027-one-date-was-three-facts.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: a data shape local to this repo, recorded in the proposal.
- [x] New pattern candidate for `00_meta/patterns/`? no.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/OPS-013-two-deadlines/` -> `specs/archive/OPS-013-two-deadlines/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder
