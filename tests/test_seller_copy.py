"""
The copy /seller/ generates (FEAT-009 PR 1): Spanish, the car, flaws, limits, links and the
scam replies. seller.mjs runs under Node on the payload the build ships, and the payment
wording is checked against the data and locales it must come from.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml
from sealed_helpers import json_block

from leaving_denver import site_builder

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("fb", "fb-es", "cl", "cl-es", "offerup", "nextdoor")
SPANISH = ("fb-es", "cl-es")
SPANISH_ONLY = re.compile(r"\b(nosotros|nuestr[oa]s?|podemos)\b", re.IGNORECASE)
PHONE = re.compile(r"\+?\d{10,}|\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}")
HYPE = re.compile(
    r"great (buy|deal)|amazing|must go|steal|won't last|priced to sell|1\.15|plus tax|"
    r"retail|bought (it )?new|compra increíble|oferta",
    re.IGNORECASE,
)
CASH = re.compile(r"\b(cash|venmo|zelle|efectivo)\b", re.IGNORECASE)


def inventory():
    return yaml.safe_load((ROOT / "data/inventory.yaml").read_text(encoding="utf-8"))


def locale(code):
    return yaml.safe_load((ROOT / "locales" / f"{code}.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """The /seller/ page and payload from a build of the real data into a temp dir."""
    public = tmp_path_factory.mktemp("public")
    patch = pytest.MonkeyPatch()
    patch.setenv("SELLER_PHONE", "+15555550100")
    patch.setattr(site_builder, "DIST_DIR", public)
    patch.setattr(site_builder, "PUBLIC_INDEX_HTML", public / "index.html")
    patch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", public / "robots.txt")
    patch.setattr(site_builder, "PUBLIC_HEADERS", public / "_headers")
    site_builder.build_public_site(site_builder.load_inventory_yaml())
    patch.undo()
    html = (public / "seller/index.html").read_text(encoding="utf-8")
    items = json_block(html, "seller-items")
    config = json_block(html, "seller-config")
    return {"html": html, "items": items, "config": config}


def run_copy(items, config):
    """makeCopy for every item on every channel, as {item id: {channel: copy}}."""
    script = """
import { makeCopy } from './src/leaving_denver/assets/seller.mjs';
let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const { items, config, channels } = JSON.parse(raw);
const out = {};
for (const item of items) {
  out[item.id] = {};
  for (const channel of channels) out[item.id][channel] = makeCopy(item, channel, config);
}
console.log(JSON.stringify(out));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        input=json.dumps({"items": items, "config": config, "channels": CHANNELS}),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def copies(built):
    return run_copy(built["items"], built["config"])


def car_of(built):
    return next(i for i in built["items"] if i["category"] == "Vehicle")


def household_of(built):
    return next(i for i in built["items"] if i["id"] == "sofa-sleeper")


def descriptions(copies):
    return [
        (item_id, channel, copy["description"])
        for item_id, by_channel in copies.items()
        for channel, copy in by_channel.items()
    ]


# --- AC1: Spanish ---------------------------------------------------------------------------


@pytest.mark.parametrize("channel", SPANISH)
def test_the_spanish_channels_write_the_listing_from_the_spanish_overlay(built, copies, channel):
    for item in built["items"]:
        copy = copies[item["id"]][channel]
        es = item["es"]
        assert es["short_title"] in copy["title"], item["id"]
        assert es["condition"] in copy["description"], item["id"]
        for spec in es["specs"]:
            assert f"- {spec}" in copy["description"], item["id"]
        assert es["pickup"] in copy["description"], item["id"]
        assert "Asking price" not in copy["description"]
        assert copy["description"].count("Me mudo y vendo") == 1
        # An item's own "a partir del 15 de noviembre" pickup date is not the car deadline.
        assert "noviembre" not in re.sub(r"a partir del \d+ de noviembre", "", copy["description"])


def test_the_spanish_overlay_is_complete_for_every_listable_item(built):
    for item in built["items"]:
        for field in ("title", "short_title", "condition", "specs", "pickup", "payment"):
            assert item["es"].get(field), f"{item['id']}: no Spanish {field}"
        assert item["es"]["condition"] != item["condition"] or item["category"] == "Vehicle"
        assert len(item["es"]["flaws"]) == len(item["flaws"])


