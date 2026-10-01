# Kubelab & n8n Integration Guide

One n8n workflow runs on the private homelab (`kubelab`) alongside the sale: a Telegram
reminder to renew the Craigslist listings. The catalog itself is a static site and calls
nothing in the homelab; buyers reach the seller by text message.

---

## 1. Kubelab services used

* **n8n:** runs the scheduled workflow.
* **Telegram:** delivers the reminder to the seller's phone.

---

## 2. Craigslist 48-Hour Bump Reminder Cron

Craigslist Denver ranks listings in strict reverse-chronological order. Listings drop to page 4+ after 48 hours.

1. Import `integrations/n8n/workflows/craigslist_48h_bump_reminder.json` into n8n.
2. The cron triggers every 48 hours at 9:00 AM MST.
3. Sends a direct link to `https://post.craigslist.org/manage` to hit "Renew" on all active listings in 30 seconds.
