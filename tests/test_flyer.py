"""
The building flyer (FEAT-010): `/flyer/` is one printable Letter page with a QR code for the
catalog, a plain first-person pitch from the data, and no phone, no price and no email.
The seller prints it from a browser; search engines and the catalog never see it.

Every build here is a scratch copy of the real inventory, so the tests read nothing of the live
`build/public` and keep running when `seller.sale_over` is committed on.
"""

import copy
import re
from html import unescape
from pathlib import Path

import pytest
import segno
import yaml

from leaving_denver import site_builder
from leaving_denver.config import DATA_DIR

ROOT = Path(__file__).resolve().parents[1]
SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))
COPY = yaml.safe_load((ROOT / "locales" / "flyer.yaml").read_text(encoding="utf-8"))
EN, ES = COPY["en"], COPY["es"]

# Written out, not built from the code under test: a change to the origin, the path or a
# parameter must fail here.
URL = "https://leaving-denver.pages.dev/?utm_source=flyer&utm_medium=print&utm_campaign=moving-sale"
# Not a real number and not the CI placeholder: it must reach no built file in any form.
SENTINEL = "+13035550100"
PHONE_FORMS = (
    "3035550100",
    "303-555-0100",
    "303.555.0100",
    "303 555 0100",
    "(303) 555-0100",
    "+13035550100",
)
QUIET_ZONE = 4


def catalog_inventory():
    data = copy.deepcopy(SOURCE)
    data["seller"].pop("sale_over", None)
    return data


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


def build_flyer(public_dir, data=None):
    site_builder.build_public_site(data or catalog_inventory())
    return (public_dir / "flyer" / "index.html").read_text(encoding="utf-8")


@pytest.fixture
def flyer(public_dir):
    return build_flyer(public_dir)


def head_of(page):
    return re.search(r"<head>.*?</head>", page, flags=re.DOTALL).group(0)


def text_of(page):
    """What a reader sees: the body without tags, scripts and styles."""
    body = re.search(r"<body.*?</body>", page, flags=re.DOTALL).group(0)
    body = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", body, flags=re.DOTALL)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", body))).strip()


def qr_matrix(page):
    """The dark modules of the page's inline QR, read back from its SVG path, quiet zone cut."""
    svg = re.search(r"<svg\b.*?</svg>", page, flags=re.DOTALL).group(0)
    side = int(re.search(r'viewBox="0 0 (\d+) \1"', svg).group(1))
    path = re.search(r'<path class="qrline"[^>]* d="([^"]+)"', svg).group(1)
    grid = [[0] * side for _ in range(side)]
    x = y = 0.0
    for command, first, second in re.findall(r"([MmhHvV])\s*(-?[\d.]+)(?:[\s,]+(-?[\d.]+))?", path):
        match command:
            case "M":
                x, y = float(first), float(second)
            case "m":
                x, y = x + float(first), y + float(second)
            case "h":
                for module in range(round(x), round(x + float(first))):
                    grid[int(y)][module] = 1
                x += float(first)
            case _:
                raise AssertionError(f"unexpected path command {command!r}")
    inner = range(QUIET_ZONE, side - QUIET_ZONE)
    return [[grid[row][col] for col in inner] for row in inner]


# AC2: the QR.


def test_the_url_is_the_origin_with_the_print_parameters():
    assert site_builder.flyer_url("https://leaving-denver.pages.dev") == URL


def test_the_qr_is_exactly_the_matrix_of_the_utm_url(flyer):
    assert qr_matrix(flyer) == [list(row) for row in segno.make(URL, error="m").matrix]


def test_the_check_notices_another_url(flyer):
    other = URL.replace("utm_medium=print", "utm_medium=paper")
    assert qr_matrix(flyer) != [list(row) for row in segno.make(other, error="m").matrix]


def test_the_qr_has_a_quiet_zone_and_scales_with_its_box(flyer):
    svg = re.search(r"<svg\b[^>]*>", flyer).group(0)
    matrix = segno.make(URL, error="m").matrix
    side = len(matrix) + 2 * QUIET_ZONE
    assert f'viewBox="0 0 {side} {side}"' in svg
    assert "width=" not in svg, "a fixed size would not follow the page"


