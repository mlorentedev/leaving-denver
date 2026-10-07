---
tags: [spec, verification]
created: "2026-10-06"
---

# Verification - FEAT-018-bundles-follow-sales

## Evidence

- [x] AC1 -> `test_it_holds_what_is_for_sale_at_the_discount_rounded_down_to_five`, `test_the_price_rounds_down_to_a_multiple_of_five`, `test_a_sold_or_reserved_item_leaves_it_and_lowers_the_price[Sold|Pending]`, `test_the_car_and_unpublished_items_are_never_in_it`, `test_a_free_item_counts_as_an_item_but_adds_nothing_to_the_price`
- [x] AC2 -> `test_a_typed_list_or_price_is_refused[items|bundle_price]`, `test_a_missing_discount_is_refused`, and `test_bundles_integrity` on the real data
- [x] AC3 -> `test_with_fewer_than_two_items_left_there_is_no_bundle`, `test_the_page_renders_without_it`
- [x] AC4 -> `test_the_real_page_offers_it_at_the_derived_price`, `test_page_figures_match_the_data`; the built page reads "Take everything: $500 · All 10 items in one trip. Save $125."
- [x] AC5 -> `test_bundle_sheet_lists_what_is_in_it` over the real data; the built page has `bundle-sofa-tv-table` on sale and no `bundle-living-room`

## Test status

- `uv run pytest` -> 1334 passed, 8 skipped (unit and browser)
- `ruff check` / `ruff format --check` clean
- Before the builder change: `tests/test_everything_bundle.py` -> 11 failed, 1 passed

## Decisions made during implementation

- A reserved item leaves Take everything instead of taking it off sale, so a pickup that falls through puts the item back on the next build.
- Fewer than two items left: no card and no sheet, instead of an "unavailable" card.
- The sheet lists the items cheapest first, in the grid's order.

## Promotion candidates

- none: the rule "derive offers from the data, never type a list that sales invalidate" is already in lesson-037's spirit; no new cross-project insight.
