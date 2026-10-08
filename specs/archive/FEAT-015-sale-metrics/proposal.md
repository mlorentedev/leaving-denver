---
id: "FEAT-015-sale-metrics"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-08: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-08)."
created: "2026-10-03"
issue: "mlorentedev/leaving-denver#177"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
wip_override: "the 15 active specs are shipped work waiting on the owner's archive (chore/archive-specs); this change is time-boxed to the sale (15 active, limit 10, 2026-10-03)"
---

# FEAT-015-sale-metrics

## Why

The owner has already posted paper flyers and wants to know what they bring and which items people want, then to read that once a day without opening a dashboard. Cloudflare Web Analytics (ADR-005) cannot answer: its FAQ says it does not log query strings, so a scan of the flyer QR (`?utm_source=flyer&...`, already printed, FLYER_UTM) is a direct visit there, and it has no custom events, so it cannot say which item a buyer asked about. Without that, repricing is a guess: an item many people open and nobody texts about is overpriced, and the owner has no way to see it.

## What

- **A first-party beacon in the catalog page.** No cookie, no IP, no user id, no phone number. It sends `{event, source, locale, item | bundle}` to the same origin's `/api/hit` with `navigator.sendBeacon`:
  - `visit`, once, when the URL carries `utm_source`. The utm parameters are then removed from the address bar (`history.replaceState`, hash kept) so a shared link does not carry them, and the source is kept in `sessionStorage` for the rest of the tab.
  - `view_item`, when an item sheet opens.
  - `text_tap`, on tapping any text-me link: the item button, the bundle button, the item sheet's bundle offer, the sticky "Text me". The car's button is the item button. The link keeps working: the beacon never delays or cancels it.
- **The share page forwards its query string.** Seller-tool links are `/i/<id>/?utm_source=<channel>&...`, and the share page replaced the location with `../../#<id>`, which drops the query: every channel but the flyer would have read as direct. It now sends `../../<query>#<id>`.
- **A Pages Function, `functions/api/hit.js`**, `POST` only. It validates strictly (allow-listed events, `^[a-z0-9-]{1,64}$` ids, known sources else `other`, locale `en|es`), writes one data point to Workers Analytics Engine through the `SALE_METRICS` binding declared in `wrangler.toml`, and answers 204. Bad input is a 400, never a 5xx; a missing binding is still a 204. It reads no header and no `request.cf`.
- **An n8n workflow, `sale_metrics_daily_digest.json`**, daily at 08:00 America/Denver: queries the Analytics Engine SQL API (visits by source, text taps by item, item views by item; the last 24 hours and the sale so far) and Cloudflare Web Analytics' GraphQL (page views and top referrer hosts, last 24 hours), and **emails** a plain-text digest through n8n's Send Email (SMTP) node. It ends with the hint that an item with many views and no text taps is a repricing candidate (`make reprice`). Credentials are named, never inlined; the recipient and sender come from n8n environment variables, so no address is in the public repo.
- **Docs.** ADR-011 (amends ADR-005), the runbook sections for the owner's setup and for reading Web Analytics meanwhile, and the teardown of the workflow, the token and the dataset in `decommission.md`.

## Out of scope

- Counting direct visits in the beacon: only a visit that carries `utm_source` is sent (Web Analytics already counts the rest). A reload after the strip is not a second visit.
- Any identifier of a person or a device, any cookie, any third-party host. Unique visitors are not measured; counts are events.
- Creating the Cloudflare token, the dataset binding in the dashboard or the n8n credentials: owner steps in the runbook. Nothing is deployed from this change.
- Changing the printed flyer URL.
- `/seller/*`: it is behind Access with `connect-src 'none'` and carries no beacon.

## Risks / open questions

