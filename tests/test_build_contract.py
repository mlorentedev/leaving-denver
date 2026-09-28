"""
Build contract: the builder fails closed, and unpublished items never reach build/public/.
"""

import json
import re
from datetime import date
from html import unescape

import pytest
import yaml

from leaving_denver import site_builder

PHONE = "+15555550100"


def inventory(*, hidden_published=False):
    item = {
        "category": "Living Room",
        "brand": "Test",
        "recommended_list_price": 10,
        "original_price": 20,
        "dimensions": "1 x 1",
        "specs": ["a", "b"],
    }
    return {
        "seller": {
            "location": "DTC, CO 80111",
            "departure_date": "2026-11-09",
            "payment_methods": {
                "household": ["Cash", "Venmo", "Zelle"],
                "vehicle": ["Cash", "Cashier's check verified at the buyer's bank"],
            },
        },
        "items": [
            {**item, "id": "shown-lamp", "title": "Shown lamp"},
            {
                **item,
                "id": "hidden-widget",
                "title": "Hidden widget",
                "published": hidden_published,
            },
        ],
        "bundles": [
            {
                "id": "bundle-with-hidden",
                "name": "With hidden",
                "items": ["shown-lamp", "hidden-widget"],
                "bundle_price": 15,
            },
            {
                "id": "bundle-shown-only",
                "name": "Shown only",
                "items": ["shown-lamp"],
                "bundle_price": 8,
            },
        ],
    }


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


def text_under(root):
    """Every file path and file body under root, as one string."""
    parts = []
    for path in sorted(root.rglob("*")):
        parts.append(str(path.relative_to(root)))
        if path.is_file() and path.suffix in {".html", ".txt", ".json", ""}:
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


@pytest.mark.parametrize(
    ("script", "missing"),
    [
        ("const INVENTORY = {items: []};\nconst _C = {{ contact_json | safe }};", "inventory_json"),
        ("const INVENTORY = {{ inventory_json | safe }};\nconst _C = {};", "contact_json"),
    ],
)
def test_missing_marker_fails(public_dir, tmp_path, monkeypatch, script, missing):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "index.html").write_text(f"<script>{script}</script>")
    monkeypatch.setattr(site_builder, "TEMPLATES_DIR", templates)
    with pytest.raises(RuntimeError, match=missing):
        site_builder.build_public_site(inventory())


def test_unpublished_item_and_its_bundles_are_absent_from_public(public_dir):
    # A photo left over from an earlier build, when the item was still published.
    stale = public_dir / "catalog" / "hidden-widget" / "old.jpg"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"jpeg")

    site_builder.build_public_site(inventory())

    public = text_under(public_dir)
    assert "shown-lamp" in public
    assert "bundle-shown-only" in public
    assert "hidden-widget" not in public
    assert "bundle-with-hidden" not in public


def test_published_defaults_to_true(public_dir):
    site_builder.build_public_site(inventory(hidden_published=True))
    assert "hidden-widget" in text_under(public_dir)


def test_unpublished_item_is_in_private_marked_draft(tmp_path, monkeypatch):
    private_dir = tmp_path / "private"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.setattr(site_builder, "load_private", lambda: {"floors": {}})
    monkeypatch.setattr(site_builder, "DIST_PRIVATE_DIR", private_dir)
    monkeypatch.setattr(site_builder, "INVENTORY_JSON_PRIVATE", tmp_path / "inventory.json")
    monkeypatch.setattr(site_builder, "PRIVATE_POSTER_HTML", private_dir / "poster_assistant.html")

    site_builder.build_private_workspace(inventory())

    data = json.loads((private_dir / "inventory.json").read_text())
    drafts = {i["id"]: i.get("draft", False) for i in data["items"]}
    assert drafts == {"shown-lamp": False, "hidden-widget": True}
    assert "item.draft" in (private_dir / "poster_assistant.html").read_text(encoding="utf-8")


def test_publish_flag_survives_yaml_round_trip(tmp_path, monkeypatch):
    path = tmp_path / "inventory.yaml"
    path.write_text(yaml.dump(inventory(), sort_keys=False))
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", path)

    site_builder.save_inventory_yaml(site_builder.load_inventory_yaml())

    hidden = yaml.safe_load(path.read_text())["items"][1]
    assert hidden["published"] is False


