---
tags: [spec, verification]
created: "2026-10-01"
---

# Verification - OPS-011-end-of-sale

## Evidence

- [x] AC1 (no phone, no item) -> `tests/test_end_of_sale.py::test_no_file_carries_the_phone_in_any_form`, `::test_no_file_names_an_item`, `::test_nothing_but_the_end_page_and_its_plumbing_is_published`. The sentinel is `+13035550100`, checked in six formats and with `sms:`, `tel:`, every item and bundle id of the real inventory, and `data-item=`.
- [x] AC2 (the end page) -> `::test_the_end_page_says_so_in_its_language[...]`, `::test_a_shared_link_previews_as_sale_over`, `::test_the_end_page_is_still_kept_out_of_search`.
- [x] AC3 (nothing else is served) -> `::test_old_share_links_land_on_the_end_page`, `::test_a_stale_catalog_is_swept_from_the_output` (a catalog left in the output by an earlier build is removed).
- [x] AC4 (builds with no secrets) -> `::test_the_end_build_needs_no_phone_and_no_private_data`: `build_all` with no `SELLER_PHONE`, and `load_private`, `seller_phone`, `sync_all_photos` and `build_private_workspace` all raising if called.
- [x] AC5 (default unchanged) -> `::test_the_switch_defaults_to_off`, `::test_the_switch_must_be_a_boolean`, `::test_with_the_switch_off_the_catalog_is_built`, and the whole existing suite in normal mode: 653 passed, 1 skipped.
- [x] AC6 (smoke follows the mode) -> `tests/test_smoke_end_of_sale.py` (passes on a served end build; fails on `sms:`/`tel:` in either language, a missing redirect, an ES page that is not the end page, a missing stylesheet) and `tests/test_smoke_script.py` (still passes against the normal build).
- [x] AC7 (runbook and ADR) -> `tests/test_decommission_runbook.py`; `docs/runbooks/decommission.md`, `docs/adr/adr-008-keep-the-pages-project-after-the-sale.md`.

## Test status

- `SELLER_PHONE=+15555550100 make check` -> `653 passed, 1 skipped in 62.15s`, ruff clean.
- The same gate with `seller.sale_over: true` committed in a scratch edit (reverted), and no `SELLER_PHONE`: `292 passed, 362 skipped in 15.77s`. Before the conftest skip list it was 141 failed and 27 errors (lesson-021).
- The `_redirects` risk (Pages with `functions/_middleware.js` present) is closed by a real rehearsal on 2026-10-01: an end-mode build deployed with `make deploy BRANCH=endsale-rehearsal` gave `/` 200, `/es/` 200, `/i/sofa-sleeper/` 302 to `/`, `/es/i/sofa-sleeper/` 302 to `/es/`, `/seller/` 302 to the Access login, and `scripts/smoke.sh` printed "smoke OK (sale over)". The deployment was deleted afterwards (404). A dispatched preview would not do, since it builds `main` with the switch off. The runbook's "Before Nov 8" repeats it a week ahead.
- The runbook's commands were read against the repository (secret names from the workflows, Make targets); none was run, since each changes the owner's accounts.

## Decisions made during implementation

- The end build sweeps the output root down to its own files: `build_all` runs the photo sync and the stylesheet step before the page build, and an earlier catalog build leaves `catalog/`, `i/` and `seller/` behind.
- The end build skips the local private workspace as well as the photos, so nothing private is read.
- The smoke's end-mode block exits early and repeats the robots, nosniff and private-path checks, so the catalog block of the shared script is not re-indented.
- `tests/conftest.py` skips the catalog tests one by one when the switch is committed on, because `make check` is the gate of the PR that flips it. Not by module: the Access guard, the phone and realized-price isolation tests stay on. Tests that build a scratch site from the committed inventory get the switch stripped (an autouse fixture), so they keep testing the catalog; a guard fails if a phone, private, isolation, access or secret test is on the skip list.
- The runbook sequences Nov 8 (flip, deploy, delete old deployments) before Nov 15 (secrets): the deploy job refuses to run without `SELLER_PHONE`.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-021-a-switch-that-retires-a-feature-retires-its-tests.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? yes: docs/adr/adr-008-keep-the-pages-project-after-the-sale.md
- [x] New pattern candidate for `00_meta/patterns/`? no: it applies to this one sale; nothing recurs across projects yet.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/OPS-011-end-of-sale/` -> `specs/archive/OPS-011-end-of-sale/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
