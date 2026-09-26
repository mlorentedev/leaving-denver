"""
n8n Integration Module for Moving Sale.
Connects with kubelab services (n8n webhooks, Apprise notifications, Vikunja task boards).
"""

import json
import urllib.error
import urllib.request


def dispatch_inquiry_webhook(
    webhook_url: str,
    item_id: str,
    item_title: str,
    price: int,
    buyer_name: str,
    buyer_phone: str,
    notes: str | None = None,
) -> bool:
    """Dispatches a buyer inquiry payload to the kubelab n8n webhook."""
    payload = {
        "source": "moving-sale-catalog",
        "item_id": item_id,
        "item_title": item_title,
        "price": price,
        "buyer_name": buyer_name,
        "buyer_phone": buyer_phone,
        "notes": notes or "Interested in pickup at DTC.",
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in (200, 201, 204)
    except Exception as exc:
        print(f"Failed to dispatch inquiry to n8n ({webhook_url}): {exc}")
        return False
