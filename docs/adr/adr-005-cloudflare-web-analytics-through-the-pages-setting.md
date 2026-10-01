---
id: "ADR-005-cloudflare-web-analytics-through-the-pages-setting"
type: adr
status: accepted
owner: manu
date: "2026-09-30"
issue: "mlorentedev/leaving-denver#39"
tags: [architecture, decision, monitoring, privacy]
created: "2026-09-30"
---

# ADR-005: Cloudflare Web Analytics Through the Pages Setting

## Status

Accepted

## Date

2026-09-30

## Context

OPS-012 asks for Cloudflare Web Analytics, to see which channel (Nextdoor, Marketplace, Craigslist) brings visits to a six-week sale. It works by a small script, `https://static.cloudflareinsights.com/beacon.min.js`, that reports each page view to `cloudflareinsights.com`. That is the first third-party script the site would load, so it needs a decision.

What the repo says today:

- **No Content-Security-Policy.** The page's `<meta>` tags are charset, viewport and robots. `PAGES_HEADERS` sets `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `X-Robots-Tag`, and nothing else. Nothing blocks the beacon.
- **No ADR or test forbids third-party scripts.** The nearest rules are PERF-001 (no third-party *font* requests, `tests/test_self_hosted_font.py`) and ADR-002 (the phone is never in static markup and is assembled client-side).
- The site is already served and its requests terminated by Cloudflare, so Web Analytics adds no new party that sees the visits. Cloudflare states the beacon sets no cookies and does not fingerprint visitors.

## Decision

- Web Analytics is switched on by the owner in the Cloudflare Pages project (Workers & Pages > `leaving-denver` > Metrics > Web Analytics). Cloudflare then adds the beacon to the HTML it serves.
- **The repository ships no beacon.** No template carries a `<script>` for it and no build step injects one. `tests/test_ops_runbook.py` fails if `cloudflareinsights` appears in a template: a copy there would count every visit twice and survive turning the setting off.
- The beacon never reads the page's contact data. ADR-002 is unaffected: the phone is still assembled in the browser from data attributes, and nothing in the beacon's reports carries it.
- Channels are told apart by referrer, and by the UTM parameters on the links the seller tool builds (`utm_source`, `utm_campaign`) if the dashboard reports them. The runbook has the owner check that before relying on it. No personal data goes into a URL.

## Consequences

### Positive

- No code, no dependency and no deploy to turn it on or off: the Pages setting is reversible at once.
- Nothing to keep current in the repo. The smoke test (`scripts/smoke.sh`) is unaffected, since it asserts on the page's own content.

### Negative

- If a Content-Security-Policy is ever added, it must allow `static.cloudflareinsights.com` in `script-src` and `cloudflareinsights.com` in `connect-src`, or the beacon is silently blocked and the dashboard goes quiet. `test_no_csp_stops_the_cloudflare_beacon` fails on a policy that does not.
- Visits are measured by a third-party script on every page, including the share pages. Visitors who block scripts are not counted.
- The repo cannot prove the setting is on. It is an owner step, verified with `curl -s https://leaving-denver.pages.dev/ | grep -c cloudflareinsights` and a test visit (runbook `ops.md`, "Minimal monitoring").

### Neutral

- Cloudflare's reports show page, referrer, country and device class. No visitor identity is stored by this site.

## References

- ADR-002 (contact obfuscation), ADR-004 (crawler policy)
- Issue: `mlorentedev/leaving-denver#39`
- Runbook: `docs/runbooks/ops.md`, "Minimal monitoring (owner setup)"
