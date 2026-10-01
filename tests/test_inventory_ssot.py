"""
Unit tests for Single Source of Truth (SSOT) inventory data integrity.
"""

import re
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
INVENTORY_YAML = BASE_DIR / "data" / "inventory.yaml"
POSTER = BASE_DIR / "src" / "leaving_denver" / "templates" / "poster_assistant.html"


@pytest.fixture
def inventory():
    assert INVENTORY_YAML.exists(), f"Missing SSOT file: {INVENTORY_YAML}"
    with open(INVENTORY_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Inventory YAML must parse into a dict"
    return data


def test_seller_metadata(inventory):
    seller = inventory.get("seller", {})
    assert "location" in seller
    assert "email" in seller
    assert "CO 80111" in seller["location"]
    assert seller["departure_date"] == "2026-11-09"
    assert set(seller["payment_methods"]) == {"household", "vehicle"}
    assert "Venmo" in " ".join(seller["payment_methods"]["household"])
    assert "Venmo" not in " ".join(seller["payment_methods"]["vehicle"])


def test_the_car_takes_only_payments_that_cannot_be_clawed_back(inventory):
    """Cashier's check or wire, nothing else (owner, 2026-09-30; docs/runbooks/vehicle-sale.md)."""
    assert inventory["seller"]["payment_methods"]["vehicle"] == [
        "Cashier's check issued at the buyer's bank",
        "Wire transfer",
    ]
    for code in ("en", "es"):
        labels = yaml.safe_load((BASE_DIR / "locales" / f"{code}.yaml").read_text(encoding="utf-8"))
        for method in inventory["seller"]["payment_methods"]["vehicle"]:
            assert method in labels["payment_methods"], f"{code}: no label for {method}"
    car = next(i for i in inventory["items"] if i["category"] == "Vehicle")
    copy = " ".join(
        [car["pickup_note"], car["es"]["pickup_note"]]
        + re.findall(r"VEHICLE_PAYMENT_ES = '([^']+)'", POSTER.read_text(encoding="utf-8"))
    ).lower()
    for banned in ("cash", "efectivo", "venmo", "zelle"):
        assert not re.search(rf"\b{banned}\b", copy), f"the car's payment copy mentions {banned}"
    assert "wire" in car["pickup_note"].lower()
    assert "transferencia" in car["es"]["pickup_note"].lower()


def test_items_integrity(inventory):
    items = inventory.get("items", [])
    assert len(items) >= 14, "Expected at least 14 items including vehicle"

    item_ids = set()
    for item in items:
        # ID uniqueness
        item_id = item.get("id")
        assert item_id, "Item missing ID"
        assert item_id not in item_ids, f"Duplicate item ID: {item_id}"
        item_ids.add(item_id)

        # Pricing integrity
        orig_price = item.get("original_price", 0)
        list_price = item.get("recommended_list_price", 0)

        assert orig_price > 0, f"Invalid original price for {item_id}"
        assert list_price > 0, f"Invalid list price for {item_id}"
        assert "firm_floor_price" not in item, (
            f"Reserve floor must live in data/private.sops.yaml, not {item_id}"
        )

        # Specs and dimensions
        assert len(item.get("specs", [])) >= 2, f"Item {item_id} needs at least 2 specs"
        assert item.get("dimensions"), f"Item {item_id} missing dimensions"


def test_vehicle_specifics(inventory):
    vehicle = next(
        (i for i in inventory.get("items", []) if i.get("id") == "2019-ford-escape-sel-awd"), None
    )
    assert vehicle is not None, "2019 Ford Escape SEL AWD not found in items"
    assert vehicle.get("category") == "Vehicle"
    assert vehicle.get("recommended_list_price") == 11875

    # Ensure zero open recall is noted
    specs_text = " ".join(vehicle.get("specs", []))
    assert "open recall" in specs_text.lower() or "recall" in specs_text.lower()


def test_bundles_integrity(inventory):
    prices = {
        i["id"]: 0 if i.get("free_with_purchase") else i["recommended_list_price"]
        for i in inventory["items"]
    }
    for b in inventory.get("bundles", []):
        assert b.get("name"), "Bundle missing name"
        # Totals and savings are computed at build time; typed copies drift (#6).
        typed = {"individual_total", "savings"} & b.keys()
        assert not typed, f"{b['id']} types derived figures {sorted(typed)}"
        assert all(i in prices for i in b["items"]), f"{b['id']} names an unknown item"
        total = sum(prices[i] for i in b["items"])
        assert 0 < b["bundle_price"] < total, f"{b['id']} has no positive discount"


def test_seller_phone_not_in_public_inventory(inventory):
    assert "phone" not in inventory.get("seller", {}), (
        "Phone must come from SELLER_PHONE or the sops file"
    )


def test_private_floors_consistent(inventory):
    from leaving_denver.private_data import floors

    reserve = floors()
    if not reserve:
        pytest.skip("data/private.sops.yaml not decryptable here")
    for item in inventory.get("items", []):
        floor = reserve.get(item["id"])
        assert floor, f"Missing reserve floor for {item['id']}"
        assert 0 < floor <= item["recommended_list_price"], (
            f"Floor exceeds list price in {item['id']}"
        )


# Claims the seller cannot back: no 100k service receipt exists, remote start and
# highway-only miles are not in the data, the departure date is 9 November, and
# the CSP 21N12 coverage ended at 84k miles. "Garage-kept" was on this list until the
# owner confirmed it (#48, 2026-09-28).
UNBACKED_CLAIMS = re.compile(
    r"100k[- ](mile )?(milestone )?(major )?s(er)?v|highway miles|highway-commuter|"
    r"remote start|fully serviced|great mechanical|in 3 weeks|within 2 weeks|"
    r"everything must go|everything was bought new|one single|21N12|"
    r"ready for immediate transfer|new, unused certificate is handed over|"
    r"servicio (de )?100k|millas de autopista|arranque remoto|mecánicamente perfecto|"
    r"en 3 semanas|dentro de 2 semanas|todo debe irse|todo se compró nuevo|"
    r"listo para transferencia inmediata",
    re.IGNORECASE,
)
CLAIM_SOURCES = [
    INVENTORY_YAML,
    BASE_DIR / "src" / "leaving_denver" / "templates" / "index.html",
    BASE_DIR / "src" / "leaving_denver" / "templates" / "poster_assistant.html",
    BASE_DIR / "build" / "public" / "index.html",
    BASE_DIR / "build" / "public" / "es" / "index.html",
]


def test_claim_guard_recognizes_spanish():
    assert UNBACKED_CLAIMS.search("Incluye arranque remoto")


@pytest.mark.parametrize("path", CLAIM_SOURCES, ids=lambda p: p.name)
def test_no_unbacked_vehicle_claims(path):
    assert path.exists(), f"missing {path}"
    hits = UNBACKED_CLAIMS.findall(path.read_text(encoding="utf-8"))
    assert not hits, f"{path.name} states a claim the seller cannot back: {hits}"


# Owner correction, 2026-09-28: first floor, one flight of stairs, no elevator; the car was
# bought used, so "everything was bought new" is false (#48).
# Strip natural English and Spanish denials, then reject any remaining elevator claim.
ELEVATOR_DENIALS = re.compile(
    r"\b(?:no elevators?(?: in the building)?|"
    r"(?:do not|don't|does not|doesn't) have (?:an? )?elevators?|"
    r"sin (?:ascensor|elevador)(?:es)?|"
    r"no hay (?:ascensor|elevador)(?:es)?(?: disponible(?:s)?)?|"
    r"no cuenta con (?:un |una )?(?:ascensor|elevador)(?:es)?)\b",
    re.I,
)
WRONG_PICKUP_FACTS = re.compile(
    r"elevators?|(?:ascensor|elevador)(?:es)?|ground floor|second floor|segundo piso|"
    r"everything was bought new",
    re.I,
)


def wrong_pickup_facts(text):
    return WRONG_PICKUP_FACTS.findall(ELEVATOR_DENIALS.sub("", text))


@pytest.mark.parametrize(
    "claim",
    [
        "con ascensor",
        "con un ascensor",
        "ascensor disponible",
        "con elevador",
        "There is an elevator in the building",
    ],
)
def test_pickup_guard_rejects_spanish_elevator_claims(claim):
    assert wrong_pickup_facts(claim)


@pytest.mark.parametrize(
    "fact",
    [
        "sin ascensor",
        "sin elevador",
        "sin ascensores",
        "no hay ascensor",
        "no hay ascensor disponible",
        "no cuenta con ascensor",
        "We do not have an elevator",
        "We don't have an elevator",
        "No elevators in the building",
    ],
)
def test_pickup_guard_allows_spanish_elevator_denials(fact):
    assert not wrong_pickup_facts(fact)


def test_pickup_floor_matches_owner(inventory):
    seller = inventory["seller"]
    assert seller["pickup_summary"] == "First floor, one flight of stairs, no elevator"
    assert "First floor, one flight of stairs, no elevator." in seller["pickup"]
    assert seller["es"]["pickup_summary"] == "Primer piso, un tramo de escaleras, sin ascensor"
    assert "Primer piso, un tramo de escaleras, sin ascensor." in seller["es"]["pickup"]


@pytest.mark.parametrize("path", CLAIM_SOURCES, ids=lambda p: p.name)
def test_no_stale_or_unbacked_pickup_facts(path):
    hits = wrong_pickup_facts(path.read_text(encoding="utf-8"))
    assert not hits, f"{path.name} states a wrong pickup fact: {hits}"
