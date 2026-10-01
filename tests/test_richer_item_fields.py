"""
Richer item fields (FEAT-007): one asking price, a condition on Facebook's scale, flaws, a
"% off" badge, size badges and a catalog sorted by price.

Real-data tests read the data and the fresh build; synthetic ones feed the builder an inventory
of their own, because the real data has no flaw and no weight to show.
"""

import json
import re

import pytest
import yaml
from test_build_contract import inventory

from leaving_denver import site_builder
from leaving_denver.config import DATA_DIR

ROOT = DATA_DIR.parent
PUBLIC = ROOT / "build" / "public"
SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))
ITEMS = {item["id"]: item for item in SOURCE["items"] if item.get("published", True) is not False}
PAGES = {"en": "index.html", "es": "es/index.html"}
# Written out here, not imported from the builder: the tests fail if the builder's scale or
# thresholds move. The Spanish labels are this project's wording, not Facebook's.
SCALE = {
    "New": "Nuevo",
    "Used - Like New": "Usado - Como nuevo",
    "Used - Good": "Usado - Buen estado",
    "Used - Fair": "Usado - Aceptable",
}
TRUCK = {"en": "Needs truck/SUV", "es": "Necesita camioneta o SUV"}
LIFT = {"en": "2-person lift", "es": "Levantar entre 2 personas"}


def built(page):
    """The page's HTML and its published items by id."""
    html = (PUBLIC / page).read_text(encoding="utf-8")
    found = re.search(r"const INVENTORY = (\{.*?\});\n", html, flags=re.DOTALL)
    return html, {item["id"]: item for item in json.loads(found.group(1))["items"]}


def card(html, item_id):
    found = re.search(
        rf'<button[^>]*data-item="{re.escape(item_id)}".*?</button>', html, flags=re.DOTALL
    )
    assert found, f"no card for {item_id}"
    return found.group(0)


def list_price(item):
    return item["recommended_list_price"]


def lamp(item_id, price=10, **fields):
    """A household item the builder accepts, on top of the shared test inventory."""
    return {
        "category": "Living Room",
        "brand": "Test",
        "id": item_id,
        "title": item_id,
        "recommended_list_price": price,
        "original_price": 20,
        "dimensions": "1 x 1",
        "specs": ["a", "b"],
        **fields,
    }


def sanitized(*items):
    data = inventory()
    data["items"] = list(items)
    data["bundles"] = []
    return site_builder.sanitize_public_inventory(data)


def public_of(item):
    return sanitized(item)["items"][0]


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    """A scratch build root: the builder writes here, never into build/public."""
    from test_build_contract import PHONE

    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


def build_items(public_dir, *items):
    data = inventory()
    data["items"] = list(items)
    data["bundles"] = []
    site_builder.build_public_site(data)
    out = {}
    for locale, page in PAGES.items():
        html = (public_dir / page).read_text(encoding="utf-8")
        found = re.search(r"const INVENTORY = (\{.*?\});\n", html, flags=re.DOTALL)
        out[locale] = (html, {i["id"]: i for i in json.loads(found.group(1))["items"]})
    return out


# --- AC1: one price -------------------------------------------------------------------------


def test_no_item_carries_a_second_asking_price():
    for item_id, item in ITEMS.items():
        assert "current_asking" not in item, f"{item_id} still carries current_asking"
        assert list_price(item) > 0, item_id


def test_the_build_refuses_an_item_with_a_second_price():
    with pytest.raises(RuntimeError, match="current_asking"):
        public_of(lamp("two-prices", current_asking=8))


def test_the_build_refuses_an_item_with_no_price():
    item = lamp("no-price")
    del item["recommended_list_price"]
    with pytest.raises(RuntimeError, match="no-price.*recommended_list_price"):
        public_of(item)


@pytest.mark.parametrize("locale", PAGES)
def test_the_published_price_is_the_one_in_the_data(locale):
    _, items = built(PAGES[locale])
    for item_id, item in items.items():
        expected = 0 if ITEMS[item_id].get("free_with_purchase") else list_price(ITEMS[item_id])
        assert item["price"] == expected, item_id
        assert "current_asking" not in item and "recommended_list_price" not in item


