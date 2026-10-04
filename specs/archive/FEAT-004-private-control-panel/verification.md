---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-004-private-control-panel

## Evidence

All tests run against `tests/fixtures/private.example.yaml` (fake numbers); none reads
`data/private.sops.yaml`.

- [x] AC1 -> `tests/test_panel.py::test_a_row_carries_every_field_the_issue_asks_for`,
  `test_there_is_one_row_per_item_in_inventory_order`,
  `test_an_item_with_no_private_data_has_empty_fields_not_a_crash`,
  `test_the_panel_renders_with_no_private_data_at_all`, `test_the_page_shows_what_the_rows_say`
- [x] AC2 -> `test_price_tiers[...]`, `test_drops_prints_the_tiers_price_tiers_computes`,
  `tests/test_sale_timeline.py`
- [x] AC3 -> `test_the_next_drop_steps_halfway_to_the_floor_at_the_first_drop_window`,
  `test_a_window_the_price_log_already_covers_is_not_the_next_drop`,
  `test_each_drop_recomputes_from_the_asking_price_in_force`,
  `test_the_last_step_is_the_floor_at_the_clear_floors_window`,
  `test_nothing_is_left_to_drop_once_every_window_is_covered`,
  `test_no_next_drop_when_there_is_nothing_to_drop[...]`,
  `test_a_drop_whose_window_has_not_started_is_not_overdue`
- [x] AC4 -> `test_facebook_renew_is_due_seven_days_after_the_latest_posting`,
  `test_an_item_not_on_facebook_has_no_renew_date`,
  `test_days_listed_counts_from_the_earliest_posting_and_stops_at_the_sale`
- [x] AC5 -> `tests/test_panel_records.py` (`test_a_post_is_appended_...`,
  `test_a_reprice_is_appended_...`, `test_nothing_is_written_when_the_history_cannot_be_read_first`,
  `test_a_failed_set_is_reported`, `test_the_public_inventory_never_gains_...`) and
  `test_the_real_sops_accepts_the_values_and_keeps_the_history` (real sops, throwaway age key)
- [x] AC6 -> `test_sold_records_the_price_and_the_day`,
  `test_sold_lists_takedown_only_for_the_channels_the_item_was_posted_on`,
  `test_sold_lists_every_channel_when_nothing_was_recorded`
- [x] AC7 -> `tests/test_panel_isolation.py` (guard, write refusal, default path, and
  `test_no_private_fixture_value_reaches_a_public_build`: two public builds, clean and with the
  fixture loaded, are identical and contain none of the fixture's values)
- [x] AC8 -> `test_the_command_renders_from_a_plain_yaml_and_writes_it_private`,
  `test_the_command_fails_closed_when_the_sops_file_cannot_be_read`,
  `test_the_command_reads_the_sops_file_in_process`
- [x] AC9 -> `test_the_runbooks_document_each_command_and_the_targets_step`,
  `test_the_makefile_exposes_panel_post_and_reprice`

## Test status

- Before: main at e011821 collects 377 tests.
- The new tests were written first and failed on missing modules and functions (collection
  error, then 8 failed and 16 errors in `test_panel_records.py`, then 3 failed in the isolation
  tests before the guard existed).
- After: `make check` -> 454 passed, 1 skipped; ruff (C901 max 10) clean.
- Visual check: headless Chrome screenshot of the panel rendered from the fixture, 1400 px wide:
  one row per item, "log differs from asking" flag, em dashes for missing data.

## Decisions made during implementation

- **Tracking is private** (ADR-006): days listed with no sale is buyer leverage, and public
  tracking costs a commit and a deploy per post.
- **Drop steps follow the log, not fixed tiers.** The tiers start from the live asking price,
  so after a repricing the old "week 2" price would no longer be below asking. A window is
  covered once a reprice is logged on or after it opens; the first uncovered window is next.
- **`sales.<id>` changed shape** from a bare price to `{price, at}`; the real file had no
  `sales:` yet and a bare price still reads.
- **`sops set` rejects a bare JSON list**, so a list grows by setting its next index
  (lesson-019).
- **A test wrote to the real private file** (`sold` without a price now records the date, and
  `test_item_status` stubbed everything but the recorder). Reverted before committing; the
  suite-wide guard in `tests/conftest.py` makes it a failing test (lesson-019).
- **`decrypt_private` raises** where `load_private` returns `{}`; all writers use the former.

## Review findings (independent review of #138)

Fixed, each with a test written first:

- `make sold` a second time with no price wiped the recorded price (`sops set` replaces the
  whole value): with no price only `sales.<id>.at` is set, and a bare-price sale is left alone
  (`test_selling_again_without_a_price_...`, and the real-sops test).
- `item_row` was radon CC 16 (ruff skips ternaries and comprehensions): helpers extracted,
  now 9 (`uvx radon cc -s`).
- A null `tracking:` or `sales:` section raised AttributeError; it reads as empty now, and a
  failed private write (RuntimeError, bad JSON, AttributeError) prints `Error:` instead of a
  traceback (`test_a_null_tracking_section_reads_as_empty`, `test_a_null_section_...`,
  `test_a_failed_write_is_an_error_not_a_traceback`).
- A sale dated before the first posting no longer shows negative days.
- `test_the_built_public_site_has_no_panel_file` asserts the build exists instead of skipping
  (`make test` builds first, so it runs in CI). The 1 skipped test locally is the Windows-only
  collection test; in CI the skips are the real-sops test (no sops there), the private
  workspace gate and the Windows one.
- The conftest guard has its own test (`test_a_test_that_forgets_to_stub_the_recorder_...`),
  and every `cmd_sold` test stubs `load_private`.

Declined, with reasons:

- Next-drop staleness until the inventory price is edited: by design, `log_mismatch` flags a
  log that disagrees with the asking price, and `reprice` does not edit the public inventory.
- `OPEN` uses `<` (overdue once the window's opening day has passed): what AC3 says.
- Future dates, duplicate posts and an unquoted `$(ID)`: owner-only inputs on a local tool.
  A non-positive price is already refused by `reprice`.

## Independent review (2026-10-03)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer, worked read-only on main at 2cdc798, and ran the `features.json` commands plus the full suite on a clean copy (1042 passed, 2 skipped).

- Verdict: archive with a note. AC2-AC6 and AC9 hold, with the tests moved to `tests/test_seller_private_logic.py`.
- Superseded by #146 (ADR-007): AC1 as an artifact (the row logic lives in `assets/seller.mjs`), AC7 and AC8 (no panel and no `build/private/` remain; `verify_security_guarantees` guards the build).
- `features.json` f1-f4, f8 and f9 point at the deleted panel tests; they stay `pending` as the record of the original plan.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-019-an-unreadable-file-is-not-an-empty-one.md
- [x] ADR-worthy decision? yes: docs/adr/adr-006-seller-tracking-stays-private.md
- [x] New pattern candidate for `00_meta/patterns/`? no: single project.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-004-private-control-panel/` -> `specs/archive/FEAT-004-private-control-panel/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
