---
id: "FEAT-003-accessible-catalog"
type: spec
status: implementing # draft | implementing | verifying | archived
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#15"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-003-accessible-catalog

> **Naming**: file lives at `<repo>/specs/FEAT-003-accessible-catalog/proposal.md`. `FEAT-003-accessible-catalog` is `AREA-NNN-slug` (e.g. `TOOL-001-secret-drift`).

## Why

<!-- from issue #15: FEAT-003: Accessible item dialog, desktop contact and readable text -->

Buyers read the catalog on phones in bright light and inside Facebook's in-app browser. Grey secondary text (neutral-400, 2.52:1) and 10–11 px labels fail WCAG AA, and the item and bundle sheets are plain `div`s: Escape does nothing, the page behind scrolls and stays focusable, and Back leaves the site instead of closing the sheet, which in an in-app browser drops the buyer out of the listing.

## What

1. **Readable text (PR 1):** no text utility under 4.5:1 on the light grounds and nothing under 12 px.
2. **Dialogs (PR 2):** item and bundle sheets become native `<dialog>`s opened modally: Escape and the backdrop close them, the background is inert and does not scroll, focus returns to the card, and Back closes an open sheet instead of navigating away.
3. **Desktop contact (PR 3, needs the owner):** where `sms:` cannot work (no coarse pointer), offer the number as `tel:` and copy-to-clipboard.

## Out of scope

- The search box listed in #15: the catalog has none since the mobile redesign (#71); chips already carry `aria-pressed`.
- Per-item links `/#<id>` (#14), statuses (#18).

## Risks / open questions

- The bundle offer must stay on one line (BUG-001 AC10). At 12 px the longest (ES) offer measures 268 px against 282 px available on a 360 px phone (Chrome canvas, Plus Jakarta Sans 700), so it still fits.
- History handling must not trap Back: one entry per open sheet, removed when the sheet closes by any path.
- PR 3: which contact channels the owner wants on desktop (tel, copy, email) is the owner's decision.

## Acceptance criteria

- [ ] AC1: every text colour meets 4.5:1 on its own ground (light: no neutral-300/400, emerald-500/600; dark: no neutral-500–700), and no text is under 12 px.
- [ ] AC2: item and bundle sheets are `<dialog>` elements opened with `showModal()`; Escape and backdrop close them; body scroll is locked while one is open.
- [ ] AC3: opening a sheet pushes one history entry; Back closes the sheet and stays on the page; closing by button or Escape removes the entry.
- [ ] AC4: on a fine pointer, the contact controls offer `tel:` and copy (owner-approved channels).

## References

- Bitácora board: issue #15
- Related spec: `specs/BUG-001-catalog-data-driven/` (AC10, one-line bundle offer)