# --- AC2: condition on the scale ------------------------------------------------------------


def test_every_household_condition_is_on_the_scale_and_the_car_keeps_its_wording():
    for item_id, item in ITEMS.items():
        if item["category"] == "Vehicle":
            assert item["condition"] == "Excellent Exterior / Very Good Interior"
        else:
            assert item["condition"] in SCALE, f"{item_id}: {item['condition']!r}"


def test_the_spanish_labels_live_once_in_the_locale_not_on_each_item():
    for code, labels in (("en", {k: k for k in SCALE}), ("es", SCALE)):
        locale = yaml.safe_load((ROOT / "locales" / f"{code}.yaml").read_text(encoding="utf-8"))
        assert locale["conditions"] == labels
    for item_id, item in ITEMS.items():
        if item["category"] != "Vehicle":
            assert "condition" not in item.get("es", {}), f"{item_id} types a Spanish condition"


@pytest.mark.parametrize("locale", PAGES)
def test_the_page_shows_the_scale_label_in_its_language(locale):
    _, items = built(PAGES[locale])
    for item_id, item in items.items():
        source = ITEMS[item_id]
        if source["category"] == "Vehicle":
            continue
        expected = SCALE[source["condition"]] if locale == "es" else source["condition"]
        assert item["condition"] == expected, item_id


def test_the_build_refuses_a_condition_off_the_scale():
    with pytest.raises(RuntimeError, match="off-scale.*Great Condition"):
        public_of(lamp("off-scale", condition="Great Condition"))


def test_the_car_may_use_its_own_scale():
    car = lamp("a-car", category="Vehicle", condition="Excellent Exterior / Very Good Interior")
    assert public_of(car)["condition"] == "Excellent Exterior / Very Good Interior"


# --- AC3: flaws -----------------------------------------------------------------------------


def test_every_flaw_in_the_data_has_a_spanish_line():
    for item_id, item in ITEMS.items():
        flaws = item.get("flaws", [])
        assert len(item.get("es", {}).get("flaws", [])) == len(flaws), item_id


def test_an_item_with_no_known_flaw_publishes_an_empty_list():
    assert public_of(lamp("clean"))["flaws"] == []


def test_flaws_reach_the_published_item_in_each_language(public_dir):
    item = lamp(
        "scuffed",
        flaws=["Scuff on the left arm", "Cushion zipper sticks"],
        es={"flaws": ["Roce en el brazo izquierdo", "El cierre del cojín se atora"]},
    )
    pages = build_items(public_dir, item)
    assert pages["en"][1]["scuffed"]["flaws"] == item["flaws"]
    assert pages["es"][1]["scuffed"]["flaws"] == item["es"]["flaws"]


@pytest.mark.parametrize(
    "spanish",
    [{}, {"flaws": []}, {"flaws": ["Uno", "Dos"]}],
    ids=["no overlay", "empty overlay", "different length"],
)
def test_the_build_refuses_flaws_with_no_matching_spanish(public_dir, spanish):
    with pytest.raises(RuntimeError, match="flawed.*flaws"):
        build_items(public_dir, lamp("flawed", flaws=["A dent"], es=spanish))


def test_the_sheet_template_lists_flaws_as_text_and_hides_the_empty_list(public_dir):
    html, _ = built("index.html")
    script = html[html.index("function openModal") : html.index("function shareItem")]
    assert "bullets(document.getElementById('modalFlaws'), item.flaws || [])" in script
    assert "document.getElementById('modalFlawsBox').hidden = !(item.flaws || []).length" in script
    for element in ('id="modalFlawsBox"', 'id="modalFlaws"'):
        assert element in html
    assert "Known flaws" in html
    assert "Defectos conocidos" in built("es/index.html")[0]


