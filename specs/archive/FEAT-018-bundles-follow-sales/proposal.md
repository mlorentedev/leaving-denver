---
id: "FEAT-018-bundles-follow-sales"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-08: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-08)."
created: "2026-10-06"
issue: "mlorentedev/leaving-denver#207"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-018-bundles-follow-sales


## Why

<!-- from issue #207: FEAT-018: Bundles follow the sales: Take everything recomputes, a sofa + TV + coffee table bundle -->

Any sale takes **Take everything** off sale: it is a fixed list of 12 items at a fixed $540, and FEAT-006 marks a bundle unavailable as soon as one of its items is not Available. The first two real sales (#206) took it off sale, and took **Living room media** with it, because the C-shaped table was in that bundle. The page's largest offer now reads "No longer available" with eight weeks of sale left.

## What

- **Take everything is derived at build time.** It holds every published household item still Available (not Pending, not Sold, not the car), and its price is their sum at the bundle's `discount_pct` (20), rounded down to a multiple of $5. Today that is $625 → $500. The data keeps only the discount: an `everything` bundle that also carries `items` or `bundle_price` fails the build, because two sources for one price would be ambiguous.
- With fewer than two such items left there is nothing to bundle, so the card and its sheet are not rendered.
- **Living room media is replaced** by `bundle-sofa-tv-table`: the onn 43" TV, the sleeper sofa and the lift-top coffee table for $300 (separately $360, save $60). Owner decision, 2026-10-06. Sleeper sofa + topper stays as it is.
- Everything else reads the derived bundle as before: the card's "All N items … Save $X", the sheet's list, its text link and the upsell rule (which never offers the everything bundle).

## Out of scope

- Recomputing the other bundles. They are curated offers; one with a sold item stays off sale (FEAT-006).
- Rounding rules beyond "down to $5", and a per-window discount (the price drops are per item).
- The seller tool and `make post`: they list items, not bundles.

## Risks / open questions

- **The price moves on every sale and on every reprice.** That is intended: it is computed from the same prices the cards show, so it can never disagree with them.
- **Free items.** The air mattress is free with a purchase (price 0). It stays in the list, so it adds to the item count and not to the price.
- **Reserved items** are left out rather than making the bundle unavailable, so a pickup that falls through puts the item back in on the next build.

## Acceptance criteria

- [x] AC1: with nothing sold, Take everything lists every published, Available household item and costs floor(sum × 0.8 / 5) × 5; a Sold or Pending item is not in it and lowers the price by its share.
- [x] AC2: an `everything` bundle with `items` or `bundle_price` fails the build with the bundle id; one without `discount_pct` fails too.
- [x] AC3: with fewer than two items left, neither the card nor the sheet is rendered, and the page builds.
- [x] AC4: the real page shows Take everything on sale at $500 with 10 items, "Save $125".
- [x] AC5: `bundle-sofa-tv-table` (TV, sleeper sofa, coffee table, $300, with Spanish copy) is on the page, and `bundle-living-room` is gone.

<!-- archived 2026-10-07 — PR: https://github.com/mlorentedev/leaving-denver/pull/239 -->
