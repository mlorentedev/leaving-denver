---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-003-accessible-catalog

## Evidence

- [x] AC1 -> `tests/test_readable_text.py` (ground-aware after PR-Agent caught two dark-card regressions on #94)
- [x] AC2 -> `test_every_sheet_is_a_labelled_dialog`, `test_page_behind_an_open_dialog_does_not_scroll`
- [x] AC3 -> `test_sheets_open_modally_and_back_closes_them` (static) + CDP run below (behaviour)
- [x] AC4 -> `tests/test_desktop_contact.py` (static) + CDP run below (behaviour)
- [x] AC5 -> `test_sticky_bar_clears_the_home_indicator`, `test_body_and_sheets_clear_the_safe_areas` (compiled CSS: body clearance and both sheet-panel rules); computed styles below. Not yet checked on a notched device.
- [x] AC6 -> `test_filtering_announces_the_result_count`; CDP below

## Test status

- `make check` -> 137 passed (PR 2); 147 passed (PR 3)
- Headless Chrome (390x844) over CDP against `feat-native-dialogs.leaving-denver.pages.dev`, real mouse/key events and `Page.navigateToHistoryEntry` for Back:
  item card opens `itemSheet` modal, `history.state={sheet}`, html overflow hidden; Escape closes and drops the entry; reopen + Back closes and stays on the page; bundle card opens its sheet; backdrop tap, close button and "Close" all close and drop the entry; focus returns to the card each time; Back with nothing open leaves the page.
- Note: the interactive Chrome window was hidden (`visibilityState: hidden`), where Chrome dispatches no dialog `close` events at all; behaviour was therefore verified headless.

- PR 3, headless Chrome over CDP against a local server of `build/public` (clipboard needs a secure context; localhost is one), desktop pointer via a `matchMedia` stub (lesson-014):
  sticky "Text me" is prevented and opens `contactSheet` with the number and the generic message; Copy writes the 11-digit number and the button reads "Copied"; Escape closes and returns focus to the link. From an item sheet, "Text about this" stacks the contact sheet with the item message; Back closes the contact sheet only, a second Back the item sheet; the ✕ closes the contact sheet only. With touch emulation (`pointer: coarse`) the sticky link keeps `sms:` and no sheet opens.
  AC5/AC6 (ES page): body padding-bottom 96px, sticky bottom 16px, sheet panel padding-bottom 24px with zero insets (desktop); the Bedroom chip writes "3 artículos visibles" to `#resultCount` with 3 cards visible.

## Decisions made during implementation

- History: one `pushState` per open sheet; `close` calls `history.back()` only while that sheet's entry is current, so a close caused by Back (popstate) does not go back twice.
- Styling moved to `dialog.sheet` / `::backdrop` in `public.css`; the panels keep their classes.
- PR 3: `popstate` closes only the open sheets whose id is not the current entry's, so stacked sheets close one per Back.
- PR 3: one document-level click listener covers every `sms:` link, including those built later in JS (item sheet, upsell).

## Independent adversarial review (2026-09-30)

Reviewer: the `reviewer` subagent, not the implementer. It ran read-only against `feat/desktop-contact`, which holds all three PRs. Verdict: **PASS-WITH-GAPS, no blocker**; `make check` 147 passed at the time.

| # | Finding | Disposition |
|---|---|---|
| 1 | Major: the dialog and contact tests are string-presence checks, and the CDP runs are not committed | **Ticketed** #99, which adds a real browser suite in CI. The CDP evidence stays recorded above. |
| 2 | Major: the fine-pointer interception removes the `sms:` path a Mac with Messages could use | **Applied** (PR 3): the contact sheet has "Open in Messages instead" (`data-native-sms`, not intercepted), and verified over CDP. |
| 3 | Item sheet ✕ has no accessible name | **Applied** (PR 2): `aria-label` plus `test_icon_only_close_buttons_are_named`. |
| 4 | "1 items shown"; the same chip twice is not re-announced | **Applied**: added `results_one`. The repeat case is **declined**: the count did not change, so there is nothing new to announce. |
| 5 | A text drag from the panel onto the backdrop closes the sheet | **Applied** (PR 2): only a press that starts on the backdrop closes it (`pointerdown` guard). |
| 6 | The Copy fallback gives no hint, and "Copied" is not announced | **Applied**: the fallback text reads "Selected: press Ctrl+C or ⌘C", and the button is `aria-live="polite"`. The display and clipboard formats differ on purpose: dialers accept both. |
| 7 | A stale sheet entry after Forward or a reload makes Back take two presses | **Applied for reload** (PR 2): the load-time `replaceState(null)` clears it. **Declined for Forward**: rare in a one-page catalog, and reopening the sheet would need the item id in the state. |
| 8 | No fallback when `showModal()` / `:has()` are missing (Safari < 15.4) | **Declined**: iOS 15.4 shipped in March 2022, and in-app browsers use the system WebView. |
| 9 | Safe-area CSS: `sm:p-7` override; left/right body insets strip the header/footer; sticky bar ignores side insets | **Applied** for `sm` (1.75rem restored under 640px+). **Declined** the rest: the strips are `#fbfbfb` against white, and the sticky bar is centred at `max-w-sm`. |
| 10 | The 12 px test is a denylist | **Declined**: the three tokens are the only arbitrary sizes Tailwind classes here produce, and the template has no other `text-[..]`. |

## Second independent review, merged state (2026-09-30)

Reviewer: the `reviewer` subagent, not the implementer. It reviewed main `2759ab7` after #94–#96 had merged. It ran a computed-style audit in headless Chrome over both locales, with every dialog open, and found nothing under 12 px or under 4.5:1. It also mutated the contrast guard, which caught `emerald-700→600` and a dark-ground `neutral-500`. All six `features.json` commands pass. Verdict: **PASS-WITH-GAPS, no blocker; archivable after housekeeping.**

| # | Finding | Disposition |
|---|---|---|
| 1 | Major: AC5's body and sheet-panel insets are untested (deleting both rules stayed green), and f5 named only the sticky bar | **Applied**: `test_body_and_sheets_clear_the_safe_areas` reads the compiled CSS and went RED with the panel `env()` removed. f5 now names all three. Device check on a notch is still owed. |
| 2 | Major: scroll lock is proven by a regex and desktop Chrome only | **Ticketed** in #99 (touch-emulated drag on the backdrop), plus an owner device check on iOS Safari and the Facebook in-app browser |
| 3 | Minor: the contrast guard misses opacity modifiers, arbitrary colours, `emerald-700` on grey and arbitrary sub-12 px sizes; the poster assistant is unchecked | **Ticketed** #106 (TEST-002). There is no current instance, per the audit. |
| 4 | Minor: stacked-sheet Back order, the one-entry rule and focus return have no test | **Ticketed** in #99 |
| 5 | Minor: a click before `initDynamicContacts` reads `href="#"` | **Ticketed** #107 (BUG-010) |
| 6 | Minor: Forward onto a stale entry needs two Backs | **Declined**, as in finding 7 above |
| 7 | Question: pointer-less and non-Mac desktops fall through to `sms:`; the desktop branch is verified only through a `matchMedia` stub | **Accepted.** "Open in Messages" covers Macs, and lesson-014 records the stub and the one manual device check. |

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive` refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a `00_meta/` path is looked up in the vault.

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-014-headless-chrome-has-no-pointer.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: native `<dialog>` and the desktop contact sheet are implementation choices inside ADR-002's contact model, not a new decision
- [x] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. no: single-project UI work; the reusable part (headless pointer) is a local lesson

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-003-accessible-catalog/` -> `specs/archive/FEAT-003-accessible-catalog/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
