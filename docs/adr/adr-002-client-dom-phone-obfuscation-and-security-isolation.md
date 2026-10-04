---
id: "ADR-002-client-dom-phone-obfuscation-and-security-isolation"
type: adr
status: accepted
owner: manu
date: "2026-09-25"
issue: ""
tags: [architecture, security, privacy, scraper-defense]
created: "2026-09-25"
---

# ADR-002: Client DOM Phone Obfuscation and Security Isolation

## Status

Accepted. Decision 1 stands. Decision 2 is superseded by ADR-007: there is no `build/private/`
and no local PIN gate any more. `poster_assistant.html` went in FEAT-009, and the one build
output, `build/public/`, holds the seller tool at `/seller/` with the ciphertext of the private
data, sealed on the owner's machine under a passphrase only the owner knows. Plaintext still
never reaches `build/public/`.

## Date

2026-09-25

## Context

Publishing contact details on public websites invites aggressive automated scraping from VoIP telemarketers and spam rings. Simultaneously, the liquidation workflow requires an internal tool (`poster_assistant.html`) with multi-portal listing copy, reserve floor prices, and pricing strategies that must never leak to prospective buyers or public search indexes.

## Decision

1. **Client DOM Phone Obfuscation:** The public `index.html` must never contain plaintext phone numbers or raw `href="sms:..."` attributes in static markup. Instead, data attributes split the country code, prefix, and line number. Client JavaScript constructs the interactive SMS links dynamically at runtime.
2. **Strict Output Isolation (superseded by ADR-007):** Build output was separated into `build/public/` (public artifacts only) and `build/private/` (internal operator tools with reserve floor prices). Cloudflare Pages deployed only `build/public/`; `build/private/` was gitignored and protected by a local master PIN gate. ADR-007 replaced this: `build/private/` and the PIN gate are gone, and the private data reaches the phone only as ciphertext inside `build/public/seller/index.html`.

## Consequences

### Positive
- Zero exposure of telephone numbers to static HTTP scrapers (curl, BeautifulSoup, regex bots).
- Hard barrier preventing accidental publication of internal reserve floor prices and seller margins.
- Automated security verification in CI via `tests/test_security_isolation.py`.

### Negative
- Users with JavaScript disabled cannot click-to-SMS (negligible on mobile iOS/Android browsers).

### Neutral
- Internal tools require manual local hosting via `leaving-denver serve`.

## References
- `docs/lessons/lesson-002-client-dom-phone-obfuscation-scraping-defense.md`
- `tests/test_security_isolation.py`
