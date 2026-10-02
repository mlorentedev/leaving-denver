"""
Price tiers for `leaving-denver drops`.

The tiers start from the asking price in force (`recommended_list_price`) and the item's
reserve floor, so a repriced item steps down from where it is now. The private views in
/seller/ compute the same tiers and the next drop in the browser (`priceTiers` and `nextDrop`
in assets/seller.mjs); a test compares the tiers.
"""

from typing import Any

# The household windows a drop can happen in, in order (`seller.price_schedule` opens them).
DROP_WINDOWS = ("first_drop", "second_drop", "clear_floors")


def price_tiers(item: dict[str, Any], floor: int | None) -> tuple[int, int, int]:
    """(list, drop, floor): the drop is halfway to the floor, rounded to $5 ($100 for the car).

    An item with no floor on file keeps its list price in all three, which is what `drops`
    always printed for it."""
    list_price = item.get("recommended_list_price", 0)
    low = list_price if floor is None else floor
    step = 100 if item.get("category") == "Vehicle" else 5
    return list_price, round((list_price + low) / 2 / step) * step, low
