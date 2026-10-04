---
id: "FEAT-007-richer-item-fields"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#19"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-007: Richer item fields: condition, flaws, retail and size

## Why

<!-- from issue #19: FEAT-007: Richer item fields: condition, flaws, retail and size -->

A buyer scanning the catalog on a phone wants four answers before texting me: what shape is
it in, what is wrong with it, how good is the price, and will it fit in my car. Today the
condition is free text ("Great Condition", "Like New (Used Once)"), no item can state a flaw,
the discount is a struck-through number the buyer has to do the arithmetic on, size is buried
in a dimensions string, and every item carries two asking prices (`current_asking` and
`recommended_list_price`) of which only one is ever rendered. The second one sits in a
public repository as an ambiguous number nobody reads.

## What

After this change, from the data in `data/inventory.yaml`:

- **One price.** `recommended_list_price` stays the one asking price (it is already the only
  figure the builder renders and publishes as `price`). `current_asking` is deleted from every
  item and the build fails on an item that still carries it or has no price. Renaming the YAML
  key to `price` was judged out of scope: it touches the CLI, the private poster tool, the
  runbook and five test files for no change in what a buyer or the seller sees.
- **Condition on one scale.** Household items use Facebook Marketplace's four labels: New,
  Used - Like New, Used - Good, Used - Fair. The Spanish labels live once, in
  `locales/es.yaml` (`conditions:`), not per item; the build fails on a condition off the
  scale. The car keeps its own vehicle wording ("Excellent Exterior / Very Good Interior"):
  Facebook grades vehicles on a different scale, and rewriting my car copy is not this change.
  Mapping of the old strings: Good and Good Condition -> Used - Good; Like New and Like New
  (Used Once) -> Used - Like New; Great Condition -> Used - Good (rounded down: the scale has
  no "great", and no hype). "Used once" stays in the air mattress's specs.
- **Flaws.** An optional `flaws:` list per item (English) with an `es: flaws:` overlay of the
  same length. The item sheet shows a "Known flaws" / "Defectos conocidos" list when it is
  non-empty and nothing when it is empty; "no known flaws" is never printed because that would
  be a claim. No flaw is known today, so every item ships without one. The `/seller/` copy
  generator lists them too.
- **"% off" badge.** The builder derives `discount_pct = (retail - price) * 100 // retail`
  (rounded down) from `original_price` and the price, only when retail > price, the item is
  not free and not the car (a used car's price against its new sticker price is not a
  comparable). It shows on the card and in the sheet for items not yet Sold.
- **Size badges.** "Needs truck/SUV" when any side is over 48 in or the weight is over 50 lb;
  "2-person lift" when the weight is over 75 lb. The inputs are explicit numbers in the data
  (`size_in: [w, d, h]`, `weight_lb`), never parsed from the `dimensions` text (fractions,
  "Diagonal", ranges and "or straight 80+" make that unreliable). `size_in` is the size as the
  buyer carries it, copied from the owner's own `dimensions` string; it is omitted for soft or
  foldable things (mattress topper, air mattress: their pickup notes say a sedan takes them) and
  for items whose string is not W x D x H (monitor, dinnerware, car). No weight is in the data
  and none is invented, so "2-person lift" renders for nothing yet (follow-up for the owner).
- **Sorted by price, lowest first, Sold last.** Low to high is the order a shopper expects
  from a marketplace and puts the cheap pickups where the eye lands first. An item that is
  free with a purchase sorts by its list price, so it does not lead the grid as a giveaway.
  Equal prices keep the data order.

## Out of scope

- Renaming `recommended_list_price`, and any change to a price value.
- Moving the removed `current_asking` values to `data/private.sops.yaml`: that file is
  ciphertext and not touched here. The values remain in git history; the owner can add them
  as private targets with `sops set` if still wanted (see verification.md).
- Weights: none is sourced, so none is written.
- Sort controls (a price direction toggle) and a condition filter.
- Showing condition, flaws or size in the private poster tool (it keeps its own templates).

## Risks / open questions

- The retail figure (`original_price`) is the owner's, unverified; the badge makes it more
  prominent, so it is derived only from that figure and rounds down.
- The sofa and the convertible desk get "Needs truck/SUV" from their listed sizes; the sofa's
  pickup note already says a pickup, van or large SUV carries it, so the two agree.
- Real flaws, once the owner notes any, are data entries with a Spanish overlay: the build
  fails on a flaw with no overlay of the same length.

## Acceptance criteria

- [ ] AC1: Each item has exactly one asking price: no item carries `current_asking`, the build
  fails on one that does or that has no `recommended_list_price`, and the published `price` of
  every item equals the value on main.
- [ ] AC2: Household conditions are one of the four scale labels in the data and render as
  that label on `/` and its Spanish label on `/es/`; the build fails on a condition off the
  scale; the car keeps its vehicle wording.
- [ ] AC3: Flaws render on the item sheet in both languages from the data, as text; an item
  with none renders no flaws section; the build fails on flaws without a same-length Spanish
  overlay; the `/seller/` copy lists them.
- [ ] AC4: The "% off" badge is `floor((retail - price) / retail * 100)`, appears only when
  retail > price, never for a free item, a Sold item or the car, on the card and in the sheet.
- [ ] AC5: "Needs truck/SUV" appears when a side of `size_in` is over 48 in or `weight_lb` is
  over 50; "2-person lift" when `weight_lb` is over 75; the build fails on a `size_in` or
  `weight_lb` that is not positive numbers; every `size_in` number appears in the item's
  `dimensions` text; no weight is written without a source.
- [ ] AC6: The catalog grid lists items by ascending price with Sold items last, a free item
  by its list price, and ties in data order.
- [ ] AC7: Badge text and flaws meet the existing guards: class coverage, AA contrast, no
  horizontal overflow at 390 px, `UNBACKED_CLAIMS`, pickup facts and payment tests stay green.

## References

- Bitácora: #19. Thresholds from clearlist (48 in / 50 lb / 75 lb).
- `specs/archive/FEAT-008-verify-the-car/` (same data-driven pattern), `docs/runbooks/ops.md` (Price).

<!-- archived 2026-10-03 — PR: https://github.com/mlorentedev/leaving-denver/pull/183 -->
