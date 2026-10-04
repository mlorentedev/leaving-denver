---
id: "TEST-001-browser-flows"
type: spec
status: implementing # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#99"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# TEST-001-browser-flows

> **Naming**: file lives at `<repo>/specs/TEST-001-browser-flows/proposal.md`. `TEST-001-browser-flows` is `AREA-NNN-slug` (e.g. `TOOL-001-secret-drift`).

## Why

<!-- from issue #99: TEST-001: run the catalog's sheet and contact flows in a real browser in CI -->

The sheet and contact tests (`test_native_dialogs.py`, `test_desktop_contact.py`) only check that strings such as `showModal()`, `popstate` and `navigator.clipboard.writeText` appear in the script, so a deleted or inverted handler still passes. The behaviours were proven once, by hand over CDP, and nothing re-checks them. A regression in Back or in the contact sheet would drop buyers inside Facebook's in-app browser, which is where most of them arrive.

## What

A behaviour suite, `tests/test_catalog_flows_browser.py`, runs the built EN page in headless Chrome and checks:

1. **Close paths.** An item sheet closed by its ✕ button, by the Escape key, and by a click on the backdrop leaves no sheet open, and `history.state` is back to `null`. So do the contact and bundle sheets' ✕. A drag that starts inside the panel and ends on the backdrop keeps the sheet open. Escape and the mouse are real input, sent over the DevTools protocol. A sheet opened twice owns one history entry, and a reload with a sheet open leaves no stale entry.
2. **Back.** `history.back()` with an item sheet open closes it, and the catalog stays.
3. **Stacked sheets.** With a fine pointer, a text link inside the item sheet opens the contact sheet over it. One Back closes the contact sheet only, and a second Back closes the item. Escape also closes one level.
4. **Desktop contact.** With a fine pointer, the contact sheet shows the number, the message taken from the link, and a native `sms:` link. Copy writes the full number and says "Copied". A refused clipboard selects the number and shows the fallback hint.
5. **Touch keeps `sms:`.** Without a fine pointer, a text link is not intercepted: no sheet opens and the click's default action is kept.
6. **Deep link** (from FEAT-002). `#<id>` opens that item and drops the hash, and an unknown id opens nothing.

**How.** The harness from FEAT-002 (`tests/test_share_button_browser.py`) moves to a shared helper, `tests/browser_harness.py`, and is reused:
- the page is staged next to links to the rest of the build, so its stylesheet applies, and a `<script>` injected before the page script installs the stubs (`matchMedia` for the fine pointer, `navigator.clipboard`);
- Chrome runs headless in real time and is driven over the DevTools protocol on `--remote-debugging-pipe`, with the standard library only;
- once the page has loaded, async steps run in it and return a JSON result, and key and mouse input go in as trusted events.

The FEAT-002 harness used `--dump-dom --virtual-time-budget`. Under virtual time, Chrome soon stops producing frames, and a dialog closed after that never gets its `close` event (lesson-017), so it could not test the close paths.

**Scope limits.**
- No new dependency and no CI change: GitHub's ubuntu runners ship Chrome, and the suite is skipped where there is none. This replaces the issue's Playwright proposal and the CI-time decision it needed.
- The string-presence tests stay as cheap guards.

## Out of scope

- Facebook's in-app browser itself, and real iOS or Android devices. Those remain owner checks.
- Visual layout checks.

## Risks / open questions

- **Chrome versions.** The CI runner's Chrome can change under the suite. Every protocol call has a 30 s deadline, and a page that never answers fails the test with Chrome's own log ("Chrome stopped answering"), so a breaking change shows up as a red test, not a hang or a silent pass.
- **Timing.** Real time can race. Steps poll for the state they expect with a deadline (`until`). Fixed waits remain in two kinds of places:
  - where nothing may change (touch, the contact sheet's own link, the drag), for 100-200 ms;
  - where the awaited change is a chain of already-settled promises (the Share and Copy stubs).

## Acceptance criteria

- [x] AC1: each close path (button, Escape, backdrop) leaves no sheet open and `history.state === null`. A drag from the panel does not close.
- [x] AC2: Back closes an open item sheet, and the page stays on the catalog.
- [x] AC3: stacked contact over item: Back closes one level at a time.
- [x] AC4: desktop contact shows the number and the message, Copy writes the number, and a refused clipboard selects it.
- [x] AC5: without a fine pointer, a text link opens no sheet and its default action is kept.
- [x] AC6: `#<id>` opens the item and clears the hash; an unknown id opens nothing.
- [x] AC7: deliberately breaking the handlers turns the suite red. Tested by mutation, with the result recorded in verification.md.

## References

- Bitácora board: #99. From the FEAT-003 review (#15).
- lesson-014 (headless Chrome has no pointer)
- FEAT-002 harness: `tests/test_share_button_browser.py`
