---
id: "FEAT-006-honest-item-status"
type: spec
status: implementing # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#18"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-006-honest-item-status

> **Naming**: file lives at `<repo>/specs/FEAT-006-honest-item-status/proposal.md`. `FEAT-006-honest-item-status` is `AREA-NNN-slug` (e.g. `TOOL-001-secret-drift`).

## Why

<!-- from issue #18: FEAT-006: Show reserved, free and sold items honestly -->

Items will start selling in October, and the catalog cannot show it. A `Sold` item renders exactly like an available one: same card, same price, same "Text about this" link. Every bundle that contains it stays on sale at its old price. Buyers would text about things that are gone, and the seller would answer the same "sorry, sold" message all month. Real sold counts are also the only honest urgency the page can show (lesson-008).

## What

Three statuses in `data/inventory.yaml`: `Available`, `Pending` (reserved, awaiting pickup) and `Sold`. "Free" is not a status; it stays the existing `free_with_purchase` price attribute.

1. **Builder (PR 1):**
   - An unknown status fails the build.
   - Public items carry the status key plus a localized label.
   - Sold items are ordered last at build time. The grid order is static, and the filter only hides cards.
   - A bundle is `available` only while every item in it is `Available`.
   - A `leaving-denver pending <id>` command sits beside `sold`, and `available <id>` undoes a reservation that fell through.
2. **Page (PR 1):**
   - Pending cards carry a "Pending pickup" badge. Sold cards are dimmed, with the price struck through and a "Sold" badge.
   - The item sheet shows the status. A sold item has no "Text about this" link. A pending one keeps it, because a backup buyer is worth having when a pickup falls through.
   - An unavailable bundle is dimmed and says so, loses its text link, and is never offered as the item sheet's upsell.
   - The vehicle hero gets the same treatment.
   - Once anything is reserved or sold, a line under the category chips reads "N of M available", with "· X sold" added once something has sold.
3. **Hide-sold toggle (PR 2):** only worth it once sold cards push available ones down; ships when the first real sales land.

## Out of scope

- "Was $X, now $Y" after a price drop. It needs a public previous-price field, and #19 first collapses `current_asking` / `recommended_list_price` into one public `price`. It will be sequenced after #19 and tracked there.
- Removing sold items: they stay visible, because the sold count is the point.

## Risks / open questions

- The template lines overlap the FEAT-003 stack (#94–#96). The page half is written after that stack lands, to avoid a three-way rebase.
- `realized_price` (what an item actually sold for) is private. The public item is built from a whitelist, so it cannot leak today, and a test pins that.
- Marketplace cross-posts are not updated by this. The existing `sold` checklist output stays the reminder.

## Acceptance criteria

- [ ] AC1: a status outside Available / Pending / Sold fails the build with the item id.
- [ ] AC2: sold items render after every unsold item; the relative order of the rest is unchanged.
- [ ] AC3: a bundle containing a Pending or Sold item is marked unavailable, shows no text link and is not offered as an upsell.
- [ ] AC4: sold cards are dimmed with the price struck through and a Sold badge; pending cards carry a Pending pickup badge; a sold item's sheet has no text link.
- [ ] AC5: once anything is reserved or sold, a line under the chips reads "N of M available", plus "· X sold" when X > 0; the figures are computed from the data.
- [ ] AC6: `leaving-denver pending|available <id>` set the status and rebuild; `realized_price` never appears in `build/public`.

## References

- Bitácora board: issue #18
- Related: lesson-008 (honest urgency), lesson-011 (derive figures), lesson-012 (template contexts are public data contracts), #19 (price field collapse)
