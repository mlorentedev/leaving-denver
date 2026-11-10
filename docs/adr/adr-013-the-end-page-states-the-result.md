---
id: "ADR-013-the-end-page-states-the-result"
type: adr
status: accepted
owner: manu
date: "2026-11-09"
issue: "mlorentedev/leaving-denver#267"
tags: [architecture, decision, content, operations]
created: "2026-11-09"
---

# ADR-013: The End Page States the Result

## Status

Accepted. It amends ADR-008 (the end page was kept, and meant to be final and empty) and relies
on ADR-002 (a phone number is never served), ADR-004 (link-preview crawlers stay allowed) and
ADR-010 (`noindex` and the security headers).

## Date

2026-11-09

## Context

ADR-008 kept the Pages project alive after the sale, for one reason: the links already in
circulation (the building flyer's QR code, shared cards in chats, marketplace listings) point at
`leaving-denver.pages.dev`, and a deleted project frees that name for anyone to claim. What it
decided to serve was a courtesy page — "the sale is over, thank you" — and it declared that page
final, since the deploy token dies with the credentials on 2026-11-15.

The sale is over now. Sixteen items left the apartment in 45 days, and the repository holds the
whole record of how: the researched targets, the reserve floors, the realized price and the day of
every sale. The page that outlives all of it carried none of that. The only artefact most visitors
will ever see — and the only one that survives the repository's own archive — said nothing about
what had happened, what it recovered, or who had built it.

One offer was considered and rejected: telling a visitor that "this space could be yours". It is
not possible — a `pages.dev` subdomain belongs to the Cloudflare account that owns the project and
cannot be transferred — and it is the precise risk ADR-008 was written against, since the whole
point of keeping the name was that no third party ever answers those old links. What can be
offered honestly is the same construction, or the method to repeat it.

## Decision

- **The end page states the result**, in both languages: the counts (derived from
  `data/inventory.yaml` at build time — never typed), the days and the recovered percentage, and
  one contact line (the public alias already in the inventory's `seller` block, and the GitHub
  profile).
- **Two of those figures are typed, once.** The days and the percentage come from prices that
  only exist encrypted, and the end build holds no private data by design (OPS-011 AC4), so they
  live in the locale files beside a comment naming `make retro` and the day it produced them.
  `lesson-011` says derive figures rather than type them; here the alternative is publishing
  private data, so the figure is typed and its source is written next to it.
- **The offer is the construction, not the address.** "Written for one move: if you are moving and
  want the same, or you want to run it yourself, write to me." The repository is the proof and the
  fork; the address is never offered.
- **Every property ADR-008 protected is kept**: no phone and no `sms:`/`tel:` link, no item, no
  photo, no metrics beacon, `noindex` as before, and the project stays in the account and in
  Terraform with `prevent_destroy`.
- **The page may change until 2026-11-15**, and then not again without a new API token set by
  hand. That consequence is ADR-008's, unchanged; this decision is shipped before the deadline
  because of it.

## Consequences

### Positive

- The one artefact that outlives the sale says something true and useful: how long it took, how
  much of the asking price came back, and how to reach the person who built it.
- The counts cannot drift, because the build reads them from the inventory; a test asserts the
  published counts against that file, and another asserts the two languages publish the same
  figures.
- The result is stated in percentages and days, so the page is honest about a sale whose absolute
  numbers are private (`data/private.sops.yaml`), and the case study can carry the same figures.

### Negative

- The end page now has a second audience — someone who may want this built for their own move —
  on a page whose primary job is to tell an old link's visitor that the sale is over. The page is
  ordered so the truth comes first and the offer last, but it is a compromise.
- Two typed figures can go stale if the encrypted record is corrected later. The mitigation is
  their provenance comment and the `make retro` run recorded in the spec's `verification.md`; no
  test can close it, and pretending otherwise would be worse than naming it.
- The contact line publishes an address that was previously only in the seller data. It is the
  DuckDuckGo alias, already public in that block, not the personal address in the private file.

### Neutral

- The published percentages (86 % of asking, 65 % of the researched targets, 81 % of the reserve
  floors) are the aggregate; the case study explains the split, and `make retro` produces both for
  whoever reads them next.
- `disposition` is a new public item field (`sale`, or `giveaway`). It exists because a giveaway is
  recorded as a sale with a realized price of `0` — correct for the lifecycle (FEAT-006), useless
  for a published count.
