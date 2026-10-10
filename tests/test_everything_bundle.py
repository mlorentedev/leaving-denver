"""
FEAT-018: "Take everything" is derived from what is still for sale, so a sale lowers its price
instead of taking it off sale. The data keeps only the discount.
"""

import pytest

from leaving_denver import site_builder


def item(item_id, price, status="Available", **extra):
    return {
        "id": item_id,
        "category": extra.pop("category", "Living Room"),
        "title": item_id,
        "recommended_list_price": price,
        "status": status,
        **extra,
    }


def inventory(*items, everything=None):
    bundle = {"id": "all", "name": "All", "everything": True, "discount_pct": 20}
    bundle.update(everything or {})
    return {"items": list(items), "bundles": [bundle]}


def everything_of(data):
    public = site_builder.sanitize_public_inventory(data)
    return next((b for b in public["bundles"] if b["everything"]), None)


def test_it_holds_what_is_for_sale_at_the_discount_rounded_down_to_five():
    bundle = everything_of(inventory(item("a", 220), item("b", 95), item("c", 85)))
    assert sorted(bundle["items"]) == ["a", "b", "c"]
    # 400 at 20% off is 320; already a multiple of 5.
    assert (bundle["individual_total"], bundle["bundle_price"]) == (400, 320)
    assert bundle["savings"] == 80 and bundle["available"]


def test_the_price_rounds_down_to_a_multiple_of_five():
    bundle = everything_of(inventory(item("a", 37), item("b", 20)))
    # 57 at 20% off is 45.6: down to 45, never up.
    assert bundle["bundle_price"] == 45


@pytest.mark.parametrize("taken", ["Sold", "Pending"])
def test_a_sold_or_reserved_item_leaves_it_and_lowers_the_price(taken):
    bundle = everything_of(inventory(item("a", 100), item("b", 100), item("c", 50, taken)))
    assert sorted(bundle["items"]) == ["a", "b"]
    assert bundle["bundle_price"] == 160 and bundle["available"]


def test_the_car_and_unpublished_items_are_never_in_it():
    bundle = everything_of(
        inventory(
            item("a", 100),
            item("b", 100),
            item("car", 9000, category="Vehicle"),
            item("hidden", 50, published=False),
        )
    )
    assert sorted(bundle["items"]) == ["a", "b"]


def test_a_free_item_counts_as_an_item_but_adds_nothing_to_the_price():
    bundle = everything_of(
        inventory(item("a", 100), item("b", 100), item("free", 20, free_with_purchase=True))
    )
    assert "free" in bundle["items"]
    assert (bundle["individual_total"], bundle["bundle_price"]) == (200, 160)


def test_with_fewer_than_two_items_left_there_is_no_bundle():
    assert everything_of(inventory(item("a", 100), item("b", 100, "Sold"))) is None


@pytest.mark.parametrize("typed", [{"items": ["a", "b"]}, {"bundle_price": 100}])
def test_a_typed_list_or_price_is_refused(typed):
    with pytest.raises(RuntimeError, match="all"):
        everything_of(inventory(item("a", 100), item("b", 100), everything=typed))


def test_a_missing_discount_is_refused():
    data = inventory(item("a", 100), item("b", 100))
    del data["bundles"][0]["discount_pct"]
    with pytest.raises(RuntimeError, match="all.*discount_pct"):
        everything_of(data)


@pytest.mark.parametrize("discount", [True, False, "20", 20.5, None])
def test_a_discount_that_is_not_a_whole_number_is_refused(discount):
    data = inventory(item("a", 100), item("b", 100))
    data["bundles"][0]["discount_pct"] = discount
    with pytest.raises(RuntimeError, match="all.*discount_pct"):
        everything_of(data)


def test_the_page_renders_without_it(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    data = site_builder.load_inventory_yaml()
    household = [i for i in data["items"] if i["category"] != "Vehicle"]
    for i in household[1:]:
        i["status"] = "Sold"
    data["bundles"] = [b for b in data["bundles"] if b.get("everything")]
    site_builder.build_public_site(data)
    html = (dist / "index.html").read_text(encoding="utf-8")
    assert "data-everything=" not in html and "data-bundle-sheet=" not in html


def test_the_real_page_offers_it_at_the_derived_price():
    data = site_builder.load_inventory_yaml()
    bundle = everything_of(data)
    on_offer = [
        i
        for i in data["items"]
        if i["category"] != "Vehicle"
        and i.get("published", True)
        and i.get("status", "Available") == "Available"
    ]
    total = sum(0 if i.get("free_with_purchase") else i["recommended_list_price"] for i in on_offer)
    assert sorted(bundle["items"]) == sorted(i["id"] for i in on_offer)
    assert bundle["bundle_price"] == total * 80 // 100 // 5 * 5
