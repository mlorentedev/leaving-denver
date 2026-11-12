---
tags: [spec, verification, templates]
created: "2026-11-09"
id: "OPS-018-close-out"
type: spec-verification
status: active
owner: manu
---

# Verification - OPS-018-close-out

## Evidence

- **AC1 — the file tells the truth.** `data/inventory.yaml`: every item `Sold`; the six giveaways
  carry `disposition: giveaway` (`air-mattress-twin-pump`, `convertible-desk`, `dell-monitor-32`,
  `office-chair-ergonomic`, `dinnerware-glassware-set`, `lamps-pair`) and the ten sales do not.
  Tests: `tests/test_close_out.py` (the split, the exact giveaway set, no item left `Available`),
  `tests/test_retro.py::test_an_unknown_disposition_is_an_error`, and `check_dispositions` in
  `site_builder.build_all` runs in both build modes.
- **AC2 — the aggregate is a command.** `uv run leaving-denver retro` (or `make retro`) prints the
  table, the counts and the days; `--json` prints the same summary as JSON. The run recorded below
  is the one the published figures came from. Tests: `tests/test_retro.py` (arithmetic without
  sops, the giveaway at zero, an unplaced item, an empty group, the phone and token sentinels, the
  unreadable file printing no total at all).
- **AC3 — the end page.** `tests/test_end_of_sale.py` (counts against the inventory, the two
  languages publishing the same figures, the contact line, no phone, no item, no beacon) plus the
  live checks below.
- **AC4 — the docs.** `docs/case-study.md`, README "Results", `docs/adr/adr-013-…`, ADR-008's
  amendment note; `tests/test_close_out.py` checks the citation of `make retro`, the absence of an
  absolute amount in the public retrospective, and the ADR cross-reference.
- **AC5 — the suite and the live page.** `make check` with the switch on (below), and the
  candidate rehearsal (below).

## Test status

