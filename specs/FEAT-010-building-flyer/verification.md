---
tags: [spec, verification]
created: "2026-10-01"
---

# Verification - FEAT-010-building-flyer

## Evidence

- [x] AC1 (the page) -> `tests/test_flyer.py::test_the_page_is_one_letter_sheet_in_print`, `::test_the_page_needs_no_script_image_or_other_host`, `::test_the_page_resets_the_catalogs_bottom_padding`.
- [x] AC2 (the QR) -> `::test_the_qr_is_exactly_the_matrix_of_the_utm_url` (the module matrix parsed out of the SVG equals `segno`'s for the literal URL), `::test_the_check_notices_another_url`, `::test_the_url_is_the_origin_with_the_print_parameters`, `::test_the_qr_follows_the_origin_the_build_is_given`, `::test_the_address_is_printed_under_the_qr_without_tracking`. A decode of the rendered page by OpenCV (run by hand, not in the suite) returned the exact URL.
- [x] AC3 (no contact, no price) -> `::test_the_flyer_holds_no_phone_in_any_form` (sentinel `+13035550100`, six formats, `sms:`/`tel:`), `::test_the_flyer_holds_no_email_address`, `::test_the_flyer_names_no_price`.
- [x] AC4 (copy from the data) -> `::test_the_categories_come_from_the_data_not_from_the_template`, `::test_a_category_with_nothing_left_is_not_advertised`, `::test_the_car_is_named_by_its_short_title`, `::test_a_sold_car_is_not_mentioned`, `::test_the_date_is_the_departure_date_in_the_data`, `::test_the_date_is_stated_as_a_fact_and_not_as_pressure`, `::test_the_copy_has_no_em_dash`.
- [x] AC5 (hidden, not linked) -> `::test_the_page_is_kept_out_of_search`, `::test_nothing_else_links_to_the_flyer`, `::test_the_site_still_keeps_every_other_crawler_out`.
- [x] AC6 (one Letter page) -> `tests/test_flyer_browser.py`: headless Chrome prints to PDF with the page's own `@page`; one `/Type /Page`, MediaBox 612 x 792, and the content under 95% of the 7.5 x 10 in box. Both tests fail with the body-padding reset removed (checked by editing the built page).
- [x] AC7 (end of sale) -> `tests/test_flyer.py::test_the_end_build_does_not_make_a_flyer`, `::test_a_flyer_left_by_a_catalog_build_is_swept_by_the_end_build`, `::test_the_old_flyer_address_lands_on_the_end_page`, and `tests/test_smoke_end_of_sale.py` unchanged and green.
- [x] AC8 (playbook, stylesheet) -> `::test_the_playbook_says_where_to_print_the_flyer_from`; `tests/test_class_coverage.py` now covers `flyer.html`.

## Test status

- `SELLER_PHONE=+13035550100 make check` -> `701 passed, 1 skipped in 75.53s`, ruff clean.
- The same suite with `seller.sale_over: true` in a scratch edit (reverted) and no `SELLER_PHONE` -> `540 passed, 162 skipped`; the build leaves no `flyer/`.
- Print check by hand: `build/public/flyer/` printed to PDF, `pdfinfo` reports 1 page, 612 x 792 pts (letter); rasterized at 96 dpi and looked at.
- The catalog's output is unchanged: the flyer's strings live in `locales/flyer.yaml`, so they do not enter the catalog's inline `ui_json`.

## Decisions made during implementation

- The address under the QR is the host only (`leaving-denver.pages.dev`): the tracking parameters are for the scan, and nobody types them off paper. The QR keeps the full UTM URL.
- The QR uses error correction M with the 4-module quiet zone: paper gets creased and shadowed on a board.
- The flyer lists only what is still for sale: a category with every item sold, and a sold car, are left out.
- `flyer_url` is the first Python UTM helper; the seller tool builds its links in `seller.mjs`. The flyer adds `utm_medium=print` to the tool's `utm_source` and `utm_campaign=moving-sale`.
- `tests/browser_harness.py:open_page` puts its setup before the first `<script>`, and now falls back to the end of `<head>` for a page with none.
- The two print tests read the live `build/public` and are on `tests/conftest.py`'s end-of-sale skip list; every other flyer test builds a scratch copy and runs in both modes.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-022-a-printed-page-inherits-the-catalogs-body-padding.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: a build-time, pure-Python dependency with no runtime surface; the end-of-sale behaviour is already ADR-008's.
- [x] New pattern candidate for `00_meta/patterns/`? no: it applies to this one sale.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-010-building-flyer/` -> `specs/archive/FEAT-010-building-flyer/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
