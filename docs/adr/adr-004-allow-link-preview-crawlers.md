---
id: "ADR-004-allow-link-preview-crawlers"
type: adr
status: accepted
owner: manu
date: "2026-09-30"
issue: "mlorentedev/leaving-denver#14"
tags: [architecture, decision, web, privacy]
created: "2026-09-30"
---

# ADR-004: Allow Link-Preview Crawlers

## Status

Accepted. It amends ADR-001's "search crawlers blocked via `robots.txt`" consequence.

## Date

2026-09-30

## Context

ADR-001 shut every crawler out with `User-agent: * / Disallow: /`, plus `X-Robots-Tag: noindex`. That blocks the preview crawlers too, so every shared link showed a bare URL. Those crawlers are Facebook's, which also serves Messenger and Marketplace chats, X's and Telegram's. The site is shared almost entirely as links in those places, and a preview with a photo and a price is what gets a link tapped.

Preview crawlers are not search indexers. They fetch one page when someone posts its link, read its Open Graph tags and cache a card.

## Decision

- `robots.txt` names the preview crawlers and allows them: `facebookexternalhit`, `Facebot`, `Twitterbot`, `TelegramBot` and `WhatsApp`. `User-agent: *` stays `Disallow: /`.
- `X-Robots-Tag: noindex` and the `noindex` meta stay on every page, so nothing is added to a search index.
- Each published item gets a static share page (`/i/<id>/`, `/es/i/<id>/`) that carries only Open Graph tags built from the sanitized public inventory. A JavaScript redirect sends people on to `/#<id>`.
- Open Graph URLs are absolute on `SITE_URL` (config, default `https://leaving-denver.pages.dev`).

## Consequences

### Positive

- Shared links show the photo, the title and the price. Item links open that item.
- Search engines still stay out: every indexer is disallowed, and indexing is refused by header.

### Negative

- A scraper can claim to be `facebookexternalhit`. robots.txt was never enforcement, so nothing is lost here that was protected before. The phone keeps its JavaScript assembly (ADR-002), and the share pages carry no contact data.
- Previews are cached by the platforms (about 30 days on Facebook). A price or status change needs a manual re-scrape (runbook `ops.md`, "Link previews").

### Neutral

- WhatsApp and iMessage build previews on the sender's phone and mostly ignore robots.txt, so their behaviour does not change.

## References

- ADR-001 (static catalog, crawler policy), ADR-002 (contact obfuscation), ADR-003 (share pages foreseen)
- Spec: `specs/archive/FEAT-002-link-previews/`