def test_the_english_channels_stay_english(built, copies):
    sofa = household_of(built)
    for channel in ("fb", "cl", "offerup", "nextdoor"):
        description = copies[sofa["id"]][channel]["description"]
        assert sofa["short_title"] in description or sofa["title"] in description
        assert sofa["es"]["condition"] not in description


# --- AC2, AC3: payment is data, and the car is paid only by bank ---------------------------


def test_the_cars_copy_names_the_bank_payments_from_the_data_on_every_channel(built, copies):
    data = inventory()
    car = car_of(built)
    for code, channels in (("en", ("fb", "cl", "offerup", "nextdoor")), ("es", SPANISH)):
        labels = locale(code)["payment_methods"]
        joined = f" {locale(code)['or']} ".join(
            labels[m] for m in data["seller"]["payment_methods"]["vehicle"]
        )
        for channel in channels:
            description = copies[car["id"]][channel]["description"]
            assert f"{joined}." in description, f"{channel}: {description}"
            assert not CASH.search(description), f"{channel} offers a clawback payment"


def test_household_copy_takes_the_catalogs_payment_wording(built, copies):
    data = inventory()
    sofa = household_of(built)
    for code, channels in (("en", ("fb", "cl", "offerup", "nextdoor")), ("es", SPANISH)):
        t = locale(code)
        methods = ", ".join(
            t["payment_methods"][m] for m in data["seller"]["payment_methods"]["household"]
        )
        for channel in channels:
            description = copies[sofa["id"]][channel]["description"]
            assert f"{methods} {t['in_person']}." in description
    assert "Cashier" not in copies[sofa["id"]]["fb"]["description"]


def test_the_page_logic_hardcodes_no_payment_wording():
    for name in ("assets/seller.mjs", "templates/seller.html"):
        source = (ROOT / "src/leaving_denver" / name).read_text(encoding="utf-8")
        found = re.findall(r"venmo|zelle|cashier|cheque|efectivo|wire transfer", source, re.I)
        assert not found, f"{name} spells out payment wording: {found}"


def test_the_car_copy_is_vehicle_copy_not_furniture_copy(built, copies):
    car = car_of(built)
    for channel in ("fb", "cl", "offerup"):
        copy = copies[car["id"]][channel]
        assert "103,500" in copy["title"], copy["title"]
        description = copy["description"]
        assert "Mileage: 103,500 miles." in description
        assert f"Title: {car['title_status']}." in description
        assert f"VIN: {car['vin']}." in description
        assert "Dimensions" not in description
        assert "bundle" not in description.lower()
    spanish = copies[car["id"]]["fb-es"]["description"]
    assert "Millaje: 103,500 millas." in spanish
    assert f"Título: {car['es']['title_status']}." in spanish


# --- AC4: flaws ------------------------------------------------------------------------------

LAMP = {
    "id": "a-lamp",
    "title": "Desk lamp",
    "short_title": "Desk lamp",
    "price": 5,
    "condition": "Used - Good",
    "specs": ["LED, dimmable"],
    "included": ["Bulb"],
    "flaws": ["Scuff on the base"],
    "pickup": "Pickup in DTC.",
    "payment": "Cash, Venmo, Zelle in person",
    "es": {
        "title": "Lámpara",
        "short_title": "Lámpara",
        "condition": "Usado - Buen estado",
        "specs": ["LED regulable"],
        "included": ["Foco"],
        "flaws": ["Raspón en la base"],
        "pickup": "Recogida en DTC.",
        "payment": "Efectivo, Venmo, Zelle en persona",
    },
}


def test_flaws_come_after_every_positive_and_follow_the_language():
    copies = run_copy([LAMP], {})["a-lamp"]
    for channel, flaw, positives in (
        ("fb", "Known flaws: Scuff on the base.", ["Used - Good", "- LED, dimmable", "Bulb"]),
        ("fb-es", "Defectos conocidos: Raspón en la base.", ["Usado - Buen estado", "Foco"]),
    ):
        description = copies[channel]["description"]
        assert flaw in description
        for positive in positives:
            assert description.index(positive) < description.index(flaw), (channel, positive)


