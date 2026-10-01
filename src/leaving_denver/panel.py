"""
The seller's private control panel (FEAT-004).

`panel_rows` joins the public inventory with the decrypted private data (floors, targets,
sales, tracking) into one row per item; `render_panel` turns the rows into a local HTML
file. Everything private is passed in, so nothing here reads the encrypted file, and the
page is only ever written under build/private/ (see `write_panel`).
"""

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from leaving_denver.config import DIST_DIR, PRIVATE_PANEL_HTML
from leaving_denver.pricing import next_drop
from leaving_denver.site_builder import render, sale_schedule

# Where an item can be listed, and how to take it down once it sells.
CHANNELS = {
    "facebook": "Facebook Marketplace: open 'Your Listings' and mark it Sold",
    "craigslist": "Craigslist: delete the post from your account dashboard",
    "offerup": "OfferUp: archive it or mark it sold",
    "nextdoor": "Nextdoor: mark the post sold or update it",
    "activebuilding": "Complex portal (ActiveBuilding): remove or update the post",
}
# Channels whose listings go stale: days until the post must be renewed (docs/runbooks/seller-playbook.md).
RENEW_AFTER_DAYS = {"facebook": 7}


def as_date(value: Any) -> date | None:
    """A date from what the private file holds: a date, a datetime or an ISO string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def posted_dates(tracking: dict[str, Any]) -> dict[str, list[date]]:
    """Each channel's posting dates, oldest first (a renewal is another posting)."""
    return {
        channel: sorted(as_date(d) for d in dates)
        for channel, dates in (tracking.get("channels") or {}).items()
        if dates
    }


def price_log(tracking: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        {"at": as_date(e["at"]), "price": e["price"]} for e in tracking.get("price_log") or []
    ]
    return sorted(entries, key=lambda e: e["at"])


def read_sale(entry: Any) -> dict[str, Any] | None:
    """A sale as {price, at}; the old shape was a bare price."""
    if entry is None:
        return None
    if isinstance(entry, dict):
        return {"price": entry.get("price"), "at": as_date(entry.get("at"))}
    return {"price": entry, "at": None}


def days_listed(posts: dict[str, list[date]], end: date) -> int | None:
    first = min((d[0] for d in posts.values()), default=None)
    # A sale dated before the first posting (a typo, a backfill) shows 0, never negative days.
    return None if first is None else max((end - first).days, 0)


def renew_due(posts: dict[str, list[date]]) -> date | None:
    """The soonest renewal across the channels that need one."""
    dues = [
        posts[channel][-1] + timedelta(days=days)
        for channel, days in RENEW_AFTER_DAYS.items()
        if channel in posts
    ]
    return min(dues, default=None)


def private_value(private: dict[str, Any], section: str, item_id: str) -> Any:
    """One item's entry in a private section; a missing or null section reads as empty."""
    return (private.get(section) or {}).get(item_id)


def listing_end(status: str, sale: dict[str, Any] | None, today: date) -> date:
    """Days listed stop at the sale date once the item is sold, else run to today."""
    sold_on = sale["at"] if status == "Sold" and sale else None
    return sold_on or today


def item_row(
    item: dict[str, Any],
    private: dict[str, Any],
    schedule: dict[str, tuple[date, date]],
    today: date,
) -> dict[str, Any]:
    item_id = item["id"]
    tracking = private_value(private, "tracking", item_id) or {}
    posts = posted_dates(tracking)
    log = price_log(tracking)
    sale = read_sale(private_value(private, "sales", item_id))
    status = item.get("status", "Available")
    due = None if status == "Sold" else renew_due(posts)
    floor = private_value(private, "floors", item_id)
    asking = item.get("recommended_list_price")
    return {
        "id": item_id,
        "title": item.get("short_title") or item.get("title") or item_id,
        "category": item.get("category"),
        "status": status,
        "draft": item.get("published", True) is False,
        "free": bool(item.get("free_with_purchase")),
        "asking": asking,
        "target": private_value(private, "targets", item_id),
        "floor": floor,
        "days_listed": days_listed(posts, listing_end(status, sale, today)),
        "channels": [{"name": c, "last": d[-1], "posts": len(d)} for c, d in posts.items()],
        "renew_due": due,
        "renew_overdue": due is not None and due <= today,
        "next_drop": next_drop(item, floor, schedule, today, [e["at"] for e in log]),
        "price_log": log,
        "log_mismatch": bool(log) and log[-1]["price"] != asking,
        "sale": sale,
    }


def panel_rows(data: dict[str, Any], private: dict[str, Any], today: date) -> list[dict[str, Any]]:
    """One row per inventory item, in inventory order. Missing private data leaves a field empty."""
    schedule = sale_schedule(data["seller"]["departure_date"])
    return [item_row(item, private, schedule, today) for item in data["items"]]


def panel_actions(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """What needs doing now: renewals due today or past, drops whose window has opened."""
    return {
        "renewals": [r for r in rows if r["renew_overdue"]],
        "drops": [r for r in rows if r["next_drop"] and r["next_drop"]["overdue"]],
    }


def takedown_steps(item_id: str, private: dict[str, Any]) -> list[str]:
    """Where to take a sold item's listing down: the channels it was posted on, else all."""
    tracking = private_value(private, "tracking", item_id) or {}
    posted = [channel for channel in posted_dates(tracking) if channel in CHANNELS]
    if posted:
        return [CHANNELS[channel] for channel in posted]
    return ["No posting recorded for this item, so check every channel:", *CHANNELS.values()]


def render_panel(rows: list[dict[str, Any]], today: date) -> str:
    return render("panel.html", rows=rows, today=today, actions=panel_actions(rows))


def write_panel(html: str, out: Path = PRIVATE_PANEL_HTML) -> Path:
    """Write the page owner-readable only, and never inside the public build."""
    if out.resolve().is_relative_to(DIST_DIR.resolve()):
        raise RuntimeError(f"Refusing to write the private panel under the public build: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as f:
        f.write(html)
    out.chmod(0o600)
    return out
