"""
The sale's arithmetic (OPS-018): expected against realized, by group, plus the days.

Everything this module needs is seller-only: the researched targets, the reserve floors and the
realized price of every sale live in `data/private.sops.yaml` (ADR-007), and the totals that come
out of adding them up are seller-only too. So the summary is printed by `leaving-denver retro`
and never written into the public tree: the end page and the case study carry percentages and
days, which are the two things that say how the sale went without saying what it paid.

The realized figures are money and are read from the encrypted sales record, not derived from the
item's status: a giveaway is a sale with a realized price of `0`, deliberately (the lifecycle in
FEAT-006 has no "given away" state), which is why the item's `disposition` and the record are
compared here instead of trusted one at a time.
"""

from datetime import date
from statistics import median
from typing import Any

from leaving_denver.config import DISPOSITIONS

HOUSEHOLD = "household"
VEHICLE = "vehicle"
TOTAL = "total"
GROUPS = (HOUSEHOLD, VEHICLE, TOTAL)


def as_date(value: Any) -> date:
    """A date from a `YYYY-MM-DD` string or a date; anything else is a data error."""
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"not a YYYY-MM-DD date: {value!r}") from None


def item_disposition(item: dict[str, Any]) -> str:
    """`sale` unless the item says otherwise: the field is optional and absent on most items."""
    disposition = item.get("disposition", "sale")
    if disposition not in DISPOSITIONS:
        raise ValueError(
            f"Item {item.get('id')}: disposition {disposition!r} is not one of {DISPOSITIONS}"
        )
    return disposition


def item_group(item: dict[str, Any]) -> str:
    return VEHICLE if item.get("category") == "Vehicle" else HOUSEHOLD


def item_days(item_id: str, sales: dict[str, Any], opened: date) -> int | None:
    """Days from the day the catalog opened to the day the item sold, or None when unrecorded.

    The start is the catalog's first day for every item, not that item's own first posting: the
    posting record covers two items only, so a per-item start would be a fact for two and a guess
    for the rest."""
    entry = sales.get(item_id) or {}
    at = entry.get("at")
    return (as_date(at) - opened).days if at else None


def _pct(part: int, whole: int) -> int | None:
    """A whole percentage of `whole`, or None when there is nothing to divide by."""
    return round(part / whole * 100) if whole else None


def _empty_group() -> dict[str, Any]:
    return {
        "items": 0,
        "sold": 0,
        "given": 0,
        "unplaced": 0,
        "realized": 0,
        "expected": 0,
        "expected_items": 0,
        "on_expected": 0,
        "asking": 0,
        "floors": 0,
        "days": [],
    }


def retro_summary(
    items: list[dict[str, Any]],
    targets: dict[str, Any],
    floors: dict[str, Any],
    sales: dict[str, Any],
    catalog_opened: Any,
) -> dict[str, Any]:
    """The aggregate: one group per kind of item plus the total, and the counts underneath.

    Pure: it takes the decrypted private data as arguments and touches no file, so the arithmetic
    is tested without sops or an age key."""
    opened = as_date(catalog_opened)
    groups = {name: _empty_group() for name in GROUPS}
    for item in items:
        item_id = item.get("id")
        disposition = item_disposition(item)
        status = item.get("status", "Available")
        realized = int((sales.get(item_id) or {}).get("price") or 0)
        for name in (item_group(item), TOTAL):
            group = groups[name]
            group["items"] += 1
            group["realized"] += realized
            group["asking"] += int(item.get("recommended_list_price") or 0)
            group["floors"] += int(floors.get(item_id) or 0)
            if item_id in targets:
                group["expected"] += int(targets[item_id] or 0)
                group["expected_items"] += 1
                group["on_expected"] += realized
            if status == "Sold":
                group["given" if disposition == "giveaway" else "sold"] += 1
            else:
                group["unplaced"] += 1
            days = item_days(item_id, sales, opened)
            # A giveaway sat until the end and sold nothing: counting its days as a sale's would
            # say the sale was slower than it was.
            if days is not None and realized:
                group["days"].append(days)

    for group in groups.values():
        # The realized figure compared against the targets is the one from the items that have
        # one: a group's whole money against the targets of a few would read as a triumph the
        # research had nothing to do with (the car has no target, and the bed listed too late).
        group["of_expected_pct"] = _pct(group["on_expected"], group["expected"])
        group["of_asking_pct"] = _pct(group["realized"], group["asking"])
        group["of_floors_pct"] = _pct(group["realized"], group["floors"])
        group["median_days"] = round(median(group["days"])) if group["days"] else None
        del group["days"]

    dates = [as_date(entry["at"]) for entry in sales.values() if entry.get("at")]
    last = max(dates) if dates else None
    return {
        "catalog_opened": opened.isoformat(),
        "last_sale": last.isoformat() if last else None,
        "span_days": (last - opened).days if last else None,
        # `total`, never `items`: the same dict is handed to the page template, where
        # `counts.items` would be the dict method.
        "counts": {
            "total": groups[TOTAL]["items"],
            "sold": groups[TOTAL]["sold"],
            "given": groups[TOTAL]["given"],
            "unplaced": groups[TOTAL]["unplaced"],
        },
        "groups": groups,
        "disagreements": disagreements(items, sales),
    }