def test_no_flaws_line_without_flaws():
    lamp = {**LAMP, "flaws": [], "es": {**LAMP["es"], "flaws": []}}
    copies = run_copy([lamp], {})["a-lamp"]
    for channel in ("fb", "fb-es"):
        assert not re.search(r"flaws|defectos", copies[channel]["description"], re.IGNORECASE)


# --- AC5: voice and content --------------------------------------------------------------------


def test_the_copy_is_singular_plain_and_phone_free(built, copies):
    for item_id, channel, description in descriptions(copies):
        where = f"{item_id}/{channel}"
        assert not re.search(r"\b(we|our|we'll)\b", description, re.IGNORECASE), where
        assert not SPANISH_ONLY.search(description), where
        assert not HYPE.search(description), where
        assert not PHONE.search(description), where
        assert not re.search(r"text(/sms)?\s+\S*\d", description, re.IGNORECASE), where
        prices = set(re.findall(r"\$[\d,]+", description))
        price = next(i["price"] for i in built["items"] if i["id"] == item_id)
        assert prices == {f"${price:,}"}, f"{where}: {prices}"


def test_every_listing_says_no_holds_and_no_deposits(copies):
    for item_id, channel, description in descriptions(copies):
        marker = "No aparto" if channel in SPANISH else "No holds"
        assert marker in description, f"{item_id}/{channel}"


def test_craigslist_replies_through_its_relay_and_chat_channels_through_chat(copies):
    sofa = copies["sofa-sleeper"]
    assert "Craigslist" in sofa["cl"]["description"]
    assert "Craigslist" in sofa["cl-es"]["description"]
    for channel in ("fb", "offerup", "nextdoor", "fb-es"):
        assert "Craigslist" not in sofa[channel]["description"]


# --- AC6: limits ---------------------------------------------------------------------------------


def test_every_listing_fits_its_platform_without_cutting_anything(copies):
    limits = {"fb": 100, "fb-es": 100, "cl": 70, "cl-es": 70, "offerup": 60, "nextdoor": 100}
    for item_id, by_channel in copies.items():
        for channel, copy in by_channel.items():
            where = f"{item_id}/{channel}"
            assert copy["limits"]["title"] == limits[channel], where
            assert copy["fits"]["title"], f"{where}: {copy['title']!r} was cut"
            assert len(copy["title"]) <= limits[channel], where
            assert copy["fits"]["description"], where
    for channel in ("fb", "fb-es"):
        assert copies["sofa-sleeper"][channel]["limits"]["description"] == 5000


def test_an_overlong_listing_is_flagged_not_silently_cut():
    long = {**LAMP, "short_title": "L" * 150, "specs": ["x" * 5200]}
    copy = run_copy([long], {})["a-lamp"]["fb"]
    assert len(copy["title"]) == 100
    assert copy["fits"] == {"title": False, "description": False}
    assert len(copy["description"]) > 5200


# --- AC7: links ----------------------------------------------------------------------------------


def test_each_channel_gets_its_own_attribution_and_the_link_stays_out_of_the_listing(built, copies):
    sources = {
        "fb": "facebook",
        "fb-es": "facebook",
        "cl": "craigslist",
        "cl-es": "craigslist",
        "offerup": "offerup",
        "nextdoor": "nextdoor",
    }
    origin = built["config"]["origin"]
    for item_id, by_channel in copies.items():
        for channel, copy in by_channel.items():
            prefix = "/es" if channel in SPANISH else ""
            assert copy["link"] == (
                f"{origin}{prefix}/i/{item_id}/?utm_source={sources[channel]}&utm_campaign=moving-sale"
            )
            assert "http" not in copy["description"], f"{item_id}/{channel} carries a link"
            assert "utm_" not in copy["description"]


def test_the_origin_the_page_links_to_is_the_builders(built):
    assert built["config"]["origin"] == site_builder.site_url()


# --- Platform shortcuts and the rest of the assistant's helpers -----------------------------------


