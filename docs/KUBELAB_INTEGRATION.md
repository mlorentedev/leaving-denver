# Kubelab & n8n Integration Guide

This guide explains how to connect the moving sale catalog with your private Kubernetes homelab (`kubelab`) infrastructure.

---

## 1. Available Kubelab Services Utilized

* **n8n:** Workflow automation & inbound webhook receiver.
* **Apprise / Telegram:** Real-time push alerts to your phone upon buyer inquiry.
* **Vikunja:** Kanban task creation for scheduling furniture test drives and pickups.
* **Cloudflare Pages / Tunnels:** Zero-cost, high-speed static hosting with automatic SSL.

---

## 2. Inbound Buyer Inquiries Workflow

When an interested buyer clicks an inquiry link or submits an inquiry from the web catalog:

```
[Buyer on Catalog]
       │ (HTTP POST Webhook)
       ▼
[n8n Webhook: /webhook/moving-sale-inquiry]
       ├──► [Telegram Alert to Your Phone] (Item, Buyer Name, Phone, Desired Time)
       └──► [Vikunja API Task Created]     (Due Date set to pickup time)
```

### Setup in n8n:
1. Open n8n in your browser (`https://n8n.kubelab.local` or tunnel URL).
2. Go to **Workflows** -> **Import from File**.
3. Select `n8n/workflows/moving_sale_inquiry_to_telegram.json`.
4. Ensure environment variables or credentials for `TELEGRAM_CHAT_ID` and `VIKUNJA_API_TOKEN` are active.
5. Click **Activate**.

---

## 3. Craigslist 48-Hour Bump Reminder Cron

Craigslist Denver ranks listings in strict reverse-chronological order. Listings drop to page 4+ after 48 hours.

1. Import `n8n/workflows/craigslist_48h_bump_reminder.json` into n8n.
2. The cron triggers every 48 hours at 9:00 AM MST.
3. Sends a direct link to `https://post.craigslist.org/manage` to hit "Renew" on all active listings in 30 seconds.

---

## 4. Mobile Photo Drop Integration (Optional)

You can configure an n8n Telegram Bot node:
* Send a photo of any item directly to your private Telegram bot with caption `#vehicle` or `#sofa`.
* n8n saves the image into `/data/leaving-denver/content/photos/<item_id>/`.
* A webhook triggers `python3 manage.py build && python3 manage.py deploy-cf`.
