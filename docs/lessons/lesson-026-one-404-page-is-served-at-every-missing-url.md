---
id: "lesson-one-404-page-is-served-at-every-missing-url"
type: lesson
scope: local
tags: [cloudflare, html, testing, i18n]
created: "2026-10-01"
source: "BUG-013 / issue #152"
---

# Lesson: One 404 Page Is Served at Every Missing URL

## Context

With no top-level `404.html`, Cloudflare Pages runs the site as a single-page app: every path it
has no file for answers `200` with the catalog (lesson-025 met this from the smoke's side). Adding
the file turns those into real 404s, and Pages serves its body at the URL that was asked for.

## Finding

A page written like the others, with `href="styles.css"` or `../styles.css`, would break: at
`/i/sofa-sleeper/nope` the browser resolves it to `/i/sofa-sleeper/styles.css` and shows an
unstyled page, and no build-time check of the file in `build/public/` sees it, because the file is
fine where it sits. The same single file also has to serve both languages, since a bare `/nope`
carries none.

## Guard

`tests/test_not_found.py` resolves every `href`/`src` of the built page against `/`, `/es/`,
`/i/<id>/` and a deeper path, and requires the same URL each time, and a file of the site. The
page's copy lives in `locales/not_found.yaml`, outside `en.yaml`/`es.yaml`, whose keys all ship to
the catalog as inline JSON. `scripts/smoke.sh` asserts every deploy answers an unknown path with a
404 and this page.

## Rule

A page the host serves for URLs you do not control is resolved against those URLs, not its own
location: root-absolute references, no language assumption, no data. Test it from a nested path,
not from where the file is written.
