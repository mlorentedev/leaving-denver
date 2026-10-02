---
id: "ADR-009-let-assistants-a-person-asked-read-the-catalog"
type: adr
status: accepted
owner: manu
date: "2026-10-02"
tags: [architecture, decision, web, privacy]
created: "2026-10-02"
---

# ADR-009: Let Assistants a Person Asked Read the Catalog

## Status

Accepted. It extends ADR-004 (link-preview crawlers) and keeps ADR-001's indexer block.

## Date

2026-10-02

## Context

`robots.txt` disallows every user agent but the link-preview crawlers (ADR-004). AI assistants that honour it refuse to open the site, so a buyer who pastes a listing link into one and asks "is this a fair price?" gets no answer. The owner hit this with an agent of his own.

The assistants publish separate user agents for separate jobs. One fetches a page because a person asked in a chat (`ChatGPT-User`, `Claude-User`, `Perplexity-User`, `MistralAI-User`). Others crawl to train models or build a search index (`GPTBot`, `ClaudeBot`, `OAI-SearchBot`, `PerplexityBot` and so on). Only the first kind matches what ADR-004 already allows: one page, fetched because someone shared or asked about it.

No `llms.txt` is added: an agent that honours `robots.txt` never reaches it.

## Decision

- `robots.txt` names the assistant fetchers (`ASSISTANT_FETCHERS` in `site_builder.py`) with `Allow: /`.
- `/seller/` is not named. Cloudflare Access guards it (ADR-007), so a fetcher gets the login page, and a `Disallow: /seller/` line would only advertise the path to anyone reading `robots.txt`.
- Training and search crawlers are not named, so `User-agent: *` / `Disallow: /` still covers them.
- `X-Robots-Tag: noindex` and the `noindex` meta stay on every page.

## Consequences

### Positive

- A buyer's assistant can read the listing, the price and the car's specs.
- No training or search crawler is let in, and nothing enters a search index.

### Negative

- Like the preview crawlers, anyone can claim these user agents. `robots.txt` was never enforcement, the phone keeps its JavaScript assembly (ADR-002), and `/seller/` stays behind Cloudflare Access (ADR-007).
- The list needs an edit when an assistant renames its fetcher. A missing name only means that assistant still refuses, as today.

## References

- ADR-001 (crawler policy), ADR-002 (contact obfuscation), ADR-004 (link-preview crawlers), ADR-007 (seller tool)
- Tests: `tests/test_security_isolation.py`
