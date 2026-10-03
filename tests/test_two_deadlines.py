"""
Two deadlines (OPS-013): household items go by 2026-10-23 and the car by 2026-11-09, and the
household price drops follow the owner's explicit dates instead of offsets from one departure.

Every build here is a scratch copy of the real inventory, so the tests read nothing of the live
`build/public` and keep running when `seller.sale_over` is committed on.
"""

import copy
import json
import re
import subprocess
import sys
from datetime import date
from html import unescape
from pathlib import Path

import pytest
import yaml

from leaving_denver import cli, private_data, site_builder
from leaving_denver.config import DATA_DIR

ROOT = Path(__file__).resolve().parents[1]
SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))
SENTINEL = "+13035550100"
CAR = "2019-ford-escape-sel-awd"


def catalog_inventory():
    data = copy.deepcopy(SOURCE)
    data["seller"].pop("sale_over", None)
    return data


def household(data):
    return [i for i in data["items"] if i["category"] != "Vehicle"]


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", SENTINEL)
    monkeypatch.delenv("SITE_URL", raising=False)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


def build(public_dir, data):
    site_builder.build_public_site(data)
    return {
        "en": (public_dir / "index.html").read_text(encoding="utf-8"),
        "es": (public_dir / "es" / "index.html").read_text(encoding="utf-8"),
        "flyer": (public_dir / "flyer" / "index.html").read_text(encoding="utf-8"),
        "seller": (public_dir / "seller" / "index.html").read_text(encoding="utf-8"),
    }


def text_of(page):
    body = re.search(r"<body.*?</body>", page, flags=re.DOTALL).group(0)
    body = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", body, flags=re.DOTALL)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", body))).strip()


def role(page, name):
    found = re.search(rf'data-role="{name}"[^>]*>(.*?)</', page, flags=re.DOTALL)
    assert found, name
    return " ".join(unescape(found.group(1)).split())


# Every way a deadline could be written on a public page (FEAT-014): ISO, US and Spanish.
DATE_SHAPES = (
    "2026-10-23",
    "2026-11-09",
    "October 23",
    "Oct 23",
    "10/23",
    "23 de octubre",
    "November 9",
    "Nov 9",
    "11/9",
    "9 de noviembre",
)


def public_pages(public_dir, pages):
    """Every page a buyer can reach: both catalogs, the flyer and the share pages."""
    shared = {str(p): p.read_text(encoding="utf-8") for p in (public_dir / "i").rglob("*.html")}
    return {"en": pages["en"], "es": pages["es"], "flyer": pages["flyer"], **shared}


def dates_on(page):
    return [shape for shape in DATE_SHAPES if shape in unescape(page)]


def description(page):
    return unescape(re.search(r'og:description" content="([^"]*)"', page).group(1))


def hide_household(data, *, sold=False):
    for item in household(data):
        if sold:
            item["status"] = "Sold"
        else:
            item["published"] = False


# The data: two dates and an explicit schedule.


def test_the_real_data_holds_the_owners_two_deadlines_and_no_departure_date():
    seller = SOURCE["seller"]
    assert seller["household_deadline"] == "2026-10-23"
    assert seller["vehicle_deadline"] == "2026-11-09"
    assert "departure_date" not in seller


def test_the_price_schedule_is_the_owners_explicit_dates():
    assert site_builder.sale_schedule(SOURCE["seller"]) == {
        "first_drop": (date(2026, 10, 6), date(2026, 10, 11)),
        "second_drop": (date(2026, 10, 12), date(2026, 10, 15)),
        "clear_floors": (date(2026, 10, 16), date(2026, 10, 19)),
        "giveaway": (date(2026, 10, 20), date(2026, 10, 22)),
    }


def test_the_schedule_is_written_down_not_computed_from_a_deadline():
    seller = copy.deepcopy(SOURCE["seller"])
    seller["household_deadline"] = "2026-10-30"
    seller["vehicle_deadline"] = "2026-12-01"
    assert site_builder.sale_schedule(seller)["first_drop"][0] == date(2026, 10, 6)
    seller["price_schedule"]["first_drop"] = "2026-10-08"
    assert site_builder.sale_schedule(seller)["first_drop"] == (
        date(2026, 10, 8),
        date(2026, 10, 11),
    )


def test_the_seller_tool_gets_the_days_the_windows_open():
    assert site_builder.seller_drops(SOURCE["seller"]) == {
        "first_drop": "2026-10-06",
        "second_drop": "2026-10-12",
        "clear_floors": "2026-10-16",
    }


def test_drops_prints_the_explicit_windows(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: {**SOURCE, "items": []})
    monkeypatch.setattr(private_data, "floors", lambda: {"unused": 1})
    cli.cmd_drops(None)
    output = capsys.readouterr().out
    assert "First drop: Oct 6-11" in output
    assert "Second drop: Oct 12-15" in output
    assert "Clear floors: Oct 16-19" in output
    assert "Giveaway: Oct 20-22" in output


