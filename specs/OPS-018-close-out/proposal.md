---
id: "OPS-018-close-out"
type: spec
status: draft # draft | implementing | verifying | archived
created: "2026-11-09"
issue: "mlorentedev/leaving-denver#267"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
owner: manu
---

# OPS-018-close-out

## Why

The sale is over on 2026-11-09 and the repository still describes a sale in progress: six items
are `Available` and nothing says that six of the sixteen left the apartment without money
changing hands (a giveaway is recorded as a sale with a realized price of `0`, deliberately, so
the status alone cannot tell them apart). The numbers that would answer "how did this go" are all
kept — the researched targets, the reserve floors, the realized price and day of every sale — but
one item at a time, encrypted, readable only by a human with an editor. And the page that outlives
the sale says "the sale is over, thank you": the repository's whole output is a sale, and the
artefact that survives it carries no result, no method and no way to reach the person who built
it. The deadline is ADR-008's: the Cloudflare token is revoked on 2026-11-15, and after that the
end page cannot be redeployed without a new token by hand. Whatever it says then, it says forever.

## What

**The end state is in the data.** Every item reaches its real end state in `data/inventory.yaml`,
and the file distinguishes a sale from a giveaway without decrypting anything: a new optional
item field, `disposition`, takes `sale` (the default, absent) or `giveaway`. `status` keeps its
meaning (`Available`, `Pending`, `Sold` — a lifecycle, FEAT-006) and gains nothing, so no page or
test that reads it changes. The six items that left without money are `Sold` + `disposition:
giveaway`; the car and the queen bed are `Sold` at their realized prices, recorded privately as
`make sold` already does.

**The aggregate is computed, not typed.** A new subcommand, `leaving-denver retro` (with
`make retro`), reads the inventory and the decrypted private data and prints one summary: per
group (household, vehicle, total) the expected value (the sum of the researched targets, and how
many items have one), the realized value, the ratio against the targets, against the asking prices
and against the reserve floors; the counts of sold, given away and unplaced; the days from the
catalog opening to the last item, and the median days per item. `--json` prints the same summary
as machine-readable JSON. It never prints the private document, which also holds the phone and the
tokens: only the numbers the summary names. Absolute money is seller-only (like the floors, and
for the same reason); nothing in the public tree holds a total.

**The end page carries the result and one way to reach the seller.** In end-of-sale mode the two
pages (EN, ES) keep the end message and add: the counts, derived from the inventory at build time
(16 items, 10 sold, 6 given away, none thrown away); the days and the recovered percentage, as
published claims typed in the locale files with the command and date that produced them in a
comment beside them; and one contact line — an email and the GitHub profile — that offers the same
construction for another move, or the method for someone who wants to run it themselves. It never
offers the address itself: a `pages.dev` name cannot be transferred, and ADR-008 kept it precisely
so that it does not fall into a third party's hands. No phone, no `sms:`/`tel:`, no item id, no
photo, `noindex` as today (ADR-010), both languages.

**A public retrospective.** `docs/case-study.md` states what happened in percentages and days,
with the honest split (the plan met in full; the household items 35% under the researched targets,
the car at its floor), and what that implies for the next sale. `README.md` gains a "Results"
section that points at it, above "Maintenance mode".

**An ADR amends ADR-008.** `docs/adr/adr-013-the-end-page-states-the-result.md` records that the
end page is no longer final-and-empty: it may change until the credentials are revoked, it carries
the result and a contact line, and it keeps every property ADR-008 protected (`noindex`, no phone,
the project never leaving the account). The "change it later means a new token" consequence
stands, and is the reason this ships before 2026-11-15.

**The repository is archived last**, after the credential removal, as
`docs/runbooks/decommission.md` already orders it. Nothing in this change archives it.

## Out of scope

- The decommission steps themselves (token and secret deletion, old deployments, uptime monitor,
  n8n digest). They are owner steps in `docs/runbooks/decommission.md` and follow the merge.
- Channel attribution: only two items ever recorded a posting (`tracking` holds nothing else), so
  "which channel sold what" is not computable and is not claimed anywhere.
- The Analytics Engine history (`visit`, `view_item`, `text_tap`): the dataset expires by itself,
  the query lives in kubelab, and no number on the page or in the case study depends on it.
