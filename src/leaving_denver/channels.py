"""
Where an item is listed, and what follows from it (FEAT-004, kept after the panel moved into
/seller/): the channel names `make post` accepts, how to take a sold item's listing down, and
the days a post may stand before it must be renewed.
"""

from datetime import date, datetime
from typing import Any

# Where an item can be listed, and how to take it down once it sells.
CHANNELS = {
    "facebook": "Facebook Marketplace: open 'Your Listings' and mark it Sold",
    "craigslist": "Craigslist: delete the post from your account dashboard",
    "offerup": "OfferUp: archive it or mark it sold",
    "nextdoor": "Nextdoor: mark the post sold or update it",
    "activebuilding": "Complex portal (ActiveBuilding): remove or update the post",
}
# Channels whose listings go stale: days until the post must be renewed (docs/runbooks/seller-playbook.md).
# The page reads this too (config.renew_after_days), so the renewals it flags are these.
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


def takedown_steps(item_id: str, private: dict[str, Any]) -> list[str]:
    """Where to take a sold item's listing down: the channels it was posted on, else all."""
    tracking = (private.get("tracking") or {}).get(item_id) or {}
    posted = [channel for channel in posted_dates(tracking) if channel in CHANNELS]
    if posted:
        return [CHANNELS[channel] for channel in posted]
    return ["No posting recorded for this item, so check every channel:", *CHANNELS.values()]
