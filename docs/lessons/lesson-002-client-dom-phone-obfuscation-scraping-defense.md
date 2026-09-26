---
id: "lesson-client-dom-phone-obfuscation-scraping-defense"
type: lesson
scope: local
tags: [movingsale, security, scraping, privacy, frontend]
created: "2026-09-25"
source: "Denver moving sale platform development"
---

# Lesson: Client-Side DOM Obfuscation Prevents Telemarketing Harassment on Classified Catalogs

## Context (The Problem/Error)
> "Publishing direct phone contact details as plaintext strings or raw `<a href="sms:...">` links in static HTML resulted in automated VoIP crawlers scraping the number within hours."

Public classified postings in Denver are systematically harvested by robocall spiders and spam bots that run headless regex matches on static markup.

## The Finding (Root Cause/Solution)
The root cause was embedding unencrypted contact markers directly in static HTML payloads crawled by simple HTTP GET bots.
The correct solution is storing phone components across segmented data attributes (`data-intent`, `data-pfx`, `data-num`) and reconstructing the `sms:` anchor and formatted display string dynamically at runtime via client JavaScript. Automated regex crawlers (curl, BeautifulSoup) see zero matching phone patterns, while real mobile visitors get seamless 1-tap SMS interactions.

## Anti-Pattern (What NOT to do)
Do not render raw phone numbers or hardcoded `sms:`/`tel:` protocol links in static HTML documents exposed on public networks.

## Golden Rule (The Pattern)
> **Whenever displaying contact phone numbers on public landing pages, reconstruct them dynamically in client-side JavaScript from split data attributes.**

## References
- `tests/test_security_isolation.py` (`test_public_html_has_no_raw_phone_plaintext`)
- `src/leaving_denver/site_builder.py` (DOM obfuscation renderer)