- `make check` → **1183 passed, 298 skipped** (the end-of-sale suite; the skipped ones are the
  catalog tests listed in `tests/conftest.py`'s `CATALOG_TESTS`, plus the browser suite).
  Lint (`ruff check` + `ruff format --check`) clean; `terraform fmt/validate` clean.
- Manual rehearsal, from this branch before merging:

  ```
  make deploy BRANCH=candidate
  scripts/smoke.sh https://candidate.leaving-denver.pages.dev
  → smoke OK (sale over)

  curl -s https://candidate.leaving-denver.pages.dev/    → <title>The sale is over · Moving Sale
                                                           16 items · 10 sold · 45 days · 86%
  curl -s https://candidate.leaving-denver.pages.dev/es/ → <title>La venta terminó · Venta por mudanza
                                                           16 artículos · 10 vendidos · 45 días · 86 %
  curl -sI .../i/sofa-sleeper/                            → HTTP/2 302
  grep -ciE '\b(sms|tel):' on / and /es/                  → 0 and 0
  ```

- The `make retro` run the figures came from (2026-11-09, seller-only output):

  ```
  GROUP      ITEMS      EXPECTED      REALIZED  /EXPECT   /ASK  /FLOOR  MED.DAYS
  household     15     $627 (13)          $490      65%    60%     81%        15
  vehicle        1        $0 (0)       $10,500      n/a    88%    100%        45
  total         16     $627 (13)       $10,990      65%    86%     99%        16

  Placed: 16 of 16 — 10 sold, 6 given away, 0 unplaced.
  Days: catalog opened 2026-09-25, last sale 2026-11-09, 45 days in total.
  ```

  Published on the page and in the case study: 16 items, 10 sold, 6 given away, 45 days, 86 % of
  the asking prices, median 15 days for household items. The absolute totals above stay in the
  encrypted file and appear nowhere in the public tree.
- No regressions: the only newly-skipped tests are the fourteen that read a live catalog with items
  still for sale, listed in `CATALOG_TESTS` with the reason, and four of those names are recorded
  in `SKIPPED_DESPITE_ITS_NAME` because they mention "private" without guarding it.

## Decisions made during implementation

- **The first aggregate was wrong, and the fix is in the report.** The first version divided a
  group's whole realized money by the targets of the few items that had one, printing 1753 % for
  the total. Now each item's realized money is compared with its own target and summed as
  `on_expected`; the report prints the denominator's population (`$627 (13)`) beside the figure.
  Written up as `docs/lessons/lesson-043-…`, since the blended total also hid the household miss.
- **The counts are derived, the days and the percentage are typed.** The end build holds no
  private data (OPS-011 AC4), so the two money-derived figures cannot be computed there. They are
  typed once in each locale file, beside a comment naming `make retro` and its date, and a test
  asserts the two languages publish the same numbers. Naming the gap was preferred to a build that
  reaches into the encrypted file.
- **`disposition` is a new optional field, not a new status.** A `Given` status would have touched
  every page and test that reads the lifecycle (FEAT-006); an optional field defaulting to `sale`
  keeps the lifecycle intact and still makes the public counts answerable.
- **The switch is flipped in this PR.** The catalog is not going to be built again, so the suite's
  live-catalog tests are skipped by the mechanism the repository already had for this day.
- **The CI job that forces the switch on is now idempotent.** With `seller.sale_over: true`
  committed, its `sed` would have written a duplicate key the parser accepts and a reader does not.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: `docs/lessons/lesson-043-a-percentage-of-a-mixed-total-hides-the-group-that-missed.md`
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? yes: `docs/adr/adr-013-the-end-page-states-the-result.md`
- [x] New pattern candidate for `00_meta/patterns/`? no: it is one project's close-out; the
  transferable part is the lesson above, which is repo-level.

## Adversarial review dispositions

Review: `review.md` in this folder — **PASS WITH GAPS**, no Blocker, no Major, four Minors
(`nan/glm5.3-flash`, 2026-11-10, reviewed `5bc70f9`). `proposal.md`, `tasks.md` and `features.json`
are the contract set the verdict closes: none of them changed after it, so the signature still holds.

| Finding | Disposition |
|---|---|
| F1 — `tasks.md` is stale: every Implementation and Closing box unticked although both PRs merged | **Accepted as-is.** The boxes are part of the reviewed contract set; ticking them would change a digest the verdict closes, and the work's real state is this file plus `gh pr view 268 269`. The cost is a reader who trusts ticks over evidence, which the review named. |
| F2 — the closing checklist requires `mypy`, which nothing runs or declares | **Ticketed:** [#273](https://github.com/mlorentedev/leaving-denver/issues/273) — add mypy to the lock, `make check` and CI, or drop the word from the template and the specs that carry it. |
| F3 — `retro` counts an `Available` item's price in `realized`, and `disagreements()` skips `status != "Sold"` | **Ticketed:** [#274](https://github.com/mlorentedev/leaving-denver/issues/274) — unreachable with the committed data (16 `Sold`, `disagreements: []`), so a follow-up rather than a blocker here. |
| F4 — the end page's sentence cannot account for an unplaced item | **Ticketed:** [#275](https://github.com/mlorentedev/leaving-denver/issues/275) — same reasoning as F3; the current split pins 10/6/0. |

The verdict travels with the folder; its **transcript does not**. That file replays the reviewer's
whole session, and in this repository the session runs the seller-only commands — the transcript of
this review carried `$10,500`, `$10,990`, the researched targets and the floors. The repository is
public, so `review.md` (percentages and days only, checked) and `review-request.json` (digests and
shas) are committed and `review-transcript.jsonl` stays on the machine that ran it; `.gitignore`
now refuses it. `review.md`'s digests still match: `dotf spec digest` normalises away the `status`
line, verified by setting `status: archived` and getting the same `proposal.md` digest
`42918bac…` that `review-request.json` recorded before the archive.

## Archive checklist

- [x] `proposal.md` frontmatter set to `status: archived`
- [x] Folder moved: `specs/OPS-018-close-out/` -> `specs/archive/OPS-018-close-out/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [x] Promotions above executed (if any)
