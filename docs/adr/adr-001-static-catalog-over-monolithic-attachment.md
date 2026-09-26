---
id: "ADR-001-static-catalog-over-monolithic-attachment"
type: adr
status: accepted
owner: manu
date: "2026-09-25"
issue: ""
tags: [architecture, decision, web, hosting]
created: "2026-09-25"
---

# ADR-001: Static CDN Catalog Over Monolithic File Attachment

## Status

Accepted

## Date

2026-09-25

## Context

Liquidating DTC apartment furniture and vehicle requires sharing a catalog with hundreds of prospective buyers across Facebook Marketplace, Craigslist, and OfferUp. A competing prototype bundled the entire inventory and Base64-encoded images into a single 3.6 MB HTML file to be sent as a direct file attachment over WhatsApp or SMS. Testing revealed that mobile OS sandboxes (especially iOS) do not execute local HTML attachments natively, prompting users to save files or flagging untrusted scripts.

## Decision

Deploy a lightweight (<50 KB) static HTML/CSS/JS catalog hosted on Cloudflare Pages (`leaving-denver.pages.dev`) with lazy-loaded progressive Web JPEGs (<300 KB each). Share short URLs in chat responses rather than file attachments.

## Consequences

### Positive
- Sub-50ms TTFB across mobile devices via Cloudflare's edge network.
- Zero buyer friction: opens natively in mobile Safari/Chrome.
- Total asset privacy: search crawlers blocked via `robots.txt` and `X-Robots-Tag: noindex`.
- Decouples text metadata from image payloads, avoiding megabyte-scale payload transfers.

### Negative
- Requires internet access for buyers to view photos.
- Requires Cloudflare Pages deployment pipeline (automated via `./manage.py deploy-cf`).

### Neutral
- Eliminates reliance on heavy frontend frameworks (React, Next.js); vanilla DOM manipulation is sufficient.

## References
- `docs/lessons/lesson-001-mobile-html-monolith-attachment-failure.md`
- `src/site_builder.py`
