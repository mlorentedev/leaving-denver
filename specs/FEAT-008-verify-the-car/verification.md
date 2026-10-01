---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-008-verify-the-car

## Evidence

All tests are in `tests/test_verify_the_car.py` unless noted.

- [x] AC1 -> `test_the_section_shows_the_vin_and_the_three_official_hosts[en|es]`,
  `test_the_section_sits_under_the_car_and_not_in_the_footer`
- [x] AC2 -> `test_every_link_is_https_on_an_official_host_or_one_of_the_cars_photos[en|es]`,
  `test_the_allow_list_rejects_look_alike_hosts`,
  `test_the_build_refuses_a_check_that_is_not_https_on_an_official_host` (http, a reseller,
  suffix look-alikes, userinfo, protocol-relative, `javascript:`)
- [x] AC3 -> `test_evidence_links_to_photos_the_car_has_and_the_build_ships[en|es]`,
  `test_the_build_refuses_evidence_that_is_not_one_of_the_cars_photos`
- [x] AC4 -> `test_the_section_hands_over_a_fresh_certificate_and_warns_about_paid_report_links[en|es]`
- [x] AC5 -> `test_the_section_claims_no_service_history_and_shows_no_personal_data[en|es]`
  (the Carfax and service-history assertions flip on purpose when #28 and #34 land);
  `tests/test_inventory_ssot.py::test_no_unbacked_vehicle_claims` still covers the new
  template and data
- [x] AC6 -> `test_the_data_carries_both_languages_for_every_entry`,
  `test_the_template_hardcodes_no_check_and_no_evidence`,
  `test_a_car_with_verify_data_renders_it_from_the_data`,
  `test_a_car_without_verify_data_renders_no_section`,
  `test_the_build_refuses_verify_data_on_a_car_with_no_vin`

## Test status

- Before: `make check` -> 331 passed, 1 skipped.
- The new tests were written first and failed (23 failed, 2 passed) with no section and no
  data.
- After: `make check` -> 356 passed, 1 skipped (25 new tests; lint clean).
- Visual check: a 390 px headless Chrome screenshot of `/es/` shows the section under the
  car's card, one column, no horizontal overflow.

## Decisions made during implementation

- **NHTSA link.** NHTSA's pages answered 403 to a script from the build host, so a VIN
  deep-link format could not be confirmed from NHTSA itself. The section links
  `https://www.nhtsa.gov/recalls` and shows the VIN, selectable, to paste. If NHTSA's
  documented format is confirmed later, it is a one-line change to the data.
- **Allow-list in code, labels in data.** `OFFICIAL_CHECK_HOSTS` lives in `site_builder.py`:
  a data-only change can add a link but not a new host, so a reseller cannot slip in through
  `inventory.yaml`. The test keeps its own copy of the list so it fails if the builder's widens.
- **Evidence is a photo, not a URL.** Evidence entries name one of the car's photos and link
  to the built JPEG. The photo must be among the item's built photos or the build fails.
- **Spanish copy by entry id** under `es.verify`, falling back to English per field like the
  rest of the overlay; the test requires it complete for the car.
- **Emissions wording.** "fresh, unused certificate" (the existing spec line), not the
  phrase `UNBACKED_CLAIMS` bans.
- **NICB note** says "theft and total-loss (salvage) records", not flood: that is what the
  tool documents, and the page claims nothing it cannot back.

## Promotion candidates

- [ ] Lesson for the repo's `docs/lessons/`? no: nothing surprising; the allow-list reasoning is in the spec and the code comment.
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: a new section on the existing static catalog, no architectural change.
- [ ] New pattern candidate for `00_meta/patterns/`? no: single project.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-008-verify-the-car/` -> `specs/archive/FEAT-008-verify-the-car/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