def broken(change):
    seller = copy.deepcopy(SOURCE["seller"])
    change(seller)
    return seller


BAD_SELLERS = {
    "no household deadline": broken(lambda s: s.pop("household_deadline")),
    "no vehicle deadline": broken(lambda s: s.pop("vehicle_deadline")),
    "no schedule": broken(lambda s: s.pop("price_schedule")),
    "a window missing": broken(lambda s: s["price_schedule"].pop("second_drop")),
    "an unknown window": broken(lambda s: s["price_schedule"].update(fire_sale="2026-10-21")),
    "an unquoted date": broken(lambda s: s.update(household_deadline=date(2026, 10, 23))),
    "an unquoted window": broken(
        lambda s: s["price_schedule"].update(first_drop=date(2026, 10, 6))
    ),
    "not an ISO date": broken(lambda s: s.update(vehicle_deadline="11/09/2026")),
    "the compact form": broken(lambda s: s.update(vehicle_deadline="20261109")),
    "a date that does not exist": broken(lambda s: s.update(vehicle_deadline="2026-11-31")),
    "the car before the household": broken(lambda s: s.update(vehicle_deadline="2026-10-23")),
    "windows out of order": broken(lambda s: s["price_schedule"].update(second_drop="2026-10-05")),
    "two windows opening one day": broken(
        lambda s: s["price_schedule"].update(second_drop="2026-10-06")
    ),
    "giveaway on the deadline": broken(lambda s: s["price_schedule"].update(giveaway="2026-10-23")),
    "a schedule that is a list": broken(lambda s: s.update(price_schedule=["2026-10-06"])),
}


@pytest.mark.parametrize("seller", BAD_SELLERS.values(), ids=BAD_SELLERS.keys())
def test_a_missing_or_ill_ordered_schedule_fails_closed(seller):
    with pytest.raises(ValueError, match="seller"):
        site_builder.sale_dates(seller)


def test_the_build_refuses_a_bad_schedule(public_dir):
    data = catalog_inventory()
    data["seller"]["price_schedule"].pop("giveaway")
    with pytest.raises(ValueError, match="price_schedule"):
        site_builder.build_public_site(data)


def test_the_end_build_needs_no_dates(public_dir):
    data = {"seller": {"sale_over": True}, "items": []}
    site_builder.build_public_site(data)
    assert (public_dir / "index.html").exists()


# The page: no sale date on any public surface (FEAT-014). A buyer who sees the day the seller
# must sell by can wait for it and bargain; the dates stay in the data for the seller tool.


@pytest.mark.parametrize("how", ["all for sale", "household hidden", "car sold"])
def test_no_public_page_shows_a_sale_date(public_dir, how):
    data = catalog_inventory()
    if how == "household hidden":
        hide_household(data)
    if how == "car sold":
        next(i for i in data["items"] if i["id"] == CAR)["status"] = "Sold"
    pages = public_pages(public_dir, build(public_dir, data))
    assert {name: dates_on(page) for name, page in pages.items() if dates_on(page)} == {}


def test_moved_dates_still_never_reach_a_public_page(public_dir):
    data = catalog_inventory()
    data["seller"]["household_deadline"] = "2026-10-30"
    data["seller"]["vehicle_deadline"] = "2026-12-04"
    pages = public_pages(public_dir, build(public_dir, data))
    for page in pages.values():
        for shape in ("October 30", "30 de octubre", "December 4", "4 de diciembre", "2026-12-04"):
            assert shape not in unescape(page)


def test_the_hero_strip_says_the_sale_is_on_without_a_date(public_dir):
    pages = build(public_dir, catalog_inventory())
    assert role(pages["en"], "sale-status") == "Available now"
    assert role(pages["es"], "sale-status") == "Disponible ahora"
    assert "deadlineCountdown" not in pages["en"]
    assert "data-countdown-date" not in pages["en"]


def test_the_meta_description_is_the_hero_line_alone(public_dir):
    pages = build(public_dir, catalog_inventory())
    assert description(pages["en"]) == role(pages["en"], "hero-copy")
    assert description(pages["es"]) == role(pages["es"], "hero-copy")


def test_the_hero_no_longer_claims_a_month_the_owner_is_not_leaving_in(public_dir):
    pages = build(public_dir, catalog_inventory())
    assert "relocating in" not in role(pages["en"], "hero-copy")
    assert "Me mudo en" not in role(pages["es"], "hero-copy")


