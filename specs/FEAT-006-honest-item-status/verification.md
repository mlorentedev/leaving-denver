---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-006-honest-item-status

## Evidence

- [x] AC1 -> `test_unknown_status_fails_the_build`
- [x] AC2 -> `test_sold_items_sort_last_and_the_rest_keep_their_order`, `test_sold_card_is_last_dimmed_and_struck`
- [x] AC3 -> `test_bundle_with_a_taken_item_is_unavailable`, `test_bundle_with_a_sold_item_is_off_sale`, `test_sheet_logic_follows_the_status`
- [x] AC4 -> `test_sold_card_is_last_dimmed_and_struck`, `test_pending_card_says_pending_pickup`, `test_sheet_logic_follows_the_status`
- [x] AC5 -> `test_availability_line_counts_from_the_data`
- [x] AC6 -> `test_status_commands_set_the_status_and_rebuild`, `test_status_commands_reject_an_unknown_id`, `test_realized_price_stays_private`

## Test status

- `make check` -> 142 passed
- Headless Chrome 390x844 on a local build with `sofa-sleeper` Sold and `dell-monitor-32` Pending:
  - The line reads "10 of 12 available · 1 sold".
  - The sofa card is last, with a faded photo, a Sold badge and a struck price; the monitor card shows "Pending pickup".
  - "Sleeper sofa + topper", "Home office" and "Take everything" read "No longer available"; "Living room media" is still on sale.
  - Item sheets: the sofa has no text link (grey pill); the monitor has an amber pill and keeps its link.
  - Office chair and topper: no upsell, since their bundles are off sale. Coffee table: upsell to "Living room media".
- No regressions: the full suite passes.

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

-
-

- A sold card fades only its photo (`opacity-60 grayscale`). Fading the whole card took "No longer available" and the titles below AA; WCAG exempts only inactive components, and these still open their sheet.
- A pending item keeps its text link: a backup buyer is worth having when a pickup falls through. Its bundles still go off sale, since the offer cannot be honoured while it is reserved.
- "Take everything" goes off sale with the first reservation or sale. Re-pricing it as "take what's left" is an owner decision in the data, not a derived figure.

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive` refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a `00_meta/` path is looked up in the vault.

- [ ] Lesson for the repo's `docs/lessons/`? <yes: path / no: reason>
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? <yes: path / no: reason>
- [ ] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. <yes: path / no: reason>

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-006-honest-item-status/` -> `specs/archive/FEAT-006-honest-item-status/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