def test_the_qr_follows_the_origin_the_build_is_given(public_dir, monkeypatch):
    monkeypatch.setenv("SITE_URL", "https://example.org")
    page = build_flyer(public_dir)
    other = "https://example.org/?utm_source=flyer&utm_medium=print&utm_campaign=moving-sale"
    assert qr_matrix(page) == [list(row) for row in segno.make(other, error="m").matrix]
    assert "example.org" in text_of(page)


def test_the_address_is_printed_under_the_qr_without_tracking(flyer):
    text = text_of(flyer)
    assert "leaving-denver.pages.dev" in text
    assert "utm_" not in text
    assert flyer.index("<svg") < flyer.index("leaving-denver.pages.dev</")


def test_the_qr_is_labelled_for_a_screen_reader(flyer):
    assert "<title>" in re.search(r"<svg\b.*?</svg>", flyer, flags=re.DOTALL).group(0)


# AC1: the page.


FLYER_CSS = ROOT / "src" / "leaving_denver" / "assets" / "flyer.css"


def test_the_page_takes_its_rules_from_a_file_beside_it_not_an_inline_style(flyer, public_dir):
    """An inline <style> would need `style-src 'unsafe-inline'` (ADR-010)."""
    assert "<style" not in flyer
    assert '<link rel="stylesheet" href="flyer.css">' in head_of(flyer)
    assert (public_dir / "flyer" / "flyer.css").read_text() == FLYER_CSS.read_text()


def test_the_page_is_one_letter_sheet_in_print():
    css = FLYER_CSS.read_text(encoding="utf-8")
    page_rule = re.search(r"@page\s*\{([^}]*)\}", css).group(1)
    assert re.search(r"size:\s*letter\b", page_rule)
    assert re.search(r"margin:\s*0\.5in\b", page_rule)


def test_the_page_needs_no_script_image_or_other_host(flyer):
    assert "<script" not in flyer
    assert "<img" not in flyer
    hosts = set(re.findall(r"https?://([^/\s\"'<>)]+)", flyer))
    assert hosts <= {"leaving-denver.pages.dev"}, hosts


def test_the_page_resets_the_catalogs_bottom_padding(flyer):
    # public.css pads <body> 6rem for the sticky bar, unlayered, so a utility would lose to it
    # (lesson-020): on paper that padding would push the page onto a second sheet. flyer.css
    # is linked after styles.css, so its rule wins on equal specificity.
    css = FLYER_CSS.read_text(encoding="utf-8")
    head = head_of(flyer)
    assert head.index("styles.css") < head.index("flyer.css")
    assert re.search(r"body\s*\{[^}]*padding:\s*0\b", css)


def test_the_page_says_what_the_brief_asks(flyer):
    text = text_of(flyer)
    for phrase in (
        EN["heading"],
        EN["pickup"],
        EN["scan"],
        ES["scan"],
    ):
        assert phrase in text, phrase
    assert re.search(r'<[a-z]+ lang="es"[^>]*>\s*' + re.escape(ES["scan"]), flyer)


def test_the_copy_is_first_person_singular(flyer):
    text = text_of(flyer)
    assert re.search(r"\bI['’]m\b|\bI am\b|\bmy\b|\bme\b", text, flags=re.IGNORECASE)
    assert not re.search(r"\bwe\b|\bour\b|\bus\b", text, flags=re.IGNORECASE)


# AC3: no contact, no price.


def test_the_flyer_holds_no_phone_in_any_form(flyer):
    for form in PHONE_FORMS:
        assert form not in flyer, form
    assert not re.search(r"\b(sms|tel|mailto):", flyer, flags=re.IGNORECASE)
    assert "const _C" not in flyer


def test_the_flyer_holds_no_email_address(flyer):
    # `@page` and `@media` are CSS, so look for a name before the sign and a domain after it.
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", flyer)
    assert SOURCE["seller"]["email"] not in flyer


def test_the_flyer_names_no_price(flyer):
    assert "$" not in flyer
    # The only figures on the page are the car's own name: no price, and no date (FEAT-014).
    car = next(i for i in SOURCE["items"] if i["category"] == "Vehicle")["short_title"]
    assert set(re.findall(r"\d+", text_of(flyer))) <= set(re.findall(r"\d+", car))


# AC4: copy from the data.

CATEGORY_LABELS = {
    "Living Room": "Living room",
    "Bedroom": "Bedroom",
    "Home Office & Tech": "Office & tech",
    "Dining & Kitchen": "Kitchen",
}


