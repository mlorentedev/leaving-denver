---
id: "FEAT-008-verify-the-car"
type: spec
status: implementing # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#37"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-008: Vehicle "verify it yourself" section

## Why

<!-- from issue #37: FEAT-008: Vehicle "verify it yourself" section -->

A stranger will not pay five figures for a car on a seller's word, and the usual
shortcut ("buy the report on my link") is also the usual scam. The listing already
holds real evidence (the recall-closure invoice and the May 2026 emissions report are
in the car's photos) but nothing tells a buyer where to check the VIN themselves.
The car needs one compact section that shows the public VIN, sends the buyer to the
official lookups, points at the evidence I already have, and says plainly where to
run checks and where never to pay.

## What

On the catalog page (`/` and `/es/`), under the car's card, a "Verify it yourself" /
"Compruébalo tú mismo" section shows:

- the public VIN, selectable for pasting;
- links to official sources only: NHTSA recalls, Ford recalls, NICB VINCheck;
- my own evidence, each linking to a photo of the car's own `photos:` list: the
  recall-closure invoice and the May 2026 emissions report (overall PASS), with the
  note that the May test passed but that certificate is already used for my registration
  renewal, so I take a new emissions test before handover and give the buyer that new
  certificate;
- (dropped 2026-10-01, owner: the "official sites only, never pay through a link" line
  was superfluous.)

The links and evidence are data under the car in `data/inventory.yaml` (`verify:`),
with Spanish labels in the car's `es:` overlay, so adding a check or an evidence item
later is one list entry. The builder fails the build on a check that is not https on
an official host, and on evidence that is not one of the car's photos.

NHTSA decision: NHTSA's own pages were not reachable from the build host to confirm a
documented VIN deep-link format, so the section links `https://www.nhtsa.gov/recalls`
and shows the VIN to paste. A VIN query parameter is never guessed.

## Out of scope

- A Carfax report and a Ford dealer service-history printout: both are pending owner
  tasks (#28, #34). The data shape takes them as one entry each later; nothing renders
  until they exist.
- A 100k service receipt: none exists, so it is never claimed (`UNBACKED_CLAIMS`).
- Title, registration, plate, owner name or address: never published; the VIN already is.
- Third-party VIN resellers or any host that is not official or first-party.
- A copy button or other JavaScript for the VIN.

## Risks / open questions

- An official site can change its URL; the links point at stable landing pages, not
  deep links, to keep that risk low.
- Adding Carfax later needs its host added to the builder's allow-list on purpose: the
  allow-list is the control that keeps resellers out.

## Acceptance criteria

- [ ] AC1: `/` and `/es/` each put a "Verify it yourself" button on the car's card (its
  action row) that opens a sheet, like the item and bundle sheets (one history entry;
  closed by its button, Escape, the backdrop and Back). The sheet shows the VIN and links
  to the three official hosts (nhtsa.gov, ford.com, nicb.org), in the page's language.
  The content is no longer a section on the page (owner, 2026-10-01).
- [ ] AC2: Every external link in the section is https on an allow-listed official
  host and opens in a new tab with `rel="noopener noreferrer"`; the build fails on a
  check outside the allow-list.
- [ ] AC3: The section shows the recall-closure invoice and the emissions report as
  links to photos that exist in the car's `photos:` and in the build; the build fails
  on evidence that names a photo the car does not have.
- [ ] AC4: The section says the May 2026 test passed, that certificate is already used for
  the owner's registration renewal, and a new emissions test is taken before handover with
  the new certificate given to the buyer. (The anti-scam line was dropped on 2026-10-01: the owner found it superfluous.)
- [ ] AC5: The section makes no 100k-service, Carfax or service-history claim and
  names no title, registration, plate, owner or address.
- [ ] AC6: The links and evidence are data with English and Spanish labels; the
  template hardcodes none of them, and a car with no `verify:` renders no section.

## References

- Bitácora: #37; pending owner tasks #28 (Carfax), #34 (dealer service history).
- `docs/runbooks/vehicle-sale.md` (§2 "Your report, their link", §6 emissions)
- `docs/lessons/lesson-010-redact-scanned-documents-on-pixels.md`