def test_bundle_items_must_be_a_list(public_dir):
    data = inventory()
    data["bundles"][0]["items"] = "shown-lamp and hidden-widget"
    with pytest.raises(RuntimeError, match="bundle-with-hidden"):
        site_builder.build_public_site(data)


def test_undefined_field_fails_the_build(tmp_path, monkeypatch):
    from jinja2 import UndefinedError

    (tmp_path / "card.html").write_text("<h2>{{ item.titel }}</h2>")
    monkeypatch.setattr(site_builder, "TEMPLATES_DIR", tmp_path)
    with pytest.raises(UndefinedError, match="titel"):
        site_builder.render("card.html", item={"title": "Lamp"})


CAR = {
    "id": "2019-ford-escape-sel-awd",
    "category": "Vehicle",
    "title": "2019 Ford Escape SEL AWD",
    "short_title": "Ford Escape",
    "brand": "Ford",
    "model": "Escape SEL AWD",
    "year": 2019,
    "odometer": 103500,
    "title_status": "Clean Colorado title",
    "color": "White",
    "recommended_list_price": 11875,
}


@pytest.mark.parametrize("published", [True, False])
def test_vehicle_card_follows_the_publish_flag(public_dir, published):
    data = inventory()
    data["items"].append({**CAR, "published": published})

    site_builder.build_public_site(data)

    page = (public_dir / "index.html").read_text(encoding="utf-8")
    assert ("2019-ford-escape" in text_under(public_dir)) is published
    assert ("Vehicle" in page.split("<script>")[0]) is published


def test_item_text_cannot_close_the_script(public_dir):
    data = inventory()
    data["items"][0]["title"] = "Lamp </script><script>alert(1)</script>"

    site_builder.build_public_site(data)

    page = (public_dir / "index.html").read_text(encoding="utf-8")
    assert "</script><script>alert" not in page
    assert "Lamp \\u003c/script>" in page


def test_bundle_figures_come_from_items():
    data = inventory(hidden_published=True)
    data["items"][1]["recommended_list_price"] = 30
    data["bundles"][0]["individual_total"] = 999  # hand-typed figures are ignored
    public = site_builder.sanitize_public_inventory(data)
    figures = {b["id"]: (b["individual_total"], b["savings"]) for b in public["bundles"]}
    assert figures == {"bundle-with-hidden": (40, 25), "bundle-shown-only": (10, 2)}


def test_bundle_figures_count_free_items_as_zero():
    data = inventory(hidden_published=True)
    data["items"][1]["free_with_purchase"] = True
    public = site_builder.sanitize_public_inventory(data)
    widget = next(i for i in public["items"] if i["id"] == "hidden-widget")
    assert (widget["price"], widget["free"]) == (0, True)
    assert public["bundles"][0]["individual_total"] == 10


def test_every_category_has_a_chip(public_dir):
    data = inventory(hidden_published=True)
    data["items"][1]["category"] = "Garage"
    with pytest.raises(RuntimeError, match="Garage"):
        site_builder.build_public_site(data)


def real_page(public_dir):
    data = site_builder.load_inventory_yaml()
    site_builder.build_public_site(data)
    return data, (public_dir / "index.html").read_text(encoding="utf-8")


def card(html, attr, value, end="</a>"):
    """The markup of the card whose `attr` is `value`, up to its closing tag."""
    start = html.index(f'{attr}="{value}"')
    return html[start : html.index(end, start)]


def text_for_role(html, role):
    match = re.search(
        rf'<[^>]+data-role="{role}"[^>]*>(.*?)</[^>]+>',
        html,
        flags=re.DOTALL,
    )
    assert match, f"missing data-role={role}"
    return re.sub(r"<[^>]+>", " ", unescape(match.group(1)))


