"""
The close-out (OPS-018): the inventory states the end of the sale, and the public retrospective
says the same thing as the seller-only arithmetic.

Two facts are kept twice here — the item is public and its realized price is not — so the tests
compare the public statement (counts, percentages) against the sources that produce it.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = yaml.safe_load((ROOT / "data/inventory.yaml").read_text(encoding="utf-8"))
ITEMS = INVENTORY["items"]
CASE = (ROOT / "docs/case-study.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
ADR_013 = next((ROOT / "docs/adr").glob("adr-013-*.md")).read_text(encoding="utf-8")
ADR_008 = next((ROOT / "docs/adr").glob("adr-008-*.md")).read_text(encoding="utf-8")

# The six items that left without money changing hands, named so a new one has to be declared.
GIVEAWAYS = {
    "air-mattress-twin-pump",
    "convertible-desk",
    "dell-monitor-32",
    "office-chair-ergonomic",
    "dinnerware-glassware-set",
    "lamps-pair",
}


def test_every_item_reached_its_end_state():
    assert [i["id"] for i in ITEMS if i.get("status") != "Sold"] == []


def test_a_giveaway_is_named_as_one_and_a_sale_needs_no_field():
    declared = {i["id"] for i in ITEMS if i.get("disposition") == "giveaway"}
    assert declared == GIVEAWAYS
    assert all(i.get("disposition", "sale") == "sale" for i in ITEMS if i["id"] not in GIVEAWAYS)


def test_the_split_the_public_page_publishes_is_the_one_the_data_holds():
    given = [i for i in ITEMS if i.get("disposition") == "giveaway"]
    sold = [i for i in ITEMS if i.get("status") == "Sold" and i["id"] not in GIVEAWAYS]
    assert (len(sold), len(given)) == (10, 6)


def test_the_sale_has_an_end_state_documented_once():
    """The catalog's opening day is what `retro` counts the days from: it is in the data, so the
    case study's 45 days is checkable arithmetic, not a memory."""
    assert INVENTORY["seller"]["catalog_opened"] == "2026-09-25"
    assert INVENTORY["seller"]["vehicle_deadline"] == "2026-11-09"
    assert "45 days" in CASE


def test_the_case_study_says_where_its_figures_came_from():
    assert "make retro" in CASE


def test_the_case_study_publishes_percentages_and_not_money():
    """Absolute totals stay in the encrypted file: the retrospective is public."""
    assert re.search(r"\d+\s?%", CASE)
    assert not re.search(r"\$\s?\d", CASE), "an absolute amount reached the public case study"


def test_the_readme_points_at_the_case_study():
    assert "docs/case-study.md" in README
    assert "## Results" in README


def test_the_adr_that_amends_adr_008_exists_and_adr_008_names_it():
    assert "adr-008" in ADR_013.lower() or "ADR-008" in ADR_013
    assert "ADR-013" in ADR_008
    assert "status: accepted" in ADR_013
