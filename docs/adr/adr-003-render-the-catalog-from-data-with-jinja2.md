---
id: "ADR-003-render-the-catalog-from-data-with-jinja2"
type: adr
status: accepted
owner: manu
date: "2026-09-26"
issue: "mlorentedev/leaving-denver#6"
tags: [architecture, decision, web, build]
created: "2026-09-26"
---

# ADR-003: Render the Catalog From Data With Jinja2

## Status

Accepted

## Date

2026-09-26

## Context

`templates/index.html` is a static page. The builder regex-replaces its `const INVENTORY = {...}` placeholder with the sanitized YAML, and client JavaScript draws the item grid from that JSON. Everything outside the array is written by hand: the hero, the vehicle card, the filter chips, the whole-apartment banner, `UPSELL_MAP` and the pickup terms. That hand-written copy is where the catalog's defects live:

- the bundle cards read fields the data does not have (#6);
- the counts, totals and "3 weeks" drift from the data (#6, #48);
- the vehicle card makes claims the YAML does not back (#9, #48).

Two planned features need HTML produced from data at build time:

- per-item share pages with Open Graph tags (#14), which a client-side script cannot produce for link crawlers;
- a build that fails when the page and the data disagree (#6, #48, DX-001 #21).

Also, if the regex injection does not match, the build ships the stale placeholder without an error.

## Decision

The builder renders the public page, and later the per-item pages, from `data/inventory.yaml` with Jinja2:

- It uses `StrictUndefined`, so a field renamed in the data but not in a template fails the build instead of rendering empty.
- Client JavaScript keeps only behaviour: filtering, the item and bundle sheets, and SMS links. It reads the same sanitized JSON, which is emitted through a fail-closed marker rather than a regex.
- `jinja2` becomes a runtime dependency. It is the only one added.

## Consequences

### Positive
- The data and the page cannot drift silently: a missing field is a build error, and tests can read the rendered HTML.
- The item cards are in the HTML itself, so the page works before, or without, JavaScript.
- Per-item pages for #14 become one more template loop.

### Negative
- One more dependency to keep locked and updated.
- The move to templates touches most of `index.html`, so it lands in several PRs, not one (see `specs/archive/BUG-001-catalog-data-driven/`).

### Neutral
- The hosting and privacy model of ADR-001 and ADR-002 is unchanged: a static site on Cloudflare Pages, the phone still fragmented in `_C`, and nothing private in `build/public/`.
- Styling is untouched here. Replacing the Tailwind play CDN (#8) is a separate change.

## Alternatives considered

- **Keep client-side rendering and move all copy into the injected JSON.** No new dependency, but the per-item OG pages would need a second generator (Python format strings), and every copy test would have to run JavaScript or re-derive what the script shows.
- **A static-site generator (Eleventy, Hugo).** It brings a second toolchain and language for a single page and a handful of stubs.

## References
- `docs/adr/adr-001-static-catalog-over-monolithic-attachment.md`
- `docs/adr/adr-002-client-dom-phone-obfuscation-and-security-isolation.md`
- `specs/archive/BUG-001-catalog-data-driven/proposal.md`
