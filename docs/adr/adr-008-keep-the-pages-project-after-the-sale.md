---
id: "ADR-008-keep-the-pages-project-after-the-sale"
type: adr
status: accepted
owner: manu
date: "2026-10-01"
issue: "mlorentedev/leaving-denver#38"
tags: [architecture, decision, cloudflare, operations]
created: "2026-10-01"
---

# ADR-008: Keep the Pages Project After the Sale

## Status

Accepted. It extends ADR-004 (link-preview crawlers stay allowed) and relies on ADR-007 (the sealed
`SELLER_SEALED` secret is deleted with the others).

## Date

2026-10-01

## Context

The seller leaves Denver on 2026-11-09. After that nobody can watch the phone number the site
shows, and every old marketplace listing, shared link and the building flyer's QR code still
point at `https://leaving-denver.pages.dev`. Issue #38 asks for the site to be shut down.

Two ways to shut a Cloudflare Pages site down:

1. **Delete the project.** Every link answers with an error, and no deployment is left to serve a phone.
2. **Keep the project and replace what it serves** with one page that says the sale is over.

`pages.dev` subdomains are first come, first served. A deleted project's name is free for anyone
to claim by creating a project again, and whoever does owns every link already out there: the flyer, the shared
previews, the marketplace listings not yet taken down. That is a ready-made phishing address
that looks like the seller's.

## Decision

- **The project is kept**, serving the end-of-sale build (`seller.sale_over: true`, OPS-011):
  an end page in English and Spanish with no phone, no item, no photo, no share pages and no seller
  tool. `/i/*` and `/es/i/*` redirect with a 302 to the home page of their language.
- **The credentials are not kept.** By Nov 15 the deploy token is revoked and the `SELLER_PHONE`,
  `SELLER_SEALED` and `CLOUDFLARE_API_TOKEN` secrets are deleted in both environments. The
  deployed end page needs none of them to keep serving. The runbook is `docs/runbooks/decommission.md`.
- **Old deployments are deleted**, because each keeps its own URL and still serves the catalog.
  Only the current production deployment stays.
- **`robots.txt` and the preview allowances stay as they are** (ADR-004), so a re-shared link
  previews as "The sale is over".
- **The Access app for `/seller/` may be removed**, but need not be: `/seller/` is no longer built.

## Consequences

### Positive

- Nobody can take over the subdomain and the links people already hold keep working, and say
  something true.
- Messages stop arriving at a number the seller can no longer watch, and nothing live is left
  behind the page: no secret, no token, no number.
- The project is free at Cloudflare's current limits, so keeping it costs nothing.

### Negative

- The CI deploy job needs `SELLER_PHONE` and the token, so after the secrets are deleted the
  site cannot be redeployed. Changing the end page later means creating a new token, setting it
  as a secret and sending a deploy by hand. The end page is meant to be final.
- Flipping the switch turns the suite's catalog tests off (`tests/conftest.py` skips them by
  name), since there is no catalog build for them to read. A new catalog test must be added to
  that list on the day it first runs against an end build.
- The project is a small liability to remember: if the Cloudflare account is ever closed, the
  name becomes claimable then.

### Neutral

- Preview crawlers cache the old cards for about 30 days; the runbook has the optional
  re-scrape that shows the end message sooner.