def disagreements(items: list[dict[str, Any]], sales: dict[str, Any]) -> list[str]:
    """Items where the public disposition and the private record tell different stories.

    The two are one fact kept twice (the item is public, its price is not), so a run that does not
    compare them will publish a count that the money contradicts."""
    found = []
    for item in items:
        item_id = item.get("id")
        entry = sales.get(item_id)
        if item.get("status") != "Sold":
            continue
        if entry is None:
            found.append(f"{item_id}: Sold with no record of the price")
        elif item_disposition(item) == "giveaway" and int(entry.get("price") or 0) != 0:
            found.append(f"{item_id}: a giveaway with a price on file")
        elif item_disposition(item) == "sale" and int(entry.get("price") or 0) == 0:
            found.append(f"{item_id}: a sale with no price on file (a giveaway not declared)")
    return found


def _money(value: int) -> str:
    return f"${value:,}"


def _pct_text(value: int | None) -> str:
    return "n/a" if value is None else f"{value}%"


def render_text(summary: dict[str, Any]) -> str:
    """The seller's report: the table, then the counts, then anything that disagrees."""
    lines = ["SALE CLOSE-OUT (seller only: the private figures stay in this terminal)"]
    lines.append("")
    header = f"{'GROUP':<10} {'ITEMS':>5} {'EXPECTED':>13} {'REALIZED':>13} {'/EXPECT':>8} {'/ASK':>6} {'/FLOOR':>7} {'MED.DAYS':>9}"
    lines.append(header)
    lines.append("-" * len(header))
    for name in GROUPS:
        group = summary["groups"][name]
        expected = f"{_money(group['expected'])} ({group['expected_items']})"
        days = "n/a" if group["median_days"] is None else str(group["median_days"])
        lines.append(
            f"{name:<10} {group['items']:>5} {expected:>13} {_money(group['realized']):>13} "
            f"{_pct_text(group['of_expected_pct']):>8} {_pct_text(group['of_asking_pct']):>6} "
            f"{_pct_text(group['of_floors_pct']):>7} {days:>9}"
        )
    lines.append("-" * len(header))
    lines.append(
        "EXPECTED is the researched target price for the items that have one (the count in "
        "parentheses); a group's expected value covers those items only."
    )
    counts = summary["counts"]
    lines.append("")
    lines.append(
        f"Placed: {counts['sold'] + counts['given']} of {counts['total']} — "
        f"{counts['sold']} sold, {counts['given']} given away, {counts['unplaced']} unplaced."
    )
    lines.append(
        f"Days: catalog opened {summary['catalog_opened']}, last sale {summary['last_sale']}, "
        f"{summary['span_days']} days in total."
    )
    for key, label in (("asking", "asking"), ("floors", "reserve floors")):
        lines.append(f"Sum of {label} prices: {_money(summary['groups'][TOTAL][key])}.")
    if summary["disagreements"]:
        lines.append("")
        lines.append("DISAGREEMENTS between the inventory and the private record:")
        lines.extend(f"  - {line}" for line in summary["disagreements"])
    return "\n".join(lines)
