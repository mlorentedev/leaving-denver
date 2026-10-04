---
id: "OPS-011-end-of-sale"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-10-01"
issue: "mlorentedev/leaving-denver#38"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# OPS-011-end-of-sale

## Why

The seller leaves Denver on 2026-11-09 (`seller.departure_date`; OPS-013 replaced it with `household_deadline` and `vehicle_deadline`, and the sale is now turned off with the car, no later than Nov 9, not on Nov 8). The site will outlive the sale unless something turns it off. Its phone number and its old marketplace links will keep drawing spam and scam messages to a number the seller can no longer watch. Shared links and the building flyer's QR code point at `leaving-denver.pages.dev`. Deleting the Pages project frees that subdomain for anyone to claim, and they would then own every link already out there. So the safe end state is: the same project, serving one page that says the sale is over, with no phone and no live credential behind it. Issue #38.

## What

One data switch, `seller.sale_over: true` in `data/inventory.yaml`, turns the build into an end-of-sale build:

- `/` and `/es/` render a short end page in EN and ES: the sale is over, thank you. It has no phone, no `sms:`/`tel:` link, no item, no price and no photo. The language links stay.
- No `/i/<id>/` share pages and no `/seller/` directory are emitted. `_redirects` sends `/i/*` and `/es/i/*` to the matching home page with a 302, so old shared links land on the end page instead of a 404.
- The build needs no `SELLER_PHONE` and no private data in this mode. If they are present, it embeds nothing from them.
- `robots.txt` and the link-preview allowances stay as they are (ADR-004), so a re-shared link previews as "sale over".
- `scripts/smoke.sh` knows the mode. In it, smoke checks the end page and that the phone is absent; it does not look for the catalog markers.
- `docs/runbooks/decommission.md` turns the #38 checklist into commands and dashboard steps, for Nov 8 and by Nov 15. ADR-008 records why the Pages project is kept and not deleted.

With the switch absent or `false`, the build is unchanged.

## Out of scope

- Flipping the switch. That is the owner's Nov 8 step, in the runbook.
- Deleting secrets, revoking the Cloudflare token, releasing Google Voice and archiving the repo. These are owner steps, listed in the runbook with commands.
- Removing the Cloudflare Access app for `/seller/`. It is harmless once `/seller/` is gone; the runbook marks its removal optional.

## Risks / open questions

- **CI deploy still injects `SELLER_PHONE`.** The end build must ignore it. AC1 asserts a sentinel phone in the environment reaches no built file.
- **`_redirects` and Pages Functions.** The middleware runs for `/seller/*` only. Check that `_redirects` rules for `/i/*` apply on Pages with Functions present: a smoke check against a preview deploy covers it.
- **Stale cache of old share pages.** Pages serves the new deploy atomically, so this is not a concern beyond the crawlers' own caches.

## Acceptance criteria

- [ ] **AC1: no phone, no item.** In an end build with `SELLER_PHONE` set to a sentinel, no file under `build/public/` contains the sentinel, any of its formatted forms, `sms:`, `tel:`, any item id from the inventory, or `data-item=`.
- [ ] **AC2: the end page.** `/index.html` and `/es/index.html` each contain the end message in their language, and `<title>` and `og:title` say the sale is over. The EN and ES pages link to each other.
- [ ] **AC3: nothing else is served.** No `i/` or `es/i/` directory and no `seller/` directory exist in the end build. `_redirects` contains a 302 from `/i/*` to `/` and from `/es/i/*` to `/es/`.
- [ ] **AC4: builds with no secrets.** The end build succeeds with no `SELLER_PHONE` and no decryptable private data.
- [ ] **AC5: the default build is the catalog.** With the switch absent, the full existing suite passes, and a test asserts the flag defaults to off. The default build gains three `sale_over_*` UI strings in the locale files (carried in the page's inline `ui_json`) and two CSS utilities from the end page's template; it is otherwise unchanged.
- [ ] **AC6: smoke follows the mode.** `scripts/smoke.sh` passes against a served end build and fails against it when the end page carries a `tel:`/`sms:` link. It still passes against the normal build.
- [ ] **AC7: runbook and ADR.** `docs/runbooks/decommission.md` has a Nov 8 section and a by-Nov-15 section, and every step is a command or a named dashboard path. ADR-008 records keep-the-project-over-delete with the subdomain-reuse reason.

## References

- Issue #38
- ADR-002 (phone obfuscation), ADR-004 (link-preview crawlers), ADR-007 (sealed private data: the `SELLER_SEALED` secret is deleted in the runbook)
- `docs/runbooks/ops.md` (links to the new runbook)

<!-- archived 2026-10-03 — PR: https://github.com/mlorentedev/leaving-denver/pull/183 -->