def test_page_figures_match_the_data(public_dir):
    data, html = real_page(public_dir)
    # Figures computed here from the YAML, independently of the builder.
    price = {
        i["id"]: 0 if i.get("free_with_purchase") else i["recommended_list_price"]
        for i in data["items"]
        if i.get("published", True)
    }
    household = [i for i in data["items"] if i["category"] != "Vehicle" and i["id"] in price]
    savings = set()
    for b in data["bundles"]:
        save = sum(price[i] for i in b["items"]) - b["bundle_price"]
        savings.add(save)
        attr = "data-everything" if b.get("everything") else "data-bundle"
        text = card(html, attr, b["id"])
        assert f"${b['bundle_price']}" in text, f"{b['id']} price"
        assert f"Save ${save}" in text, f"{b['id']} savings"
        assert f"{len(b['items'])} items" in text, f"{b['id']} item count"
    assert f"All · {len(household)}" in html
    assert html.count('class="item-card') == len(household)
    # No figure on the page that the data does not produce (the old banner typed $173).
    assert {int(s) for s in re.findall(r"Save \$(\d+)", html)} <= savings
    assert "UPSELL_MAP" not in html


def test_free_item_shows_its_note_not_a_price(public_dir):
    data, html = real_page(public_dir)
    for item in data["items"]:
        if item.get("free_with_purchase"):
            text = card(html, "data-item", item["id"], "</button>")
            assert item["note"] in text
            assert f"${item['recommended_list_price']}<" not in text


def test_mobile_shell_item_grid_has_two_columns(public_dir):
    _, html = real_page(public_dir)
    grid = re.search(r'<div id="itemsGrid" class="([^"]+)"', html)
    assert grid and "grid-cols-2" in grid.group(1).split()


def test_sale_schedule_comes_from_departure_date():
    schedule = site_builder.sale_schedule("2026-11-09")
    assert schedule == {
        "first_drop": (date(2026, 10, 3), date(2026, 10, 6)),
        "second_drop": (date(2026, 10, 15), date(2026, 10, 17)),
        "clear_floors": (date(2026, 10, 20), date(2026, 10, 25)),
        "giveaway": (date(2026, 11, 3), date(2026, 11, 5)),
    }
    shifted = site_builder.sale_schedule("2026-11-10")
    assert shifted["first_drop"] == (date(2026, 10, 4), date(2026, 10, 7))


def test_vehicle_card_claims_are_in_data(public_dir):
    data, html = real_page(public_dir)
    vehicle = next(item for item in data["items"] if item["category"] == "Vehicle")
    claims = [
        unescape(re.sub(r"<[^>]+>", "", claim)).strip()
        for claim in re.findall(
            r"<[^>]+data-vehicle-claim[^>]*>(.*?)</[^>]+>",
            html,
            flags=re.DOTALL,
        )
    ]
    assert len(claims) == 4
    assert set(claims) <= set(vehicle["specs"])


def test_payment_terms_by_kind(public_dir):
    data, html = real_page(public_dir)
    terms = text_for_role(html, "pickup-terms")
    seller = data["seller"]
    for method in seller["payment_methods"]["household"]:
        assert method in terms
    for method in seller["payment_methods"]["vehicle"]:
        assert method in terms
    vehicle_payment = " ".join(text_for_role(html, "vehicle-payment").split())
    assert vehicle_payment == " or ".join(seller["payment_methods"]["vehicle"])
    assert "no advance deposit" not in html.lower()


def test_mobile_copy_budget(public_dir):
    _, html = real_page(public_dir)
    hero = text_for_role(html, "hero-copy")
    pickup = text_for_role(html, "pickup-terms")
    assert len(hero.split()) <= 20
    assert len([part for part in re.split(r"[.!?]+", pickup) if part.strip()]) <= 2


def test_countdown_updates_in_browser_from_departure_date(public_dir):
    _, html = real_page(public_dir)
    assert 'data-departure-date="2026-11-09"' in html
    assert "function updateDepartureCountdown()" in html
    assert "America/Denver" in html
    assert "{{ days_remaining }}" not in html


def test_vehicle_poster_copy_uses_inventory_fields():
    template = (site_builder.TEMPLATES_DIR / "poster_assistant.html").read_text(encoding="utf-8")
    assert "Mileage: ${item.odometer.toLocaleString()}" in template
    assert template.count("${specs}") >= 2
    assert template.count("${inc}") >= 2
    assert template.count("${item.pickup_note}") >= 2
    assert template.count("${vehiclePayment}") >= 2
    for stale in (
        "Mileage: 103,500",
        "ready to sign over today",
        "valid, unused certificate",
        "Clean title ready in hand",
    ):
        assert stale not in template
