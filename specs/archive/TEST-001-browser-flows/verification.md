---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - TEST-001-browser-flows

## Evidence

- [x] AC1 -> `test_the_close_button_closes_the_sheet_and_its_history_entry`, `test_escape_closes_the_sheet_and_its_history_entry`, `test_a_press_on_the_backdrop_closes_the_sheet` (which also checks that the panel fills the dialog and that the click point is outside it), `test_a_drag_from_the_panel_onto_the_backdrop_keeps_the_sheet`, `test_the_close_button_of_other_sheets_closes_them[contact/bundle]`, `test_a_sheet_opened_twice_owns_one_history_entry`, `test_a_reload_with_a_sheet_open_leaves_no_stale_entry`
- [x] AC2 -> `test_back_closes_the_sheet_and_stays_on_the_catalog`
- [x] AC3 -> `test_back_closes_a_contact_sheet_over_an_item_one_level_at_a_time`, `test_escape_closes_a_contact_sheet_over_an_item_one_level`
- [x] AC4 -> `test_a_text_link_with_a_mouse_opens_the_contact_sheet`, `test_a_refused_clipboard_selects_the_number`, `test_an_item_text_link_carries_its_message_into_the_contact_sheet`, `test_the_contact_sheets_own_link_hands_off_to_messages`
- [x] AC5 -> `test_a_text_link_on_a_touch_screen_keeps_the_native_hand_off`
- [x] AC6 -> `test_a_linked_item_opens_and_drops_the_hash`, `test_an_unknown_linked_item_opens_nothing`
- [x] AC7 -> mutation run below

### Mutation run (AC7)

Each mutation was applied to the built `build/public/index.html` (or `styles.css`), and `tests/test_catalog_flows_browser.py` was run against it. All 15 turned the suite red (run after the review fixes):

| Mutation | Failed |
|---|---|
| the `close` listener no longer calls `history.back()` | 6 (every ✕, Escape, backdrop, stacked Escape) |
| any press arms the backdrop (`pressedBackdrop = true`) | 1 (drag) |
| `popstate` closes nothing | 3 (Back, stacked Back, double open) |
| `popstate` closes every sheet | 2 (stacked Back, stacked Escape) |
| no `desktop.matches` check | 1 (touch) |
| `data-native-sms` not honoured | 1 (contact's own link) |
| Copy never confirms | 1 (desktop contact) |
| no clipboard fallback | 1 (refused clipboard) |
| `openSheet` pushes no history entry | 6 |
| the deep link keeps the hash | 2 (both deep-link cases) |
| the link's message is ignored | 1 (item message) |
| `[data-close-sheet]` ignored | 2 (contact and bundle ✕) |
| a reload keeps the stale entry | 1 (reload) |
| no already-open guard in `openSheet` | 1 (double open) |
| `styles.css`: the dialog gets `padding: 1rem` | 1 (backdrop: the panel no longer fills the dialog) |

## Test status

- Test suite: `make check` -> ruff clean, 291 passed (18 new)
- The browser suites (24 tests) passed every run after the review fixes, about 11 s each; before them, 8 runs in a row. The reviewer also ran them 4 times under a CPU overload, all green.
- With fds 3 and 4 free in the parent (`os.closerange(3, 64)` first), the harness still starts Chrome and reads the page.
- No regressions in the existing suite: yes

## Decisions made during implementation

- **Real time over CDP, not virtual time.** `--virtual-time-budget` could not see a dialog's `close` event (lesson-017). `--disable-frame-rate-limit` made it flaky, 2 to 6 failures per run. The harness now drives Chrome over `--remote-debugging-pipe`, with the standard library only, so the no-new-dependency and no-CI-change scope holds.
- **Escape is in scope after all.** Once the harness speaks CDP, a trusted Escape costs one call, so the `requestClose()` stand-in the proposal planned was dropped. The backdrop is a real mouse click too, and the drag is a real press, move and release.
- **Stacked Escape needs a real click.** Chrome groups dialogs opened with no user activation in between, and one Escape then closes the group. With a synthetic `click()` on the text link, Escape closed both sheets and left the item's entry behind. A buyer always clicks, so the test clicks for real over CDP (lesson-017).
- **The string-presence tests stay** (`test_native_dialogs.py`, `test_desktop_contact.py`). They are cheap and name the contract, and these tests prove the behaviour.

## Independent review (reviewer subagent, ce1c723): PASS-WITH-GAPS

No blocker. Dispositions, applied in the next commit unless noted:

| # | Finding | Disposition |
|---|---|---|
| 1 | The page was staged without `styles.css`, so (5,5) hit the dialog's box, not `::backdrop`, and the CSS contract "the panel fills the dialog" was untested | **Applied.** The page is staged next to links to the whole build. The backdrop test asserts that the panel's box equals the dialog's and that the point is outside it. A `padding: 1rem` mutation of `styles.css` now fails. |
| 2 | lesson-017's "the close event never fires" did not reproduce: a quick ✕ click fired it | **Applied.** Re-run with a minimal page: `close()` in the first frame fires the event, and 100 ms or 1 s later it never does. The lesson and the proposal now state the timing and carry the table. |
| 3 | If the pipe ends are fds 3 or 4, `dup2` onto itself keeps close-on-exec | **Applied.** Every end is moved above fd 4 first (`F_DUPFD_CLOEXEC`). Checked with fds 3 and 4 free in the parent. |
| 4 | Per-read deadline only, no overall one; Chrome's stderr discarded | **Applied.** `send` and `wait_for` have a 30 s overall deadline, and Chrome's stderr goes to a log quoted in the failure. |
| 5 | `Page.loadEventFired` could be about:blank's | **Applied.** After it, the harness waits until the page is the staged `file:` page and complete. |
| 6 | `[data-close-sheet]`, the reload neutralisation and the already-open guard survived mutation; Escape on stacked sheets untested | **Applied.** Four new tests (contact and bundle ✕, reload, double open, stacked Escape); all three mutations now fail. |
| 7 | "Poll instead of fixed sleeps" overstated | **Applied.** The proposal's Risks name where fixed waits remain and why. |
| 8 | `--disable-dev-shm-usage` absent | **Declined.** Only needed in containers with a small `/dev/shm`; the suite runs on GitHub's VM runners and on hosts. |

## Independent review (2026-10-03)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer, worked read-only on main at 2cdc798, and ran the `features.json` commands plus the full suite on a clean copy (1042 passed, 2 skipped).

- Verdict: archive. AC1-AC7 hold; AC7 was reproduced on the built page (the `popstate` mutation turns 3 tests red, the backdrop mutation 1).

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-017-virtual-time-starves-dialog-close-events.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: test tooling inside the existing no-new-dependency scope, reversible, with no public contract
- [x] New pattern candidate for `00_meta/patterns/`? no: one project uses the harness so far

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/TEST-001-browser-flows/` -> `specs/archive/TEST-001-browser-flows/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
