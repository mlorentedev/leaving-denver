---
id: "BUG-003-tailwind-v4"
type: spec
status: verifying
created: "2026-09-29"
issue: "mlorentedev/leaving-denver#8"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# BUG-003-tailwind-v4

> **Naming**: file lives at `<repo>/specs/BUG-003-tailwind-v4/proposal.md`. `BUG-003-tailwind-v4` is `AREA-NNN-slug` (e.g. `TOOL-001-secret-drift`).

## Why

<!-- from issue #8: BUG-003: Replace the Tailwind play CDN with a v4 build step -->

Issue #8: the play CDN loads Tailwind v3 JavaScript at runtime while both templates use v4 utilities, leaving those styles missing; a failed CDN request leaves both sites unstyled. The public EN/ES catalog and local private seller assistant need reliable, locally compiled styles without changing their data or privacy contracts.

## What

Every generated HTML page links to a stylesheet shipped alongside its own distribution. A pinned Tailwind v4 CLI build produces that CSS from both templates (including dynamic class names); direct `leaving-denver build` and Make/CI builds compile it or fail with a clear prerequisite error. No Tailwind runtime script is loaded.

## Out of scope

Things this PR explicitly does NOT include. Forces a sharp boundary and prevents scope creep.

- Redesign, translations, seller data, inventory or image processing.
- Hosting private assets on Cloudflare Pages; only `build/public/` is deployed.

## Risks / open questions

Failure modes, dependencies, and unknowns to clarify before implementation. If any item here is unresolved, do not move to `tasks.md` yet.

- Tailwind source scanning must include both templates and static JS class strings; use explicit template sources rather than inventory or build outputs.
- A missing Node/npm toolchain or CLI build must stop direct builds before a stale stylesheet can ship. CI must install the pinned locked dependencies.

## Acceptance criteria

Observable outcomes. Each must be testable.

- [x] Public EN and ES pages link to an existing local CSS asset and neither loads the Tailwind play CDN.
- [x] The local private assistant links to its own existing stylesheet, does not load the CDN, and no private data or assistant asset appears under `build/public/`.
- [x] Compiled CSS contains working v4-only utilities used by both templates (including `aspect-4/3`, `shadow-2xs`, `backdrop-blur-xs`, `scale-101`) and the Plus Jakarta Sans font theme.
- [x] `make check` and direct CLI builds produce fresh CSS using pinned dependencies; missing CSS tooling fails explicitly rather than shipping an unstyled page.

## References

- Bitácora board: the GitHub issue / Project item tracking this spec (see the `issue:` frontmatter field)
- Related ADR: `docs/adr/adr-002-client-dom-phone-obfuscation-and-security-isolation.md`