def test_the_seller_copy_lists_the_flaws():
    import subprocess

    script = (
        "import { makeCopy } from './src/leaving_denver/assets/seller.mjs';"
        "const item = { id: 'a-lamp', title: 'Lamp', price: 5, condition: 'Used - Good',"
        " flaws: ['Scuff on the base', 'Shade is yellowed'] };"
        "console.log(JSON.stringify([makeCopy(item, 'fb').description,"
        " makeCopy({ ...item, flaws: [] }, 'fb').description]));"
    )
    out = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    flawed, clean = json.loads(out)
    assert "Known flaws: Scuff on the base; Shade is yellowed." in flawed
    assert "flaws" not in clean.lower()


# --- AC4: % off -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("price", "retail", "expected"),
    [(220, 578, 61), (95, 180, 47), (35, 129, 72), (10, 10, 0), (12, 10, 0), (10, 11, 9)],
)
def test_the_discount_is_the_whole_percent_below_retail(price, retail, expected):
    item = lamp("deal", price=price, original_price=retail)
    assert public_of(item)["discount_pct"] == expected


def test_there_is_no_discount_without_a_retail_figure():
    item = lamp("no-retail")
    del item["original_price"]
    assert public_of(item)["discount_pct"] == 0


def test_a_free_item_has_no_discount():
    free = lamp("freebie", price=20, original_price=40, free_with_purchase=True)
    assert public_of(free)["discount_pct"] == 0


def test_the_car_has_no_discount_against_its_new_price():
    car = lamp("a-car", category="Vehicle", price=11875, original_price=29800)
    car["recommended_list_price"] = 11875
    assert public_of(car)["discount_pct"] == 0


@pytest.mark.parametrize("locale", PAGES)
def test_every_real_item_shows_its_own_discount_on_the_card(locale):
    html, items = built(PAGES[locale])
    word = "off" if locale == "en" else "de descuento"
    shown = 0
    for item_id, item in items.items():
        source = ITEMS[item_id]
        if source["category"] == "Vehicle":
            assert item["discount_pct"] == 0
            continue
        price, retail = list_price(source), source["original_price"]
        expected = (
            0
            if source.get("free_with_purchase") or retail <= price
            else (retail - price) * 100 // retail
        )
        assert item["discount_pct"] == expected, item_id
        badge = re.search(r'data-role="discount-badge"[^>]*>([^<]*)<', card(html, item_id))
        if expected:
            shown += 1
            assert badge and badge.group(1).strip().startswith(f"{expected}%"), item_id
            assert word in badge.group(1)
        else:
            assert not badge, item_id
    assert shown >= 10


def test_a_sold_item_shows_no_discount_badge(public_dir):
    pages = build_items(public_dir, lamp("gone", status="Sold"), lamp("here"))
    html = pages["en"][0]
    assert 'data-role="discount-badge"' not in card(html, "gone")
    assert 'data-role="discount-badge"' in card(html, "here")


# --- AC5: size badges -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("size", "weight", "flags"),
    [
        ([92, 60, 37], None, ["truck"]),
        ([48, 48, 48], None, []),
        ([48.5, 10, 10], None, ["truck"]),
        ([10, 10, 10], 50, []),
        ([10, 10, 10], 51, ["truck"]),
        ([10, 10, 10], 75, ["truck"]),
        ([10, 10, 10], 76, ["truck", "lift"]),
        (None, 80, ["truck", "lift"]),
        (None, None, []),
    ],
)
def test_the_thresholds_are_over_48_in_over_50_lb_and_over_75_lb(size, weight, flags):
    item = lamp("big")
    if size:
        item["size_in"] = size
    if weight:
        item["weight_lb"] = weight
    assert public_of(item)["size_flags"] == flags


@pytest.mark.parametrize(
    "fields",
    [
        {"size_in": [10, 10]},
        {"size_in": [10, 10, 0]},
        {"size_in": [10, -1, 10]},
        {"size_in": ["10", 10, 10]},
        {"size_in": [True, 10, 10]},
        {"size_in": "10 x 10 x 10"},
        {"weight_lb": 0},
        {"weight_lb": "heavy"},
        {"weight_lb": False},
    ],
)
def test_the_build_refuses_a_size_or_weight_that_is_not_positive_numbers(fields):
    with pytest.raises(RuntimeError, match="sized.*(size_in|weight_lb)"):
        public_of(lamp("sized", **fields))


