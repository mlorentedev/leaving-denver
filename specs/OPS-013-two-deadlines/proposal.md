---
id: "OPS-013-two-deadlines"
type: spec
status: verifying # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-10-02"
issue: "mlorentedev/leaving-denver#156"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# OPS-013-two-deadlines

## Why

The data held one date, `seller.departure_date: 2026-11-09`, and everything derived from it: the
price-drop windows (offsets of -37 to -4 days), the hero and its countdown, the meta description,
the flyer's "Everything must go by November 9" and the seller tool's drop suggestions. On
2026-10-02 the owner decided two deadlines: household items (everything except the car) must go by
**2026-10-23**, the car by **2026-11-09** (the owner flies on 2026-11-18, which the site does not
need). Offsets from 2026-10-23 would put two of the four drops in the past, so the owner also fixed
the household schedule by hand. Issue #156.

## What

- **Data shape.** `seller.departure_date` is replaced by `household_deadline`, `vehicle_deadline`
  and `price_schedule`, in `data/inventory.yaml`:

  ```yaml
  household_deadline: '2026-10-23'
  vehicle_deadline: '2026-11-09'
  price_schedule:          # the day each window opens
    first_drop: '2026-10-06'
    second_drop: '2026-10-12'
    clear_floors: '2026-10-16'
    giveaway: '2026-10-20'
  ```

  The owner's windows are first drop from Oct 6, second drop from Oct 12, floors Oct 16-19 and
  giveaway Oct 20-22. They are contiguous, so each window is listed by its opening day and runs to
  the day before the next one opens, the giveaway to the day before `household_deadline`. That
  gives the owner's dates exactly and leaves one date to edit per window. The car has no schedule.
  There is no `data/inventory.json`: the YAML is the only file.
- **Fail closed.** `sale_dates()` (next to `sale_over()`, same style) rejects a missing key, an
  unknown window, a date that is not a quoted ISO string (YAML turns a bare `2026-10-23` into a date
  object), a household deadline not before the car's, and windows that do not open in order before
  the household deadline. The end build (OPS-011) does not read the dates.
- **Countdown.** It targets the household deadline while any published household item is for sale
  (status not `Sold`, so `Pending` counts), otherwise the car's. The rule reads the sanitized items,
  so hiding the unsold household items on Oct 23 (`published: false`) is what moves it.
- **Page copy, EN and ES.** The countdown line says "Furniture & tech until October 23" (then
  "Car available until November 9" once no household item is left); the car card says "Available
  until November 9" while the car is Available. The hero and the title name what is still for sale
  (both, household only, car only). They no longer say "I am relocating in <month>": that month was
  the single deadline, and the owner leaves in November. The meta description is the hero line plus
  the countdown line, so its month follows the same rule. ES dates are "23 de octubre", from a
  per-locale `date_format`.
- **Flyer.** "Furniture & tech by October 23 · car until November 9", each part only while
  something under it is for sale. No "Everything must go" claim.
- **Seller tool.** `seller_drops()` and `leaving-denver drops` read `price_schedule`, and the car
  gets no next-drop suggestion in `/seller/` (it has no schedule). Listing copy keeps its month and
  takes it from `vehicle_deadline` (November), which is when the owner moves.
- **Household close-out (Oct 23).** Unsold household items leave the catalog with
  `published: false`, not `Sold` and not by deleting entries: deleting breaks every bundle that
  names them, while `published: false` already hides the item, every bundle containing it, its photos
  and its share page (a 404 since #154). `docs/runbooks/decommission.md` has the step, with a
  comment-preserving snippet that a test runs against a copy of the real data. The existing
  end-of-sale flow follows once the car is handed over, no later than Nov 9.
- **Runbooks.** Seller playbook, backup exits, vehicle sale, decommission and ops use the two dates.

## Out of scope

- Archived specs, lessons and ADRs keep the single date they were written with.
- A time-based switch of the countdown: the page is static, and the owner's close-out is the
  event that moves it.
- Any change to the price tiers or to the private views' arithmetic.

## Risks / open questions

- The hero line changed shape (lesson-027). The owner may want a different sentence; the copy is
  in `locales/en.yaml` and `locales/es.yaml`.
- `leaving-denver drops` still prints the car's price tiers (prices only, no dates); only the
  seller tool's dated next-drop suggestion is household-only.
- The WIP limit of `dotf spec init` (14 active specs, the limit is 10) was not run; the spec
  folder was written by hand in the shape of BUG-013.

## Acceptance criteria

- [ ] **AC1: data.** `seller` holds `household_deadline`, `vehicle_deadline` and `price_schedule`, and no `departure_date`; the schedule yields the owner's windows.
- [ ] **AC2: fail closed.** A missing or ill-ordered schedule, a non-ISO or unquoted date, or a car deadline not after the household's fails the build with a message naming `seller.<key>`.
- [ ] **AC3: countdown.** It targets Oct 23 while a household item is for sale (Pending counts) and Nov 9 otherwise, in both languages; the meta description month follows.
- [ ] **AC4: copy.** The car card says it is available until Nov 9 only while Available; the hero and the title name what is for sale; EN and ES.
- [ ] **AC5: flyer.** "Furniture & tech by October 23 · car until November 9", with the car part only while the car is for sale and no "Everything must go".
- [ ] **AC6: seller tool.** `seller_drops()`, the built `/seller/` config and `leaving-denver drops` follow the explicit schedule, and the car has no next drop.
- [ ] **AC7: close-out.** The runbook's snippet hides every unsold household item and nothing else, and a build of the result targets the car's date and drops the share pages.
- [ ] **AC8: runbooks and gates.** The runbooks use the two dates; `make check` is green with the sale on and with `sale_over: true`.

## References

- Issue #156; OPS-011 (end of sale, `sale_over`), BUG-013 / #154 (the 404 for a removed share page), lesson-008 (no invented urgency), lesson-027