- Any change to the catalog build, the seller tool, the flyer, the share pages, the prices, or the
  private data's schema beyond what `retro` reads.
- Any redesign of the end page beyond the three blocks above: no navigation, no item list, no
  images, no analytics beacon.

## Risks / open questions

- **The published percentages can drift from the data.** The counts are derived at build time, but
  the days and the percentages cannot be: the end build has no private data by design (OPS-011
  AC4), so they are typed in the locale files. Mitigation: they are typed once, beside a comment
  naming `make retro` and the day it produced them, and `verification.md` records that run; the
  case study repeats them with the same provenance. A test cannot close this gap, and pretending
  otherwise would be worse than naming it.
- **The last deploy is nearly irreversible.** After 2026-11-15 a change to this page costs a new
  API token. The rehearsal (a `candidate` deployment, `scripts/smoke.sh`) is therefore mandatory
  before the merge, not optional, and `decommission.md` already says so.
- **`disposition` is a public field with a private truth.** A typo turns a sale into a giveaway in
  the published counts. Mitigation: the field is validated against a closed set (an unknown value
  fails the build), a test asserts the four giveaways and the twelve sales, and `retro` reports
  both counts so the two sources are compared in one run.
- **The contact line invites mail to an address published on a page.** It is a DuckDuckGo alias
  already public in the catalog's seller data, not the personal address in the private file.
  Mitigation: nothing to do beyond using the alias, and the page stays `noindex` so it is not
  harvested into a directory.

## Acceptance criteria

- [ ] **AC1 — the file tells the truth.** Every item in `data/inventory.yaml` is `Sold`; the four
  giveaways (`dell-monitor-32`, `office-chair-ergonomic`, `dinnerware-glassware-set`,
  `lamps-pair`) carry `disposition: giveaway` and the twelve sales do not; an unknown
  `disposition` value fails the build. A test asserts the exact split (12 sales, 4 giveaways, 0
  unplaced) and that no item is left `Available`.
- [ ] **AC2 — the aggregate is a command.** `leaving-denver retro` prints the summary described
  above and `--json` prints it as JSON; with private data absent or unreadable it fails with a
  message that says so, and never prints a partial total that reads as a real one. Its output
  contains no phone, no token and no secret from the private document (asserted against sentinel
  values). Unit tests cover the arithmetic (targets present or absent, a giveaway at `0`, an
  unplaced item, an empty group) without touching sops.
- [ ] **AC3 — the end page.** In an end build, `/index.html` and `/es/index.html` each carry the
  counts, the published days and percentage, and one contact line, in their own language; the
  counts match the inventory the build read. The build still needs no phone and no private data,
  and no file under `build/public/` contains a phone, `sms:`, `tel:`, an item id or a realized
  total.
- [ ] **AC4 — the docs.** `docs/case-study.md` states the results with `make retro` cited as their
  source; `README.md` links it in a "Results" section; ADR-013 amends ADR-008 in writing, and
  ADR-008's status line points at it.
- [ ] **AC5 — the suite and the live page.** `make check` passes in both modes; the end-of-sale CI
  job passes with the switch on; the candidate deployment answers `/`, `/es/` with the new page
  and `/i/*` with a 302, and `scripts/smoke.sh` passes against it (the rehearsal of
  `decommission.md`).

## References

- Bitácora: mlorentedev/leaving-denver#267
- `docs/adr/adr-008-keep-the-pages-project-after-the-sale.md` (amended by ADR-013),
  `adr-002` (the phone is never served), `adr-004` (link-preview crawlers),
  `adr-010` (security headers and `noindex`)
- `specs/archive/OPS-011-end-of-sale/` (the switch this extends),
  `specs/archive/FEAT-006-honest-item-status/` (the lifecycle `disposition` must not disturb),
  `specs/archive/FEAT-015-sale-metrics/` (why no beacon is added to the end page)
- `docs/runbooks/decommission.md` (the ordering: page, then credentials, then archive)
- `docs/lessons/lesson-011-derive-figures-never-type-them.md` (the risk named above),
  `lesson-008-honest-urgency-over-invented-scarcity.md` (the tone of the page)
