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


def countdown(page):
    found = re.search(
        r'<span id="deadlineCountdown" data-countdown-date="([^"]+)">([^<]+)</span>', page
    )
    assert found
    return found.group(1), " ".join(unescape(found.group(2)).split())


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


# The page: the countdown follows what is still for sale.


def test_while_household_items_are_for_sale_the_countdown_targets_their_deadline(public_dir):
    pages = build(public_dir, catalog_inventory())
    assert countdown(pages["en"]) == ("2026-10-23", "Furniture & tech until October 23")
    assert countdown(pages["es"]) == (
        "2026-10-23",
        "Muebles y tecnología hasta el 23 de octubre",
    )


def test_a_pending_household_item_still_counts_as_for_sale(public_dir):
    data = catalog_inventory()
    hide_household(data, sold=True)
    household(data)[0]["status"] = "Pending"
    assert countdown(build(public_dir, data)["en"])[0] == "2026-10-23"


@pytest.mark.parametrize("how", ["hidden", "sold"])
def test_with_no_household_item_left_the_countdown_targets_the_car(public_dir, how):
    data = catalog_inventory()
    hide_household(data, sold=how == "sold")
    pages = build(public_dir, data)
    assert countdown(pages["en"]) == ("2026-11-09", "Car available until November 9")
    assert countdown(pages["es"]) == ("2026-11-09", "Auto disponible hasta el 9 de noviembre")


def test_a_sold_car_does_not_move_the_household_deadline(public_dir):
    data = catalog_inventory()
    next(i for i in data["items"] if i["id"] == CAR)["status"] = "Sold"
    assert countdown(build(public_dir, data)["en"])[0] == "2026-10-23"


def test_the_meta_description_month_follows_the_same_rule(public_dir):
    data = catalog_inventory()
    pages = build(public_dir, data)
    assert "October 23" in description(pages["en"])
    assert "23 de octubre" in description(pages["es"])
    hide_household(data)
    pages = build(public_dir, data)
    assert "November 9" in description(pages["en"])
    assert "9 de noviembre" in description(pages["es"])
    assert "October" not in description(pages["en"])


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


# The car card says how long the car is available.


def test_the_car_card_says_it_is_available_until_the_car_deadline(public_dir):
    pages = build(public_dir, catalog_inventory())
    assert role(pages["en"], "vehicle-until") == "Available until November 9"
    assert role(pages["es"], "vehicle-until") == "Disponible hasta el 9 de noviembre"


@pytest.mark.parametrize("status", ["Pending", "Sold"])
def test_a_car_that_is_not_available_does_not_claim_to_be(public_dir, status):
    data = catalog_inventory()
    next(i for i in data["items"] if i["id"] == CAR)["status"] = status
    assert "vehicle-until" not in build(public_dir, data)["en"]


# The flyer.


def flyer_deadline(page):
    return (
        re.search(r'<p class="mt-3 text-2xl font-semibold"[^>]*>(.*?)</p>', page).group(1).strip()
    )


def test_the_flyer_states_both_dates_and_drops_the_everything_claim(public_dir):
    flyer = build(public_dir, catalog_inventory())["flyer"]
    assert flyer_deadline(flyer) == "Furniture &amp; tech by October 23 · car until November 9"
    assert "Everything must go" not in text_of(flyer)


def test_a_sold_car_leaves_only_the_household_date(public_dir):
    data = catalog_inventory()
    next(i for i in data["items"] if i["id"] == CAR)["status"] = "Sold"
    flyer = build(public_dir, data)["flyer"]
    assert flyer_deadline(flyer) == "Furniture &amp; tech by October 23"
    assert "November" not in text_of(flyer)


def test_with_no_household_item_left_the_flyer_names_only_the_car(public_dir):
    data = catalog_inventory()
    hide_household(data)
    assert flyer_deadline(build(public_dir, data)["flyer"]) == "Car until November 9"


def test_the_flyer_dates_come_from_the_data(public_dir):
    data = catalog_inventory()
    data["seller"]["household_deadline"] = "2026-10-30"
    data["seller"]["vehicle_deadline"] = "2026-12-04"
    flyer = build(public_dir, data)["flyer"]
    assert flyer_deadline(flyer) == "Furniture &amp; tech by October 30 · car until December 4"


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
    # Listings say when the owner moves, and that is the car's month: the owner leaves in November.
    assert config["month"]["en"] == "November"


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


def test_after_the_closeout_the_page_targets_the_car_and_the_old_share_page_is_gone(
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
    assert countdown(pages["en"])[0] == "2026-11-09"
    assert not (public_dir / "i" / "sofa-sleeper").exists()
    assert (public_dir / "i" / CAR / "index.html").exists()
