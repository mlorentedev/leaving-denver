"""
Items are Available, Pending (reserved, awaiting pickup) or Sold, and the page says which
(FEAT-006). Sold items sort last; a bundle is on sale only while all its items are.
"""

import argparse
import re
from types import SimpleNamespace

import pytest

from leaving_denver import cli, site_builder


def data(**statuses):
    items = [
        {"id": i, "category": "Living Room", "title": i, "recommended_list_price": 10, "status": s}
        for i, s in statuses.items()
    ]
    return {
        "items": items,
        "bundles": [
            {"id": "ab", "name": "AB", "items": ["a", "b"], "bundle_price": 15},
            {"id": "cd", "name": "CD", "items": ["c", "d"], "bundle_price": 15},
        ],
    }


def test_unknown_status_fails_the_build():
    with pytest.raises(RuntimeError, match="b.*Reserved"):
        site_builder.sanitize_public_inventory(
            data(a="Available", b="Reserved", c="Sold", d="Sold")
        )


def test_status_defaults_to_available():
    inv = data(a="Available", b="Available", c="Available", d="Available")
    del inv["items"][0]["status"]
    public = site_builder.sanitize_public_inventory(inv)
    assert public["items"][0]["status"] == "Available"


def test_sold_items_sort_last_and_the_rest_keep_their_order():
    public = site_builder.sanitize_public_inventory(
        data(a="Sold", b="Available", c="Pending", d="Available")
    )
    assert [i["id"] for i in public["items"]] == ["b", "c", "d", "a"]


@pytest.mark.parametrize("taken", ["Pending", "Sold"])
def test_bundle_with_a_taken_item_is_unavailable(taken):
    public = site_builder.sanitize_public_inventory(
        data(a="Available", b=taken, c="Available", d="Available")
    )
    availability = {b["id"]: b["available"] for b in public["bundles"]}
    assert availability == {"ab": False, "cd": True}


def test_realized_price_stays_private():
    inv = data(a="Sold", b="Available", c="Available", d="Available")
    inv["items"][0]["realized_price"] = 7
    public = site_builder.sanitize_public_inventory(inv)
    assert "realized_price" not in public["items"][-1]
    assert "7" not in repr(public["items"][-1].values())


def test_status_label_is_localized_and_the_key_kept():
    inv = data(a="Pending", b="Available", c="Available", d="Available")
    public = site_builder.sanitize_public_inventory(inv)
    for locale in ("en", "es"):
        translations = site_builder.load_locale(locale)
        localized = site_builder.localize_public_inventory(public, inv, locale, translations, "")
        item = localized["items"][0]
        assert item["status"] == "Pending"
        assert item["status_label"] == translations["statuses"]["Pending"]


@pytest.mark.parametrize(
    ("command", "status"), [("pending", "Pending"), ("available", "Available"), ("sold", "Sold")]
)
def test_status_commands_set_the_status_and_rebuild(monkeypatch, command, status):
    inv = data(a="Available", b="Pending", c="Available", d="Available")
    saved, built = [], []
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: inv)
    monkeypatch.setattr(cli, "save_inventory_yaml", saved.append)
    monkeypatch.setattr(cli, "build_all", lambda: built.append(True))
    # `sold` records the day and reads the tracking: never against the owner's real file.
    monkeypatch.setattr(cli, "record_sale", lambda *args: None)
    monkeypatch.setattr(cli, "load_private", lambda: {})
    getattr(cli, f"cmd_{command}")(SimpleNamespace(id="b", price=None))
    assert saved[0]["items"][1]["status"] == status
    assert built


def test_status_commands_reject_an_unknown_id(monkeypatch):
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: data(a="Available", b="", c="", d=""))
    monkeypatch.setattr(cli, "save_inventory_yaml", lambda d: pytest.fail("saved"))
    with pytest.raises(SystemExit):
        cli.cmd_pending(argparse.Namespace(id="nope", price=None))


# --- The page -------------------------------------------------------------------------

PHONE = "+15555550100"


@pytest.fixture
def page(tmp_path, monkeypatch):
    """The real catalog, with one item sold and one reserved, rendered in EN."""
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    inv = site_builder.load_inventory_yaml()
    bundle = next(b for b in inv["bundles"] if not b.get("everything"))
    sold, pending = (
        bundle["items"][0],
        next(
            i["id"]
            for i in inv["items"]
            if i["category"] != "Vehicle" and i["id"] not in bundle["items"]
        ),
    )
    for item in inv["items"]:
        item["status"] = {sold: "Sold", pending: "Pending"}.get(item["id"], item.get("status"))
    site_builder.build_public_site(inv)
    html = (dist / "index.html").read_text(encoding="utf-8")
    return SimpleNamespace(html=html, inv=inv, sold=sold, pending=pending, bundle=bundle["id"])


def card_for(html, item_id):
    start = html.index(f'data-item="{item_id}"')
    return html[html.rindex("<button", 0, start) : html.index("</button>", start)]


def test_sold_card_is_last_dimmed_and_struck(page):
    ids = re.findall(r'class="item-card[^"]*" data-item="([^"]+)"', page.html)
    assert ids[-1] == page.sold
    sold = card_for(page.html, page.sold)
    assert 'data-status="Sold"' in sold
    # The photo fades; the text does not, so it keeps its contrast.
    assert re.search(r'<img [^>]*class="[^"]*opacity-60', sold) and "line-through" in sold
    assert not re.search(r"<button [^>]*opacity-", sold)
    assert ">Sold<" in sold


def test_pending_card_says_pending_pickup(page):
    pending = card_for(page.html, page.pending)
    assert 'data-status="Pending"' in pending and ">Pending pickup<" in pending
    assert "opacity-60" not in pending


def test_bundle_with_a_sold_item_is_off_sale(page):
    start = page.html.index(f'data-bundle="{page.bundle}"')
    card = page.html[page.html.rindex("<button", 0, start) : page.html.index("</button>", start)]
    assert 'data-available="false"' in card and "No longer available" in card
    sheet = re.search(rf'data-bundle-sheet="{page.bundle}".*?</section>', page.html, re.S).group(0)
    assert "data-sms-intent" not in sheet
    # Every other bundle but "take everything" (which holds the sold item too) stays on sale.
    others = re.findall(r'data-bundle="([^"]+)"[^>]*data-available="true"', page.html)
    assert page.bundle not in others and others


def test_sheet_logic_follows_the_status(page):
    js = "".join(re.findall(r"<script>(.*?)</script>", page.html, re.S))
    # No text link on a sold item; the upsell only offers a bundle still on sale.
    assert "item.status === 'Sold'" in js
    assert "b.available && !b.everything" in js


def test_availability_line_counts_from_the_data(page):
    household = [
        i for i in page.inv["items"] if i["category"] != "Vehicle" and i.get("published", True)
    ]
    available = sum(i.get("status", "Available") == "Available" for i in household)
    line = re.search(r'data-role="availability"[^>]*>(.*?)<', page.html).group(1)
    assert line.strip() == f"{available} of {len(household)} available · 1 sold"
