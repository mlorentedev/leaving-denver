---
id: "ADR-010-public-pages-content-security-policy-and-security-headers"
type: adr
status: accepted
owner: manu
date: "2026-10-03"
tags: [architecture, decision, security, headers, csp]
created: "2026-10-03"
---

# ADR-010: Public Pages Get a Content-Security-Policy and the Standard Security Headers

## Status

Accepted. It amends **ADR-005**, negative consequence 1 ("if a Content-Security-Policy is ever
added, it must allow the beacon"): the policy now exists and does. It sits beside **ADR-007**,
which keeps `/seller/*` on its own, stricter policy set by `functions/_middleware.js`; nothing here
touches that file.

## Date

2026-10-03

## Context

A header scanner flagged the production site for no `Strict-Transport-Security`, no
`Content-Security-Policy`, no `Permissions-Policy`, and `access-control-allow-origin: *`. Until
now `_headers` carried four headers (`nosniff`, `X-Frame-Options`, `Referrer-Policy`,
`X-Robots-Tag`) and ADR-005 deliberately had no policy.

What the pages needed in order to take a strict policy:

- The catalog carried one large inline `<script>` (contact data, the inventory, the page logic),
  six `onclick=` attributes, one `style=` attribute and an inline `<style>`; the flyer, the end page
  and the 404 page each had an inline `<style>`; each share page had a one-line inline redirect.
- Cloudflare Web Analytics is switched on in the dashboard and injects an external script
  (`static.cloudflareinsights.com`) that reports to `cloudflareinsights.com` (ADR-005).
- Pages' `_headers`: up to 100 rules and 2,000 characters a line; a header written twice is joined
  with a comma; a header can be detached with `! Name`; rules do not apply to responses generated
  by Functions.
- A repeated `Content-Security-Policy` is not merged: a browser enforces each value, so two
  policies leave a page only what both allow.
- The 404 page is served at the URL that was asked for (lesson-026), so only a `/*` rule reaches it.

## Decision

### 1. One policy, on `/*`, with the inline scripts listed by hash

```
default-src 'none'; script-src 'self' https://static.cloudflareinsights.com <hashes>;
style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self' https://cloudflareinsights.com;
frame-ancestors 'none'; base-uri 'none'; object-src 'none'; form-action 'none'
```

- `script-src` lists `'sha256-...'` for **every inline script the build emitted** (the English
  catalog, the Spanish catalog, and the one share-page redirect). `site_builder.write_headers()`
  computes them from the pages as written, and runs last in both builds, so a page made after it
  cannot carry an unlisted script. A hash is additive: the Spanish catalog's hash on the English
  page allows nothing the site does not already ship.
- Nothing is allowed inline in styles or markup: the build moved every `<style>` into
  `public.css` (and the flyer's print rules into `assets/flyer.css`), replaced the `style=`
  attribute with a Tailwind class, and replaced each `onclick=` with a `data-` attribute wired in
  the page script. No `'unsafe-inline'`, `'unsafe-eval'` or `'unsafe-hashes'`.
- The share-page redirect is the same script on every page (`location.replace` of the link in the
  page), so 80 share pages cost one hash and the policy stays one line, far under the limits.
- `connect-src 'self'` keeps a future first-party `/api/hit` beacon possible.
- `/*` also matches `/seller/*`. The static policy has none of the seller policy's directives and
  the middleware sets its header with `.set()`, so a seller response holds one policy, whether
  or not Pages applies `_headers` to it. A test pins that the static headers never carry the
  seller policy.
- Why hashes and not external script files: hashing is a build step with a test that fails if the
  policy and the emitted pages drift, and it leaves the page's script, its globals and the many
  browser tests that call them untouched. Moving the code to files would have been a large
  refactor for the same protection. The cost is coupling: an edge that rewrites the HTML would
  break the hashes, which is why `scripts/smoke.sh` checks, on the served `/`, that every inline
  script it finds is in the served policy.

### 2. The other headers

| Header | Value | Why |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Every host under `leaving-denver.pages.dev` (the previews) is ours. No `preload`: it is not reversible quickly and `pages.dev` is not ours to submit. |
| `Permissions-Policy` | denies camera, microphone, geolocation, payment, usb, serial, hid, midi, sensors, wake lock, display capture, idle detection, browsing topics, autoplay, WebAuthn get, XR; `clipboard-write=(self)` | The share button (`navigator.share`) and the copy buttons (`navigator.clipboard`) must keep working. `web-share` is not named: its default is `self`, and Chrome logs an *error* for a feature name it does not know on its platform; desktop Linux, where Lighthouse runs, does not know `web-share` or `bluetooth`, and a console error costs the Best Practices score. A test fails on any unknown name. |
| `Cross-Origin-Opener-Policy` | `same-origin` | Nothing here opens or is opened by a cross-origin window. |
| `! Access-Control-Allow-Origin` | detached | Pages adds `*` to static assets. No page here is read cross-origin; the font preload is same-origin CORS and needs no header. |

Not added:

- **COEP.** `require-corp` would block the beacon and any image that sends no CORP header.
- **CORP `same-site`.** `pages.dev` is on the Public Suffix List, so `same-site` is `same-origin`
  here. Link-preview fetchers are servers and ignore CORP, so previews would survive, but it
  would break a photo hotlinked from the owner's own listing on another site and protects nothing:
  every byte is public. The gain does not pay for a break nobody can enumerate.
- **`<link rel="preconnect" href="https://cloudflareinsights.com">`.** ADR-005 decided the
  repository ships no beacon and `tests/test_ops_runbook.py` fails if `cloudflareinsights` is in a
  template; a hint naming it would be the first mention and would survive turning the setting off.

### 3. Lighthouse findings fixed in the same change

- `<meta name="description">` on the catalog and end pages, from the existing hero line (never a
  sale date).
- `hreflang` links were relative, which Lighthouse rejects. They are absolute on `site_url()`,
  with an `x-default`.
- SEO stays low by design: `noindex` and the robots rules are ADR-004/ADR-009, and not touched.
- Photo URLs are not content-hashed (lesson-016), so cache lifetimes are unchanged.

## Consequences

### Positive

- A script injected into a page does not run: only the site's files, the beacon and the build's own
  inline scripts do. The page cannot be framed, post a form, or load a plugin.
- The test that matters runs the built site over HTTP with its own `_headers` applied, in headless
  Chrome (catalog in both languages, an item sheet, the gallery, share, the contact sheet, a share
  page, the flyer, the 404 and both end pages), and fails on any `securitypolicyviolation` or
  console error. Mutating the build to drop the hashes fails it.
- `scripts/smoke.sh` fails a deployment that stops sending HSTS, the policy or the permissions
  policy, or whose policy does not list the served page's inline scripts.

### Negative

- A new inline script is blocked until the build emits it, and the build does that by itself; a new
  inline `style=`, `<style>` or `on...=` is blocked, and a test names it.
- Cloudflare features that rewrite HTML (Rocket Loader, Auto Minify) must stay off. The smoke
  catches the hash mismatch after a deploy, not before.
- What no test here can see: that Cloudflare applies `/*` to the 404 response and to a URL with a
  query string, and that it honours the `!` detach. The first is proven by the candidate smoke on
  merge (it reads the served `/`), the 404 case and the detach are not gated: a deployment that
  still sends `access-control-allow-origin` prints a `SMOKE WARN`.

### Neutral

- The seller page is unchanged: its policy and its blocking of the beacon are ADR-007's.

## References

- ADR-005 (beacon), ADR-007 (seller policy), ADR-004 (crawlers)
- lesson-024 (CSP needs an HTTP-served test), lesson-026 (the 404), lesson-028 (this change)
- Cloudflare Pages `_headers`: <https://developers.cloudflare.com/pages/configuration/headers/>