- **Not run against the live API.** Analytics Engine bindings cannot be used locally (Cloudflare docs), and no deploy is in scope, so the write path is proven with a fake binding and the real SQL and GraphQL text is not executed here. The runbook has the owner run each query once with `curl`.
- **The RUM GraphQL dataset is not documented.** `rumPageloadEventsAdaptiveGroups` is listed by Cloudflare only in its data-localization page; the field names come from public code that queries it. The digest runs that query in its own step, which cannot fail the email.
- **CSP.** A parallel change adds a Content-Security-Policy. The beacon is same-origin (`connect-src 'self'`), adds no inline handler and no new origin; the code lives in the page's existing inline script.
- **Honesty and privacy.** Counts of taps are the seller's private signal, shown nowhere on the page (lesson-008: no fake urgency, no social proof from these numbers). The payload holds no phone; the browser test checks every captured payload for the number.
- **Spam.** The endpoint is public. A forged request can inflate counts, nothing more; the write is bounded by the 100,000 data points a day of the free plan. Accepted.
- **Source allow-list drift.** A channel the seller tool adds must be in the function's list or it reads as `other`; a test fails when a `channels.py` channel or a `seller.mjs` source is missing.

## Acceptance criteria

- [ ] **AC1: validation.** `hit.js` writes exactly one data point `[event, source, item, bundle, locale]` for a valid payload; an unknown event, a malformed or oversized body or a non-object is a 400 and writes nothing; an id that is not `^[a-z0-9-]{1,64}$` is dropped, an unknown source becomes `other`; a missing binding or a throwing one still answers 204; only POST is handled.
- [ ] **AC2: nothing personal.** The function reads no request header and not `request.cf`; the data point holds no field outside the five.
- [ ] **AC3: the visit.** A page opened with `?utm_source=flyer&utm_medium=print&utm_campaign=moving-sale` sends one `visit` for `flyer` to `/api/hit`, then its address bar has no utm parameter and keeps the hash; a page with no utm sends none; a reload after the strip sends none.
- [ ] **AC4: the taps.** Tapping the item button, the car's button, the bundle button, the sheet's bundle offer and the sticky "Text me" each sends one `text_tap` with the item or bundle id (none for the sticky) and the landing source (`direct` without one); each link's `sms:` href is unchanged and the click is not cancelled by the beacon. The contact sheet's own hand-off is not counted twice.
- [ ] **AC5: the views.** Opening an item sheet sends `view_item` with its id; opening a linked item (`/#id`) counts as well.
- [ ] **AC6: ADR-002 and CSP.** No captured payload holds the phone (with `SELLER_PHONE` set to a sentinel) or `sms:`; every request goes to `/api/hit` on the page's own origin; the page has no new inline event handler and no new host.
- [ ] **AC7: share links keep their source.** `/i/<id>/?utm_source=facebook` lands on the catalog with the query and the hash, in both locales, and its `visit` is `facebook`.
- [ ] **AC8: the binding.** `wrangler.toml` declares `SALE_METRICS` with an `[[analytics_engine_datasets]]` block; `/api/hit` is not under `/seller/` and the middleware passes it through (`context.next()`).
- [ ] **AC9: the workflow.** `sale_metrics_daily_digest.json` is valid n8n JSON with a daily 08:00 schedule in America/Denver, the Analytics Engine SQL and the GraphQL requests, and an Email Send (SMTP) node; it holds no secret and no recipient address, names its credentials, mentions no Telegram, and carries no price or item title; the digest text carries the `make reprice` hint.
- [ ] **AC10: the docs.** ADR-011, a runbook section for the token (Account Analytics Read), the credentials, the variables, import and activation, the Web Analytics reading, and the teardown by Nov 15 in `decommission.md`.
- [ ] **AC11: the end of the sale.** The new catalog-reading browser tests are in `CATALOG_TESTS`, and `make check` passes with `seller.sale_over: true`.

## References

- Issue #177
- ADR-002 (the phone is never sent), ADR-005 (Web Analytics, amended by ADR-011), ADR-007 (`/seller/*` policy), ADR-008 (the Pages project outlives the sale)
- Lessons 008 (honest urgency), 024 (CSP and inline script)
- Cloudflare docs: Analytics Engine (get started, limits, pricing, SQL API), Pages Functions bindings, Web Analytics FAQ

<!-- archived 2026-10-07 — PR: https://github.com/mlorentedev/leaving-denver/pull/239 -->
