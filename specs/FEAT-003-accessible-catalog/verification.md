---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-003-accessible-catalog

## Evidence

- [x] AC1 -> `tests/test_readable_text.py` (ground-aware after PR-Agent caught two dark-card regressions on #94)
- [x] AC2 -> `test_every_sheet_is_a_labelled_dialog`, `test_page_behind_an_open_dialog_does_not_scroll`
- [x] AC3 -> `test_sheets_open_modally_and_back_closes_them` (static) + CDP run below (behaviour)
- [ ] AC4 -> PR 3, blocked on the owner

## Test status

- `make check` -> 137 passed
- Headless Chrome (390x844) over CDP against `feat-native-dialogs.leaving-denver.pages.dev`, real mouse/key events and `Page.navigateToHistoryEntry` for Back:
  item card opens `itemSheet` modal, `history.state={sheet}`, html overflow hidden; Escape closes and drops the entry; reopen + Back closes and stays on the page; bundle card opens its sheet; backdrop tap, close button and "Close" all close and drop the entry; focus returns to the card each time; Back with nothing open leaves the page.
- Note: the interactive Chrome window was hidden (`visibilityState: hidden`), where Chrome dispatches no dialog `close` events at all; behaviour was therefore verified headless.

## Decisions made during implementation

- History: one `pushState` per open sheet; `close` calls `history.back()` only while that sheet's entry is current, so a close caused by Back (popstate) does not go back twice.
- Styling moved to `dialog.sheet` / `::backdrop` in `public.css`; the panels keep their classes.

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive` refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a `00_meta/` path is looked up in the vault.

- [ ] Lesson for the repo's `docs/lessons/`? <yes: path / no: reason>
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? <yes: path / no: reason>
- [ ] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. <yes: path / no: reason>

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-003-accessible-catalog/` -> `specs/archive/FEAT-003-accessible-catalog/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
