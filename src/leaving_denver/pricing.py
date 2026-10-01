"""
Price tiers and drop steps, shared by `leaving-denver drops` and the control panel.

The tiers start from the asking price in force (`recommended_list_price`) and the item's
reserve floor, so a repriced item steps down from where it is now.
"""

from datetime import date
from typing import Any

# The sale windows a drop can happen in, in order (sale_schedule names them).
DROP_WINDOWS = ("first_drop", "second_drop", "clear_floors")


def price_tiers(item: dict[str, Any], floor: int | None) -> tuple[int, int, int]:
    """(list, drop, floor): the drop is halfway to the floor, rounded to $5 ($100 for the car).

    An item with no floor on file keeps its list price in all three, which is what `drops`
    always printed for it."""
    list_price = item.get("recommended_list_price", 0)
    low = list_price if floor is None else floor
    step = 100 if item.get("category") == "Vehicle" else 5
    return list_price, round((list_price + low) / 2 / step) * step, low


def next_drop(
    item: dict[str, Any],
    floor: int | None,
    schedule: dict[str, tuple[date, date]],
    today: date,
    repriced_on: list[date],
) -> dict[str, Any] | None:
    """The first drop window the price log does not cover yet, with the price to move to.

    A window is covered once a reprice is logged on or after the day it opens. The last
    window is the floor itself; earlier ones step halfway. None when there is nothing to
    drop: not for sale, free with purchase, no floor on file, or already at the floor."""
    if item.get("status", "Available") != "Available" or item.get("free_with_purchase"):
        return None
    asking, step_price, low = price_tiers(item, floor)
    if low >= asking:
        return None
    last = max(repriced_on, default=None)
    for window in DROP_WINDOWS:
        opens = schedule[window][0]
        if last is None or last < opens:
            price = low if window == "clear_floors" else step_price
            return {"on": opens, "price": price, "overdue": opens < today}
    return None
