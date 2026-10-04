---
id: "BUG-013-not-found-page"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-10-01"
issue: "mlorentedev/leaving-denver#152"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# BUG-013-not-found-page

## Why

The build emits no `404.html`, so Cloudflare Pages runs the site in single-page-app mode: any
path it has no file for answers `200 text/html` with the catalog
(`curl -sI https://leaving-denver.pages.dev/definitely-not-here.txt`). A stale or mistyped link
shows the catalog as if it were valid, a link-preview crawler is told a broken link is fine, and
a fresh deployment can serve the catalog for a file it has not published yet (lesson-025, which
made the smoke retry `robots.txt` for that reason). Issue #152.

The Pages rule, from "Serving Pages" (https://developers.cloudflare.com/pages/configuration/serving-pages/):
"If your project does not include a top-level `404.html` file, Pages assumes that you are
deploying a single-page application", and with one, Pages answers a missing path with a 404 and
the closest `404.html`, looking up the directory tree and ending at `/404.html`.

## What

The build writes a top-level `404.html`, in the catalog build and in the end-of-sale build
(OPS-011) alike:

- **One page, both languages.** Pages serves one file for every missing path and cannot know the
  reader's language (`/es/nope` has no `es/404.html` unless one is built, and a bare `/nope` has
  no language at all). So an English and a Spanish block sit on the same page, each with a link
  to its home page (`/` and `/es/`). Per-language 404 pages would double the surface for the one
  page that has no content.
- **Root-absolute assets.** Pages serves the file at the URL that was asked for, so `/i/x/y`
  resolves a relative `styles.css` to `/i/x/styles.css`. The catalog and end pages use relative
  paths (`styles.css`, `../styles.css`) because each sits at a fixed depth; this one cannot, so it
  links `/styles.css`, `/favicon.svg` and `/fonts/...`.
- **No data.** It takes nothing from the inventory or the phone: no `sms:`, no `tel:`, no item
  id, no price, no `const _C`, no script. `noindex`, no Open Graph tags (no card for a broken
  link).
- **Its own copy** in `locales/not_found.yaml`, not in `en.yaml`/`es.yaml`, whose keys all travel
  to the catalog page as inline JSON.
- **End build keeps it.** `END_SITE_FILES` lists `404.html`, so the sweep of stale output leaves
  it, and `_redirects` (`/i/*`, `/es/i/*`, `/flyer`, `/flyer/*`) still sends those paths to the
  end page and nothing else. An end build that served the catalog's SPA fallback would be the
  opposite of its purpose, so it emits the page too, under the same no-contact rules.
- **Smoke.** `scripts/smoke.sh` requests `/smoke-not-found-<random>/` in both branches and
  requires a 404 whose body is the not-found page, with retries for a fresh deployment.

## Out of scope

- Per-language or per-section 404 pages (`/es/404.html`, `/i/404.html`).
- Changing `_redirects`, the Access middleware or the share pages.

## Risks / open questions

- **Real Pages behaviour.** The 404 status and `_headers` applying to the 404 response can only
  be confirmed on a deploy; the smoke asserts the status on every deploy from now on.
- **Anything that relied on the fallback.** Reasoned through in `verification.md`: nothing does.

## Acceptance criteria

- [ ] **AC1: the page exists in both modes.** `build/public/404.html` is written by the catalog build and by the end build, and the end build's published files are exactly the previous set plus it.
- [ ] **AC2: bilingual, linked, out of search.** It carries the heading, text and home link of both languages, links to `/` and `/es/`, and is `noindex`.
- [ ] **AC3: no contact, no item data.** In either mode, with a sentinel `SELLER_PHONE`, it holds no phone in any form, no `sms:`/`tel:`, no `const _C`, no script, no item id, no price and no `data-item=`.
- [ ] **AC4: it works at any depth.** Every `href`/`src` is root-absolute and resolves to the same URL from `/`, `/es/`, `/i/<id>/` and a deeper path; each target is a file of the site, and the stylesheet is the compiled `/styles.css`.
- [ ] **AC5: the end build still sweeps and redirects.** A catalog left in the output is swept without removing `404.html`, and `_redirects` has no rule that catches it.
- [ ] **AC6: smoke asserts a 404.** `scripts/smoke.sh` passes against both builds served with a 404 page, and fails when an unknown path answers 200 or answers 404 with another body.
- [ ] **AC7: the stylesheet covers it.** Every class of `not_found.html` has a rule in the compiled CSS.

## References

- Issue #152; lesson-025 (Pages answers a missing file with the home page), lesson-026
- OPS-011 (end-of-sale: `END_SITE_FILES`, `END_REDIRECTS`), ADR-004 (link-preview crawlers)

<!-- archived 2026-10-03 — PR: https://github.com/mlorentedev/leaving-denver/pull/183 -->
