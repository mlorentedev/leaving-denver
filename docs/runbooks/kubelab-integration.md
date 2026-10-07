# Kubelab & n8n Integration Guide

Two n8n workflows run on the private homelab (`kubelab`) alongside the sale: a Telegram
reminder to renew the Craigslist listings, and a daily email with the sale's metrics. The first
lives in this repository and is imported by hand; the second is owned and imported as code by the
kubelab repository. The catalog itself is a static site and calls
nothing in the homelab; buyers reach the seller by text message.

---

## 1. Kubelab services used

* **n8n:** runs the scheduled workflow.
* **Telegram:** delivers the reminder to the seller's phone.
* **SMTP relay:** delivers the metrics digest, in a channel apart from Telegram, through kubelab's
  shared n8n credential `kubelab-smtp`.

---

## 2. Craigslist 48-Hour Bump Reminder Cron

Craigslist Denver ranks listings in strict reverse-chronological order. Listings drop to page 4+ after 48 hours.

1. Import `integrations/n8n/workflows/craigslist_48h_bump_reminder.json` into n8n.
2. The cron triggers every 48 hours at 9:00 AM MST.
3. Sends a direct link to `https://post.craigslist.org/manage` to hit "Renew" on the free household listings that offer it.

The message names no item and no price: prices live in `data/inventory.yaml` and a copy typed
into the workflow goes stale. The car's paid cars-by-owner post cannot be renewed (repost it
only after it expires; see [seller-playbook.md](seller-playbook.md)), so the reminder leaves it out.

When the sale ends, deactivate the workflow on kubelab: [decommission.md](decommission.md), "By Nov 9".

---

## 3. Sale Metrics Daily Digest

Emails the owner, every day at 08:00 America/Denver, which channels brought visits (the printed
flyer included), which items were opened and texted about, Cloudflare Web Analytics' page views
and top referrers, and the items worth repricing. The data is first-party (ADR-011): the page
sends events to `/api/hit`, a Pages Function writes them to Workers Analytics Engine, and the
workflow reads them back with the SQL API.

The workflow is not in this repository. kubelab owns it (kubelab#2088, kubelab#2090):
`infra/n8n/workflows/sale-metrics-daily-digest.json` in `mlorentedev/kubelab`, imported as code,
prod only. Its README, "Removing the sale (2026-11-09)", is the teardown. It holds nothing
private: the three values below are filled in at import from kubelab's encrypted secrets, and the
workflow reads no n8n variable.

1. Set the three values in kubelab's SOPS, from the kubelab checkout, one at a time and never
   echoed (the exact commands are in [ops.md](ops.md), "Sale metrics", step 5):
   - `apps.services.automation.n8n.sale_digest.analytics_token`: a Cloudflare **user token**
     (My Profile > API Tokens), not an account token. kubelab's expiry check asks
     `/user/tokens/verify`, which an account token does not answer. Permission Account | Account
     Analytics | Read.
   - `apps.services.automation.n8n.sale_digest.recipient`: the address that reads the digest.
     It is deliberately not in this public repository.
   - `apps.services.automation.n8n.sale_digest.site_tag`: the Web Analytics site tag.
2. Email goes through `kubelab-smtp`, the shared SMTP credential kubelab renders from its own relay
   settings. Nothing to create in n8n: the import makes it, and the sender is the relay's account.
3. From the kubelab checkout: `toolkit infra n8n import --env prod --dry-run`, then
   `make import-n8n ENV=prod`. A missing value fails the import before anything is applied and
   names the path.
4. The workflow is live as soon as it is imported; there is no step that switches it on. The first
   email is the next 08:00 America/Denver, or run Execute workflow once in the n8n UI to see it
   now.

The step-by-step (creating the token, trying both queries, what the digest means) is in
[ops.md](ops.md), "Sale metrics". When the sale ends, remove it the way kubelab's
`infra/n8n/workflows/README.md`, "Removing the sale (2026-11-09)", says; this repository's side is
[decommission.md](decommission.md), "By Nov 9". `kubelab-smtp` stays: it is shared.
