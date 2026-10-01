---
id: "FEAT-005-mobile-posters"
type: spec
status: implementing # draft | implementing | verifying | archived
created: "2026-09-29"
issue: "mlorentedev/leaving-denver#17"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-005: Owner-only mobile posters

## Why

<!-- from issue #17: FEAT-005: Poster tool: neighbor-voice copy, field buttons and UTM links -->

The seller needs the listing-copy generator on a phone, but the existing local
assistant includes reserve floors and negotiation notes and its JavaScript PIN
is not authentication. Publishing it would leak seller-only information. An
owner-only mobile version must remain usable without exposing those private
inputs if Cloudflare Access is disabled or a preview hostname is overlooked.

## What

Generate copy for Facebook, Craigslist, OfferUp and Nextdoor from **published,
sanitized inventory only** at `/seller/`. Cloudflare Access authenticates the
owner via a one-time email code; Pages middleware verifies the Access JWT on
every seller asset and fails closed if its audience/domain are unconfigured.
The existing local assistant retains reserve-price controls and is never
deployed. No editable inventory or negotiation state is exposed remotely.

## Out of scope

Things this PR explicitly does NOT include. Forces a sharp boundary and prevents scope creep.

- Uploading `build/private/`, publishing floor prices, or trusting the existing
  JavaScript PIN as authentication.
- Editing inventory, scheduling posts, or adding a server-side AI generation API.

## Risks / open questions

Failure modes, dependencies, and unknowns to clarify before implementation. If any item here is unresolved, do not move to `tasks.md` yet.

- Access applications, the allowed owner identity, team domain, and audience
  must be configured by an account administrator before announcing the URL.
  Existing Pages-only credentials may not have Zero Trust write permission.
- Access needs to cover the production hostname and all preview aliases;
  middleware independently validates JWTs so an alias cannot bypass it.
- A Pages asset may still be retrievable if routing is changed later. Therefore
  `/seller/` contains only data already safe for the public catalog.

## Acceptance criteria

Observable outcomes. Each must be testable.

- [ ] AC1: `/seller/` renders a phone-usable per-item copy generator from
  published available inventory, with selectable platforms and copyable
  title/description and a per-platform UTM-attributed item link.
  It never renders floors, internal notes, draft items, or a plaintext PIN.
- [ ] AC2: Every `/seller/` request passes Access JWT validation; unset Access
  configuration fails closed and a missing/invalid JWT is denied on every
  hostname, including preview URLs.
- [ ] AC3: `make check` verifies the public-only build and local private
  assistant still works; only `build/public/` deploys.
- [ ] AC4: A runbook explains owner-only Access configuration, all relevant
  hostnames, and an anonymous-versus-owner smoke test before advertising the
  mobile URL.

## References

- Bitácora: #17; existing private control panel #16 remains local.
- `docs/adr/adr-001-static-catalog-over-monolithic-attachment.md`
- `docs/adr/adr-002-static-site-buyer-contact.md`
