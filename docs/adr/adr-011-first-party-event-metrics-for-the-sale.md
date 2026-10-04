---
id: "ADR-011-first-party-event-metrics-for-the-sale"
type: adr
status: accepted
owner: manu
date: "2026-10-03"
issue: "mlorentedev/leaving-denver#177"
tags: [architecture, decision, monitoring, privacy, cloudflare]
created: "2026-10-03"
---

# ADR-011: First-Party Event Metrics for the Sale

## Status

Accepted. It amends ADR-005: Cloudflare Web Analytics stays on and unchanged, and a small first-party
event beacon now covers what it cannot see. ADR-002 (the phone is never sent anywhere), ADR-007
(`/seller/*` has no network at all) and ADR-008 (the project outlives the sale) hold.

## Date

2026-10-03

## Context

The owner posted printed flyers and wants to know what they bring and which items buyers want, then
to read it once a day. ADR-005's tool cannot say either:

- Its FAQ says Web Analytics does not log query strings, "to avoid collecting potentially sensitive
  data". The flyer QR encodes `?utm_source=flyer&utm_medium=print&utm_campaign=moving-sale` and is
  already printed (`FLYER_UTM`, FEAT-010), so a scan is a direct visit there. ADR-005 said the
  runbook would check whether the dashboard reports UTMs: it does not.
- It has no custom events ("Not yet", same FAQ), so it cannot say which item was opened or texted about.
  Items that many people open and nobody texts about are the repricing signal.

Verified against Cloudflare's documentation (2026-10-03):

- **Workers Analytics Engine is on the Workers Free plan**: 100,000 data points written and 10,000
  read queries per day. It is not billed yet. Retention is three months. Limits: one index of at most
  96 bytes, 20 blobs and 20 doubles per point.
- **Pages Functions can bind it**: top-level `[[analytics_engine_datasets]]` with `binding` and
  `dataset` in `wrangler.toml` (the same syntax as a Worker), or Settings > Bindings in the dashboard.
  The dataset is created by the first write. The binding cannot be used in local development.
- **The SQL API** is `POST https://api.cloudflare.com/client/v4/accounts/<account_id>/analytics_engine/sql`
  with a bearer token holding **Account | Account Analytics | Read**. Sampled data needs
  `SUM(_sample_interval)`, not `COUNT()`.
- **The Web Analytics GraphQL dataset** (`rumPageloadEventsAdaptiveGroups` under `viewer.accounts`,
  filter `siteTag`) is not described in Cloudflare's own docs, only listed in its data-localization
  page; its fields come from public code that queries it. The same token reads it.

## Decision

- **A beacon in the catalog page**, in its existing inline script. It sends `{event, source, locale,
  item | bundle}` with `navigator.sendBeacon` to the same origin's `/api/hit`: `visit` (once, when the
  URL has `utm_source`, after which the utm parameters leave the address bar), `view_item` (a sheet
  opens) and `text_tap` (any text link). The source is kept in `sessionStorage` for the tab and is
  `direct` without one. No cookie, no IP, no user id, no phone, no other origin, no new inline
  handler: a Content-Security-Policy with `connect-src 'self'` lets it through.
- **The share page forwards its query string** to the catalog. The seller tool's links are
  `/i/<id>/?utm_source=<channel>`, and the page used to drop the query on its way to `/#<id>`, so no
  channel but the flyer would have shown.
- **`functions/api/hit.js`** takes `POST` only, validates strictly, and writes one data point
  `[event, source, item, bundle, locale]` (count 1, index = event) to the `SALE_METRICS` binding.
  It reads nothing of the request but its body. Bad input is a 400, anything else a 204.
  `functions/_middleware.js` passes `/api/*` through; `/seller/*` is untouched.
- **A daily n8n digest by email** (`sale_metrics_daily_digest.json`) queries the SQL API and the
  Web Analytics GraphQL for the last 24 hours and the whole sale, and ends with the repricing hint.
  The recipient and sender are n8n variables and the credentials are named, so nothing private is in
  the repository.
- **Counts are events, not people.** No unique visitors are computed.

## Consequences

### Positive

- The flyer is a measurable channel, and so is each seller-tool channel; the owner sees which items
  get opened and which get a text, which is what repricing needs.
- All on the free plan, no new dependency, no new origin, no cookie banner.

### Negative

- It is a second analytics path to keep, with an allow-list of sources in `hit.js`. A test fails when
  a channel in the seller tool or in `make post` is missing from it.
- Only a visit that carries `utm_source` is sent: direct visits are Web Analytics' to count. A forged
  request can inflate a count; the free plan's write cap bounds it.
- The write path cannot run locally. It is tested with a fake binding, and the live SQL and GraphQL
  text is run once by the owner (runbook). The GraphQL dataset is undocumented by Cloudflare and may change.
- The first deploy with a binding in `wrangler.toml` must be checked: the file is the source of truth
  for the project's configuration, so `/seller/` must still reach Access (runbook).
- Preview deployments write to the same dataset.
- Three months of retention is longer than the sale, and the dataset, the workflow and the token are
  removed by Nov 15 (decommission runbook).

### Neutral

- The Web Analytics beacon is unchanged and ADR-005's CSP note stays: a policy must allow it.

## References

- ADR-002, ADR-005, ADR-007, ADR-008; lessons 008 (honest urgency: these counts are not shown to buyers) and 024
- Spec: `specs/FEAT-015-sale-metrics/`; issue `mlorentedev/leaving-denver#177`
- Runbooks: `docs/runbooks/ops.md` ("Sale metrics"), `docs/runbooks/kubelab-integration.md`
