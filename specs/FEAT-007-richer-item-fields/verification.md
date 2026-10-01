---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-007-richer-item-fields

## Evidence

Tests are in `tests/test_richer_item_fields.py` (builder and built pages) and
`tests/test_richer_item_fields_browser.py` (the sheet in headless Chrome).

- [x] AC1 -> `test_no_item_carries_a_second_asking_price`,
  `test_the_build_refuses_an_item_with_a_second_price`,
  `test_the_build_refuses_an_item_with_no_price`, `test_the_published_price_is_the_one_in_the_data[en|es]`.
  Prices unchanged: a one-off script compared `recommended_list_price`, `original_price` and the
  bundle prices of `origin/main:data/inventory.yaml` with the branch: identical for all 14 items.
- [x] AC2 -> `test_every_household_condition_is_on_the_scale_and_the_car_keeps_its_wording`,
  `test_the_spanish_labels_live_once_in_the_locale_not_on_each_item`,
  `test_the_page_shows_the_scale_label_in_its_language[en|es]`,
  `test_the_build_refuses_a_condition_off_the_scale`, `test_the_car_may_use_its_own_scale`,
  `test_the_private_poster_gets_the_spanish_label_from_the_locale`
- [x] AC3 -> `test_flaws_reach_the_published_item_in_each_language`,
  `test_the_build_refuses_flaws_with_no_matching_spanish[3 cases]`,
  `test_the_sheet_template_lists_flaws_as_text_and_hides_the_empty_list`,
  `test_the_seller_copy_lists_the_flaws`, `test_every_flaw_in_the_data_has_a_spanish_line`;
  in Chrome: `test_the_sheet_shows_badges_and_flaws_from_the_data[en|es]` (flaws set in the page
  render as text, markup is not interpreted, an item with none hides the section)
- [x] AC4 -> `test_the_discount_is_the_whole_percent_below_retail[6 cases]`,
  `test_there_is_no_discount_without_a_retail_figure`, `test_a_free_item_has_no_discount`,
  `test_the_car_has_no_discount_against_its_new_price`,
  `test_every_real_item_shows_its_own_discount_on_the_card[en|es]`,
  `test_a_sold_item_shows_no_discount_badge`
- [x] AC5 -> `test_the_thresholds_are_over_48_in_over_50_lb_and_over_75_lb[9 cases]`,
  `test_the_build_refuses_a_size_or_weight_that_is_not_positive_numbers[9 cases]`,
  `test_the_published_item_carries_the_flags_and_no_measurements`,
  `test_the_labels_come_from_the_locale`, `test_a_sold_item_shows_no_size_badge`,
  `test_every_size_in_the_data_is_the_owners_own_number`,
  `test_a_weight_in_the_data_names_its_source`,
  `test_a_soft_item_that_fits_a_sedan_gets_no_truck_badge`, `test_the_real_big_items_say_so[en|es]`
- [x] AC6 -> `test_items_sort_by_ascending_price_with_sold_last_and_ties_in_data_order`,
  `test_a_free_item_sorts_by_its_list_price_and_does_not_lead_the_grid`,
  `test_the_real_grid_runs_from_cheap_to_dear_with_sold_last[en|es]`
- [x] AC7 -> the existing suites, unchanged in intent: `test_class_coverage.py`,
  `test_readable_text.py`, `test_inventory_ssot.py` (UNBACKED_CLAIMS, pickup, payment),
  `test_verify_the_car.py`. Two assertions about the Spanish condition moved from "typed on each
  item" to "the locale's label" (`test_build_contract.py`, `test_item_sheet_detail.py`).

## Test status

- Before: `make check` -> 376 passed, 1 skipped.
- The new tests were written first and failed (51 failed, 10 passed) with none of the fields.
- After: `make check` -> 440 passed, 1 skipped (64 new tests; lint clean, C901 under 10).
- Visual check: a 390 px headless Chrome screenshot of `/es/` shows the "% off" badge on every
  card and "Necesita camioneta o SUV" under the sofa and the convertible desk, wrapping inside
  the two-column grid, no horizontal overflow.

## Decisions made during implementation

- **The price key stays `recommended_list_price`.** The published field is already `price`;
  renaming the YAML key would touch the CLI, the private poster, the runbook and five test
  files for no visible change. `current_asking` is deleted and refused by the build.
- **`current_asking` follow-up (owner).** Its values were never published as a price, but they
  sat in the public repository and remain in git history. Whatever the owner still wants as
  private targets can be added with `sops set` in `data/private.sops.yaml` (not touched here).
- **Condition mapping.** Good, Good Condition and Great Condition -> Used - Good ("Great" is not
  on the scale; rounded down, no hype); Like New and Like New (Used Once) -> Used - Like New
  ("used once" stays in the air mattress's specs). Spanish labels are this project's wording, not
  claimed to be Facebook's. The car keeps its vehicle wording (different Facebook scale).
- **No flaws, no weights.** None is known or sourced, so none is written: "2-person lift" renders
  for nothing today. Owner follow-up: weigh the sofa, the desk and the TV; add `weight_lb` with a
  `weight_source`. The sofa note already says two people carry it.
- **`size_in` only where the owner's string is W x D x H**, as the buyer carries it: sofa,
  TV, convertible desk, coffee table, stools, TV stand, chair, nightstand, side table. Omitted for
  the monitor (diagonal), dinnerware, the car, and the mattress topper and air mattress (they
  roll or fold; their pickup notes say a sedan takes them, so a truck badge would contradict them).
  Result: "Needs truck/SUV" on the sofa and the convertible desk.
- **No "% off" for the car** (a used car against its new sticker is not a comparable) or for Sold
  items. Free items never show it.
- **Sort: ascending, free by list price.** Documented in the proposal.
- **Generated copy.** The `/seller/` generator lists flaws. It gets no size badge: it reads the
  English public items, which carry flags but no labels. The old private poster tool is untouched
  except that it keeps getting `es.condition`, now filled from the locale in the private build.

## Promotion candidates

- [ ] Lesson for the repo's `docs/lessons/`? no: nothing surprising.
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: new derived fields on the existing static catalog.
- [ ] New pattern candidate for `00_meta/patterns/`? no: single project.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-007-richer-item-fields/` -> `specs/archive/FEAT-007-richer-item-fields/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
