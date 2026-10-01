"""
The item sheet shows the whole item: every spec, its condition, dimensions and colour, and what
is included (FEAT-011, superseding BUG-001's four-fact cap). The card stays a four-line teaser,
so "View specs" shows more than the card. The footer holds only the credit and the build.
"""

import json
import re

import pytest
import yaml

from leaving_denver.config import DATA_DIR

ROOT = DATA_DIR.parent
PUBLIC = ROOT / "build" / "public"
SOURCE = {
    item["id"]: item
    for item in yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))["items"]
}
PAGES = {"en": "index.html", "es": "es/index.html"}


def inventory(page):
    html = (PUBLIC / page).read_text(encoding="utf-8")
    found = re.search(r"const INVENTORY = (\{.*?\});\n", html, flags=re.DOTALL)
    return html, {item["id"]: item for item in json.loads(found.group(1))["items"]}


@pytest.mark.parametrize("locale", PAGES)
def test_every_item_publishes_all_its_specs_and_what_is_included(locale):
    _, items = inventory(PAGES[locale])
    for item_id, item in items.items():
        source = SOURCE[item_id]
        copy = source.get(locale, {}) if locale != "en" else source
        assert item["specs"] == copy.get("specs", source["specs"]), item_id
        assert item["included"] == copy.get("included", source.get("included", [])), item_id


def test_the_spanish_sheet_has_spanish_details():
    # The summary line shows these three; with no overlay the Spanish sheet shows English.
    _, items = inventory(PAGES["es"])
    for item_id, item in items.items():
        overlay = SOURCE[item_id].get("es", {})
        for field in ("condition", "dimensions", "color"):
            if SOURCE[item_id].get(field):
                assert overlay.get(field), f"{item_id}: no Spanish {field}"
                assert item[field] == overlay[field], f"{item_id}: {field}"


def test_the_car_has_more_specs_than_its_card_shows():
    html, items = inventory("index.html")
    car = items["2019-ford-escape-sel-awd"]
    assert len(car["specs"]) > 4
    assert len(re.findall(r"data-vehicle-claim>", html)) == 4


@pytest.mark.parametrize("locale", PAGES)
def test_the_sheet_renders_every_spec_the_details_and_the_included_list(locale):
    html, _ = inventory(PAGES[locale])
    script = html[html.index("function openModal") : html.index("function shareItem")]
    assert "bullets(document.getElementById('itemFacts'), item.specs || [])" in script
    assert "item.condition, item.dimensions, item.color" in script
    assert "bullets(document.getElementById('modalIncluded'), item.included || [])" in script
    # Data goes in as text, never as markup.
    assert "innerHTML = `" not in script.split("modalThumbStrip")[1]
    bullets = script[script.index("const bullets") : script.index("bullets(document")]
    assert "innerHTML" not in bullets
    assert "text.textContent = line" in bullets
    for element in ('id="itemFacts"', 'id="modalSummary"', 'id="modalIncluded"'):
        assert element in html


@pytest.mark.parametrize(("locale", "heading"), [("en", "What's included"), ("es", "Qué incluye")])
def test_the_included_list_has_a_heading(locale, heading):
    html, _ = inventory(PAGES[locale])
    assert heading in html


@pytest.mark.parametrize("locale", PAGES)
def test_the_footer_holds_only_the_credit_and_the_build(locale):
    html, _ = inventory(PAGES[locale])
    footer = re.search(r"<footer.*?</footer>", html, flags=re.DOTALL).group(0)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", footer)).strip()
    assert "Relocation Sale" not in text and "Venta por mudanza" not in text
    assert "CO 80111" not in text
    assert text.startswith(("Built by", "Creado por"))
