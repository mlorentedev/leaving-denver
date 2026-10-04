# Kubelab & n8n Integration Guide

Two n8n workflows run on the private homelab (`kubelab`) alongside the sale: a Telegram
reminder to renew the Craigslist listings, and a daily email with the sale's metrics. The catalog itself is a static site and calls
nothing in the homelab; buyers reach the seller by text message.

---

## 1. Kubelab services used

* **n8n:** runs the scheduled workflow.
* **Telegram:** delivers the reminder to the seller's phone.
* **SMTP mailbox:** delivers the metrics digest, in a channel apart from Telegram.

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

1. Import `integrations/n8n/workflows/sale_metrics_daily_digest.json` into n8n. It arrives switched off.
2. Credentials, by name only (nothing is in the file): Header Auth `cloudflare-analytics-read`
   (`Authorization: Bearer <token>`, token permission Account | Account Analytics | Read) and SMTP
   `sale-digest-smtp`.
3. n8n variables: `SALE_DIGEST_TO`, `SALE_DIGEST_FROM`, `CF_WEB_ANALYTICS_SITE_TAG`. The recipient
   address is deliberately not in this public repository.
4. Execute once, check the email, switch Active on.

The step-by-step (creating the token, trying both queries, what the digest means) is in
[ops.md](ops.md), "Sale metrics". Deactivate the workflow when the sale ends:
[decommission.md](decommission.md), "By Nov 9".