def test_the_hero_names_what_is_still_for_sale(public_dir):
    data = catalog_inventory()
    both = role(build(public_dir, data)["en"], "hero-copy")
    assert "furniture" in both and "SUV" in both
    hide_household(data)
    only_car = build(public_dir, data)
    assert "furniture" not in role(only_car["en"], "hero-copy")
    assert "SUV" in role(only_car["en"], "hero-copy")
    assert "muebles" not in role(only_car["es"], "hero-copy")
    assert "Furniture" not in re.search(r"<title>(.*?)</title>", only_car["en"]).group(1)


def test_the_page_without_the_car_still_says_furniture_and_tech(public_dir):
    data = catalog_inventory()
    data["items"] = household(data)
    data["bundles"] = [b for b in data["bundles"] if CAR not in b["items"]]
    text = role(build(public_dir, data)["en"], "hero-copy")
    assert "furniture and tech" in text and "SUV" not in text


# The car card and the flyer carry no date either.


def test_the_car_card_claims_no_until_date(public_dir):
    pages = build(public_dir, catalog_inventory())
    assert "vehicle-until" not in pages["en"]
    assert "Available until" not in text_of(pages["en"])
    assert "Disponible hasta" not in text_of(pages["es"])


def test_the_flyer_has_no_date_line_and_no_everything_claim(public_dir):
    flyer = build(public_dir, catalog_inventory())["flyer"]
    assert not dates_on(flyer)
    assert " until " not in text_of(flyer) and " by " not in text_of(flyer)
    assert "Everything must go" not in text_of(flyer)


def test_a_flyer_with_only_the_car_has_no_for_sale_line(public_dir):
    data = catalog_inventory()
    hide_household(data)
    text = text_of(build(public_dir, data)["flyer"])
    assert "For sale:" not in text
    assert "My car: 2019 Ford Escape SEL AWD" in text


# The seller tool.


def seller_config(page):
    found = re.search(
        r'<script type="application/json" id="seller-config">(.*?)</script>', page, re.S
    )
    assert found, "the seller page carries its settings as JSON"
    return json.loads(found.group(1))


def test_the_seller_tool_page_carries_the_explicit_drop_days(public_dir):
    config = seller_config(build(public_dir, catalog_inventory())["seller"])
    assert config["drops"] == {
        "first_drop": "2026-10-06",
        "second_drop": "2026-10-12",
        "clear_floors": "2026-10-16",
    }
    # The listings it writes never say when I move (FEAT-014).
    assert "month" not in config


# The close-out: the runbook's snippet hides what is unsold, and the page follows.


def runbook_snippet():
    text = (ROOT / "docs/runbooks/decommission.md").read_text(encoding="utf-8")
    section = text.split("\n## Oct 23: household close-out", 1)[1].split("\n## ", 1)[0]
    return re.search(r"```python\n(.*?)```", section, flags=re.DOTALL).group(1)


def test_the_closeout_snippet_hides_unsold_household_items_and_nothing_else(tmp_path):
    (tmp_path / "data").mkdir()
    source = DATA_DIR / "inventory.yaml"
    (tmp_path / "data" / "inventory.yaml").write_text(source.read_text(encoding="utf-8"))
    result = subprocess.run(
        [sys.executable, "-c", runbook_snippet()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    after = yaml.safe_load((tmp_path / "data" / "inventory.yaml").read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in after["items"]}
    before = {i["id"]: i for i in SOURCE["items"]}
    assert by_id[CAR].get("published", True) is True
    unsold = [
        i
        for i in before.values()
        if i["category"] != "Vehicle"
        and i.get("status", "Available") != "Sold"
        and i.get("published", True)
    ]
    assert unsold, "the real data has household items for sale"
    assert all(by_id[i["id"]]["published"] is False for i in unsold)
    assert f"hidden: {len(unsold)}" in result.stdout
    # Same data otherwise: only `published` was added.
    for item_id, item in before.items():
        assert {k: v for k, v in by_id[item_id].items() if k != "published"} == {
            k: v for k, v in item.items() if k != "published"
        }
    assert after["seller"] == SOURCE["seller"]


def test_after_the_closeout_the_page_offers_only_the_car_and_the_old_share_page_is_gone(
    tmp_path, public_dir
):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "inventory.yaml").write_text(
        (DATA_DIR / "inventory.yaml").read_text(encoding="utf-8")
    )
    subprocess.run(
        [sys.executable, "-c", runbook_snippet()], cwd=tmp_path, check=True, capture_output=True
    )
    data = yaml.safe_load((tmp_path / "data" / "inventory.yaml").read_text(encoding="utf-8"))
    data["seller"].pop("sale_over", None)
    pages = build(public_dir, data)
    assert "furniture" not in role(pages["en"], "hero-copy")
    assert not dates_on(pages["en"])
    assert not (public_dir / "i" / "sofa-sleeper").exists()
    assert (public_dir / "i" / CAR / "index.html").exists()