def test_the_real_flyer_lists_every_category_of_the_catalog(flyer):
    text = text_of(flyer)
    for label in CATEGORY_LABELS.values():
        assert label in text, label
    assert "Vehicle" not in text, "the car has its own line, not a category"


def test_the_categories_come_from_the_data_not_from_the_template(public_dir):
    data = catalog_inventory()
    data["items"] = [i for i in data["items"] if i["category"] in {"Bedroom", "Dining & Kitchen"}]
    data["bundles"] = []
    text = text_of(build_flyer(public_dir, data))
    assert "Bedroom" in text and "Kitchen" in text
    assert "Living room" not in text and "Office & tech" not in text


def test_a_category_with_nothing_left_is_not_advertised(public_dir):
    data = catalog_inventory()
    for item in data["items"]:
        if item["category"] == "Bedroom":
            item["status"] = "Sold"
    text = text_of(build_flyer(public_dir, data))
    assert "Bedroom" not in text and "Kitchen" in text


def test_the_car_is_named_by_its_short_title(flyer):
    car = next(i for i in SOURCE["items"] if i["category"] == "Vehicle")
    assert car["short_title"] in text_of(flyer)
    assert car["title"] not in text_of(flyer)


def test_a_sold_car_is_not_mentioned(public_dir):
    data = catalog_inventory()
    car = next(i for i in data["items"] if i["category"] == "Vehicle")
    car["status"] = "Sold"
    assert car["short_title"] not in text_of(build_flyer(public_dir, data))


def test_a_catalog_without_a_car_still_makes_a_flyer(public_dir):
    data = catalog_inventory()
    data["items"] = [i for i in data["items"] if i["category"] != "Vehicle"]
    data["bundles"] = [b for b in data["bundles"] if "2019-ford-escape-sel-awd" not in b["items"]]
    assert "Escape" not in text_of(build_flyer(public_dir, data))


def test_the_date_is_stated_as_a_fact_and_not_as_pressure(flyer):
    text = text_of(flyer)
    assert not re.search(
        r"hurry|last chance|limited|act now|don['’]t miss|going fast|while (they|supplies)"
        r"|prices (go|will|are going) up|people (are )?(asking|interested)",
        text,
        flags=re.IGNORECASE,
    )


def test_the_copy_has_no_em_dash(flyer):
    assert "—" not in text_of(flyer)
    assert "—" not in "".join([*EN.values(), *ES.values()])


# AC5: hidden, not linked.


def test_the_page_is_kept_out_of_search(flyer):
    assert re.search(r'<meta name="robots" content="[^"]*noindex', head_of(flyer))


def test_nothing_else_links_to_the_flyer(public_dir, flyer):
    for path in public_dir.rglob("*.html"):
        if path == public_dir / "flyer" / "index.html":
            continue
        assert "flyer" not in path.read_text(encoding="utf-8").lower(), path


def test_the_site_still_keeps_every_other_crawler_out(public_dir, flyer):
    robots = (public_dir / "robots.txt").read_text(encoding="utf-8")
    assert re.search(r"User-agent: \*\nDisallow: /\n?$", robots)
    assert "X-Robots-Tag: noindex" in (public_dir / "_headers").read_text(encoding="utf-8")


# AC7: end of sale.


def end_inventory():
    data = copy.deepcopy(SOURCE)
    data["seller"]["sale_over"] = True
    return data


def test_the_end_build_does_not_make_a_flyer(public_dir):
    site_builder.build_public_site(end_inventory())
    assert not (public_dir / "flyer").exists()


def test_a_flyer_left_by_a_catalog_build_is_swept_by_the_end_build(public_dir, flyer):
    assert (public_dir / "flyer" / "index.html").is_file()
    site_builder.build_public_site(end_inventory())
    assert not (public_dir / "flyer").exists()


def test_the_old_flyer_address_lands_on_the_end_page(public_dir):
    site_builder.build_public_site(end_inventory())
    rules = (public_dir / "_redirects").read_text(encoding="utf-8").splitlines()
    assert "/flyer / 302" in rules
    assert "/flyer/* / 302" in rules


# AC8: the playbook and the stylesheet.


def test_the_playbook_says_where_to_print_the_flyer_from():
    playbook = (ROOT / "docs" / "runbooks" / "seller-playbook.md").read_text(encoding="utf-8")
    assert "https://leaving-denver.pages.dev/flyer/" in playbook