def test_the_published_item_carries_the_flags_and_no_measurements():
    item = public_of(lamp("big", size_in=[60, 10, 10], weight_lb=80))
    assert "size_in" not in item and "weight_lb" not in item


def test_the_labels_come_from_the_locale(public_dir):
    pages = build_items(public_dir, lamp("big", size_in=[60, 10, 10], weight_lb=80))
    for locale in PAGES:
        html, items = pages[locale]
        assert items["big"]["size_badges"] == [TRUCK[locale], LIFT[locale]]
        shown = re.findall(r'data-role="size-badge"[^>]*>([^<]*)<', card(html, "big"))
        assert [s.strip() for s in shown] == [TRUCK[locale], LIFT[locale]]


def test_a_sold_item_shows_no_size_badge(public_dir):
    pages = build_items(public_dir, lamp("gone", size_in=[60, 1, 1], status="Sold"))
    assert 'data-role="size-badge"' not in card(pages["en"][0], "gone")


def test_every_size_in_the_data_is_the_owners_own_number():
    for item_id, item in ITEMS.items():
        written = {float(n) for n in re.findall(r"\d+(?:\.\d+)?", item["dimensions"])}
        for side in item.get("size_in", []):
            assert float(side) in written, f"{item_id}: {side} is not in {item['dimensions']!r}"


def test_a_weight_in_the_data_names_its_source():
    for item_id, item in ITEMS.items():
        if "weight_lb" in item:
            assert item.get("weight_source"), f"{item_id}: a weight with no source"


def test_a_soft_item_that_fits_a_sedan_gets_no_truck_badge():
    for item_id in ("ikea-mattress-topper", "air-mattress-twin-pump"):
        assert "size_in" not in ITEMS[item_id], item_id
        assert public_of({**lamp(item_id), **ITEMS[item_id]})["size_flags"] == []


@pytest.mark.parametrize("locale", PAGES)
def test_the_real_big_items_say_so(locale):
    html, items = built(PAGES[locale])
    for item_id, item in items.items():
        source = ITEMS[item_id]
        big = max(source.get("size_in", [0])) > 48 or source.get("weight_lb", 0) > 50
        assert (TRUCK[locale] in item["size_badges"]) == big, item_id
        if source["category"] != "Vehicle":  # the car has its own section, not a grid card
            assert (TRUCK[locale] in card(html, item_id)) == big, item_id
    assert TRUCK[locale] in items["sofa-sleeper"]["size_badges"]
    assert items["tv-stand-canyon-walnut"]["size_badges"] == []


# --- AC6: sort ------------------------------------------------------------------------------


def test_items_sort_by_ascending_price_with_sold_last_and_ties_in_data_order():
    public = sanitized(
        lamp("c", 30),
        lamp("sold-cheap", 5, status="Sold"),
        lamp("a", 10),
        lamp("b1", 20),
        lamp("b2", 20),
        lamp("sold-dear", 50, status="Sold"),
        lamp("pending", 15, status="Pending"),
    )
    assert [i["id"] for i in public["items"]] == [
        "a",
        "pending",
        "b1",
        "b2",
        "c",
        "sold-cheap",
        "sold-dear",
    ]


def test_a_free_item_sorts_by_its_list_price_and_does_not_lead_the_grid():
    public = sanitized(
        lamp("cheap", 10),
        lamp("freebie", 20, free_with_purchase=True),
        lamp("dear", 30),
    )
    assert [i["id"] for i in public["items"]] == ["cheap", "freebie", "dear"]
    assert public["items"][1]["price"] == 0


@pytest.mark.parametrize("locale", PAGES)
def test_the_real_grid_runs_from_cheap_to_dear_with_sold_last(locale):
    html, items = built(PAGES[locale])
    order = re.findall(r'data-item="([^"]+)"', html)
    keys = [(ITEMS[i].get("status") == "Sold", list_price(ITEMS[i])) for i in order]
    assert keys == sorted(keys)
    assert len(order) == len(items) - 1  # the car has its own section