def test_each_channel_opens_its_listing_creator_and_the_car_the_vehicle_one(built, copies):
    sofa, car = household_of(built)["id"], car_of(built)["id"]
    assert copies[sofa]["fb"]["create"] == "https://www.facebook.com/marketplace/create/item"
    assert copies[car]["fb"]["create"] == "https://www.facebook.com/marketplace/create/vehicle"
    assert copies[car]["cl"]["create"] == "https://post.craigslist.org/c/den/cto"
    assert copies[sofa]["cl"]["create"] == "https://post.craigslist.org/c/den"
    assert copies[sofa]["offerup"]["create"] == "https://offerup.com/post"
    assert copies[sofa]["nextdoor"]["create"] == "https://nextdoor.com/for_sale_and_free/"


def test_the_copy_carries_the_price_digits_tags_and_the_full_listing(built, copies):
    sofa = household_of(built)
    copy = copies[sofa["id"]]["fb"]
    assert copy["price"] == str(sofa["price"])
    assert copy["tags"] == ", ".join(sofa["tags"]) and copy["tags"]
    assert (
        copy["full"]
        == f"TITLE: {copy['title']}\nPRICE: ${sofa['price']:,}\n\n{copy['description']}"
    )


# --- AC8: scam replies -----------------------------------------------------------------------------

REPLY_IDS = [
    "verification-code",
    "fake-payment-email",
    "overpayment",
    "courier",
    "report-link",
    "deposit",
]


def test_six_scam_replies_each_have_english_and_spanish_with_copy_buttons(built):
    html = built["html"]
    assert re.findall(r'data-reply="([^"]+)"', html) == REPLY_IDS
    for reply_id in REPLY_IDS:
        for lang in ("en", "es"):
            box = f"reply-{reply_id}-{lang}"
            assert re.search(rf'<textarea[^>]*id="{box}"[^>]*readonly', html), box
            assert f'data-copy="{box}"' in html, box


def test_the_replies_come_from_the_data_with_the_car_payment_filled_in(built):
    raw = yaml.safe_load((ROOT / "data/seller-replies.yaml").read_text(encoding="utf-8"))
    assert [r["id"] for r in raw["replies"]] == REPLY_IDS
    html = built["html"]
    data = inventory()
    for code in ("en", "es"):
        t = locale(code)
        bank = f" {t['or']} ".join(
            t["payment_methods"][m] for m in data["seller"]["payment_methods"]["vehicle"]
        )
        filled = [r[code]["text"].replace("{vehicle_payment}", bank) for r in raw["replies"]]
        for text in filled:
            assert "{" not in text
        # Apostrophes are HTML-escaped inside the textarea, so compare unescaped.
        import html as htmllib

        page = htmllib.unescape(html)
        for text in filled:
            assert text in page
    assert "{vehicle_payment}" not in html


def test_the_replies_are_singular_plain_and_phone_free():
    raw = yaml.safe_load((ROOT / "data/seller-replies.yaml").read_text(encoding="utf-8"))
    for reply in raw["replies"]:
        for code in ("en", "es"):
            text = reply[code]["text"]
            assert not re.search(r"\b(we|our|we'll)\b", text, re.IGNORECASE), reply["id"]
            assert not SPANISH_ONLY.search(text), reply["id"]
            assert not PHONE.search(text), reply["id"]


def test_the_build_refuses_a_reply_with_no_spanish(tmp_path, monkeypatch):
    raw = yaml.safe_load((ROOT / "data/seller-replies.yaml").read_text(encoding="utf-8"))
    del raw["replies"][2]["es"]
    broken = tmp_path / "replies.yaml"
    broken.write_text(yaml.safe_dump(raw), encoding="utf-8")
    monkeypatch.setattr(site_builder, "SELLER_REPLIES_YAML", broken)
    with pytest.raises(RuntimeError, match="overpayment"):
        site_builder.seller_replies({"en": "x", "es": "y"})


def test_the_build_refuses_a_reply_with_an_unfilled_placeholder(tmp_path, monkeypatch):
    raw = yaml.safe_load((ROOT / "data/seller-replies.yaml").read_text(encoding="utf-8"))
    raw["replies"][0]["en"]["text"] = "Pay {balance} first."
    broken = tmp_path / "replies.yaml"
    broken.write_text(yaml.safe_dump(raw), encoding="utf-8")
    monkeypatch.setattr(site_builder, "SELLER_REPLIES_YAML", broken)
    with pytest.raises(RuntimeError, match="verification-code"):
        site_builder.seller_replies({"en": "x", "es": "y"})
