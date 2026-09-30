---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - TEST-001-browser-flows

## Evidence

- [x] AC1 -> `test_the_close_button_closes_the_sheet_and_its_history_entry`, `test_escape_closes_the_sheet_and_its_history_entry`, `test_a_press_on_the_backdrop_closes_the_sheet`, `test_a_drag_from_the_panel_onto_the_backdrop_keeps_the_sheet`
- [x] AC2 -> `test_back_closes_the_sheet_and_stays_on_the_catalog`
- [x] AC3 -> `test_back_closes_a_contact_sheet_over_an_item_one_level_at_a_time`
- [x] AC4 -> `test_a_text_link_with_a_mouse_opens_the_contact_sheet`, `test_a_refused_clipboard_selects_the_number`, `test_an_item_text_link_carries_its_message_into_the_contact_sheet`, `test_the_contact_sheets_own_link_hands_off_to_messages`
- [x] AC5 -> `test_a_text_link_on_a_touch_screen_keeps_the_native_hand_off`
- [x] AC6 -> `test_a_linked_item_opens_and_drops_the_hash`, `test_an_unknown_linked_item_opens_nothing`
- [x] AC7 -> mutation run below

### Mutation run (AC7)

Each mutation was applied to the built `build/public/index.html`, and `tests/test_catalog_flows_browser.py` was run against it. All 11 turned the suite red:

| Mutation | Failed |
|---|---|
| the `close` listener no longer calls `history.back()` | 3 (button, Escape, backdrop) |
| any press arms the backdrop (`pressedBackdrop = true`) | 1 (drag) |
| `popstate` closes nothing | 2 (Back, stacked) |
| `popstate` closes every sheet | 1 (stacked) |
| no `desktop.matches` check | 1 (touch) |
| `data-native-sms` not honoured | 1 (contact's own link) |
| Copy never confirms | 1 (desktop contact) |
| no clipboard fallback | 1 (refused clipboard) |
| `openSheet` pushes no history entry | 4 |
| the deep link keeps the hash | 2 (both deep-link cases) |
| the link's message is ignored | 1 (item message) |

## Test status

- Test suite: `make check` -> ruff clean, 286 passed (13 new)
- The browser suites (19 tests) passed 8 runs in a row, 7.4-7.8 s each
- No regressions in the existing suite: yes

## Decisions made during implementation

- **Real time over CDP, not virtual time.** `--virtual-time-budget` could not see a dialog's `close` event (lesson-017). `--disable-frame-rate-limit` made it flaky, 2 to 6 failures per run. The harness now drives Chrome over `--remote-debugging-pipe`, with the standard library only, so the no-new-dependency and no-CI-change scope holds.
- **Escape is in scope after all.** Once the harness speaks CDP, a trusted Escape costs one call, so the `requestClose()` stand-in the proposal planned was dropped. The backdrop is a real mouse click too, and the drag is a real press, move and release.
- **The string-presence tests stay** (`test_native_dialogs.py`, `test_desktop_contact.py`). They are cheap and name the contract, and these tests prove the behaviour.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-017-virtual-time-starves-dialog-close-events.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: test tooling inside the existing no-new-dependency scope, reversible, with no public contract
- [x] New pattern candidate for `00_meta/patterns/`? no: one project uses the harness so far

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/TEST-001-browser-flows/` -> `specs/archive/TEST-001-browser-flows/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
