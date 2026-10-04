---
id: "FEAT-002-link-previews"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#14"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-002-link-previews

> **Naming**: file lives at `<repo>/specs/FEAT-002-link-previews/proposal.md`. `FEAT-002-link-previews` is `AREA-NNN-slug` (e.g. `TOOL-001-secret-drift`).

## Why

<!-- from issue #14: FEAT-002: Link previews and shareable per-item links -->

The seller shares the catalog in Facebook Marketplace, WhatsApp and text threads. Today every link previews as a bare URL: `robots.txt` shuts out the preview crawlers too, and the page has no Open Graph tags. A buyer asking about one item gets a link to the whole catalog, not to the item. A preview with a photo and a price is what gets a link tapped. A link that opens the item is what saves a round of messages.

## What

PR 1 (previews and links):

1. **Preview crawlers.** `robots.txt` names the link-preview fetchers (`facebookexternalhit`, `Facebot`, `Twitterbot`, `TelegramBot`, `WhatsApp`) and allows them. `User-agent: *` stays `Disallow: /`. The `X-Robots-Tag: noindex` header and the `noindex` meta stay, so the site is still kept out of search indexes. Preview fetchers do not index, and indexers are still refused. WhatsApp and iMessage fetch from the sender's phone and mostly ignore robots.txt, so they need no rule. ADR-004 records the change to ADR-001.
2. **Per-item share pages.** Every published item gets `i/<id>/index.html`, and `es/i/<id>/index.html` for the Spanish page. Each one carries:
   - `og:title` (the item title);
   - `og:description` (price or free note, status and the pickup area). A sold item still has a page, and its description says Sold;
   - `og:url` (the share page's own absolute URL, because Facebook re-reads `og:url` as the canonical page);
   - `og:image` plus its width, height and alt;
   - `og:locale` and its alternate;
   - `twitter:card=summary_large_image`.
   A script sends people on to `../../#<id>` with `location.replace`, and a plain link in the body covers browsers without JavaScript. The redirect is JavaScript only, never `meta refresh` or an HTTP redirect: a crawler following either would land on `/`, where the hash is lost, and would read the catalog's tags instead of the item's. The pages are built from the sanitized public inventory only. So an unpublished item never gets one, and no page carries the contact fragments.
3. **Preview image.** `catalog/<id>/og/<cover>.jpg` is 1200×630, in its own folder, so no photo name can collide with it. The cover is letterboxed onto the page background (`#fbfbfb`), not centre-cropped, because the cards use `object-contain` and a crop would cut the furniture. The image is encoded from the processed cover JPEG and written only when its bytes change, so a rebuild with nothing new touches nothing (lesson-016). Pillow's JPEG encoder is deterministic for one version, and the photo manifest already pins that version. Any other file in `og/`, such as the preview of an earlier cover, is pruned. An item with no photo gets no `og:image`.
4. **Catalog preview.** `index.html` and `es/index.html` get the same tags for the catalog: the page title, a one-line summary from the locale, and the vehicle's preview image (or the first item's when there is no vehicle).
5. **Deep link.** Opening `/#<id>` (or `/es/#<id>`) opens that item's sheet after the page loads. The hash is dropped from the address first, so a reload after closing shows the catalog. It opens through the same `openSheet`, so Back closes the sheet and stays on the catalog. An unknown id does nothing. Item ids must be lower-case slugs (the build fails otherwise), since they become paths and fragments.
6. **Canonical origin.** `SITE_URL` in `config.py` defaults to `https://leaving-denver.pages.dev` and can be overridden from the environment. The build fails on a value that is not an `https://` origin without a path. Preview deployments therefore emit production `og:image` URLs. That is acceptable, because only production links get shared.
7. **Smoke.** `scripts/smoke.sh` also checks that `robots.txt` names `facebookexternalhit`. It checks that the catalog's `og:image` answers as a JPEG on the deployment. It checks that the first item's EN and ES share pages exist (matched by their own `og:url`, since Pages answers unknown paths with `index.html`) and that their `og:image` answers as a JPEG.

PR 2 (share button):

8. **Share button** in the item sheet. It uses `navigator.share({title, url})` where available. Otherwise it copies the URL to the clipboard and says "Link copied". Without a clipboard, it selects the URL in place. The URL shared is the absolute share page (`SITE_URL/i/<id>/`, or `/es/i/<id>/`), not `/#<id>`: a `/#<id>` link would preview as the catalog.

## Out of scope

- Share pages for bundles; `/#<bundle-id>` deep links.
- Updating the hash as sheets open and close. The shared URL comes from the button, not the address bar.
- A custom domain. `SITE_URL` is the only place to change when one arrives.
- Purging preview caches automatically. The runbook covers the manual refresh.

## Risks / open questions

- **Scrapers pretending to be `facebookexternalhit`.** robots.txt is advisory, so a scraper can already ignore it. Allowing a named user agent gives nothing to one that lies. The phone keeps its JavaScript assembly (ADR-002), and the share pages carry no contact data.
- **Preview caches.** Facebook caches a preview for about 30 days. After a price or status change, a re-scrape from the Sharing Debugger refreshes it (runbook).
- **Owner review.** The owner asked for the design before code. The choices above are defaults that can be overruled in review: the extra crawlers, letterboxing, the catalog image and the JavaScript-only redirect.

## Acceptance criteria

- [ ] AC1: `robots.txt` allows each named preview crawler and still disallows `User-agent: *`. The `noindex` header and meta are unchanged.
- [ ] AC2: every published item has an EN and an ES share page with absolute `og:url` and `og:image`, a description with its price and status, and no `meta refresh`. Its script redirects to `../../#<id>`.
- [ ] AC3: an unpublished item has no share page and no preview image. No share page carries the contact fragments.
- [ ] AC4: the preview image is 1200×630, letterboxed on `#fbfbfb`, and is not rewritten when nothing changed. A replaced cover prunes the old one.
- [ ] AC5: both catalog pages carry catalog-level Open Graph tags with an existing absolute image.
- [ ] AC6: `/#<id>` opens that item's sheet, and an unknown id opens nothing (checked in a browser, recorded in verification.md).
- [ ] AC7: a `SITE_URL` that is not a bare `https://` origin fails the build, and so does an item id that is not a lower-case slug.
- [ ] AC8 (PR 2): the item sheet has a Share button that shares or copies the item's share page URL.

## References

- Bitácora board: #14
- ADR-001 (crawlers blocked), amended by `docs/adr/adr-004-allow-link-preview-crawlers.md`
- ADR-002 (contact obfuscation), ADR-003 (per-item share pages foreseen)
- lesson-016 (freshness keyed on content)

<!-- archived 2026-10-03 — PR: https://github.com/mlorentedev/leaving-denver/pull/183 -->
