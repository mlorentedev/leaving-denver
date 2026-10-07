"""
The social images (FEAT-017): `/social/` holds a collage for the feed, a QR story and the copy
to paste, all built from the sanitized data like the flyer. No price, no phone, no date; what
has sold drops out on the next build, and the whole directory is gone once the sale is over.

Every build here is a scratch copy of the real inventory with stand-in covers, so the tests read
nothing of the live `build/public`.
"""

import copy
import re
from html import unescape
from pathlib import Path

import pytest
import segno
import yaml
from PIL import Image

from leaving_denver import site_builder, social
from leaving_denver.config import DATA_DIR

ROOT = Path(__file__).resolve().parents[1]
SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))
COPY = yaml.safe_load((ROOT / "locales" / "social.yaml").read_text(encoding="utf-8"))

# Written out, not built from the code under test: a change to the origin, the path or a
# parameter must fail here.
ORIGIN = "https://leaving-denver.pages.dev"
CAMPAIGN = "utm_medium=social&utm_campaign=moving-sale"
STORY_URL = f"{ORIGIN}/?utm_source=instagram&{CAMPAIGN}"
LINKS = {source: f"{ORIGIN}/?utm_source={source}&{CAMPAIGN}" for source in social.SOURCES}
SENTINEL = "+13035550100"
PHONE_FORMS = ("3035550100", "303-555-0100", "303.555.0100", "303 555 0100", "(303) 555-0100")
URGENCY = re.compile(
    r"hurry|last chance|limited|act now|don['’]t miss|going fast|while (they|supplies)"
    r"|everything must go|prices (go|will|are going) up|people (are )?(asking|interested)",
    re.IGNORECASE,
)
DATE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d|\d{1,2}/\d{1,2}|\b20\d\d-",
    re.IGNORECASE,
)


def catalog_inventory():
    data = copy.deepcopy(SOURCE)
    data["seller"].pop("sale_over", None)
    return data


def with_covers(dist, data):
    """A flat stand-in for each item's built cover, where the real build would have put it."""
    for n, item in enumerate(data["items"]):
        if item.get("images"):
            cover = dist / item["images"][0]
            cover.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (800, 600), (40 + n * 13 % 200, 90, 140)).save(cover, "JPEG")
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


@pytest.fixture
def built(public_dir):
    site_builder.build_public_site(with_covers(public_dir, catalog_inventory()))
    return public_dir / "social"


def text_of(page):
    body = re.search(r"<body.*?</body>", page, flags=re.DOTALL).group(0)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", body))).strip()


def item(item_id, category, price, status="Available"):
    return {
        "id": item_id,
        "category": category,
        "price": price,
        "status": status,
        "images": [f"catalog/{item_id}/cover.jpg"],
    }


# AC1: the page and the two images.


def test_the_build_writes_the_page_and_both_images_at_their_sizes(built):
    with Image.open(built / "post.jpg") as post:
        assert (post.format, post.size) == ("JPEG", (1080, 1350))
    with Image.open(built / "story.png") as story:
        assert (story.format, story.size) == ("PNG", (1080, 1920))
    assert (built / "index.html").is_file()


def test_the_page_shows_both_images_the_caption_and_one_link_per_network(built):
    page = (built / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<img [^>]*src="post\.jpg"', page)
    assert re.search(r'<img [^>]*src="story\.png"', page)
    for url in LINKS.values():
        assert url.replace("&", "&amp;") in page, url
    assert COPY["en"]["heading"] in unescape(page)


def test_the_page_is_hidden_scriptless_and_self_contained(built):
    page = (built / "index.html").read_text(encoding="utf-8")
    head = re.search(r"<head>.*?</head>", page, flags=re.DOTALL).group(0)
    assert re.search(r'<meta name="robots" content="[^"]*noindex', head)
    assert "<script" not in page
    hosts = set(re.findall(r'(?:src|href)="https?://([^/"]+)', page))
    assert hosts <= {"leaving-denver.pages.dev"}, hosts


def test_the_font_is_the_sites_own_and_loads():
    assert social.load_font(site_builder.FONT_FILE, 40, 800).getbbox("Moving sale")[2] > 0
    with pytest.raises(OSError):
        social.load_font(Path("/nonexistent/font.woff2"), 40, 800)


# AC2: the story.


def test_the_story_qr_is_exactly_the_instagram_url():
    image = social.render_story(
        STORY_URL, social.story_lines(COPY, "leaving-denver.pages.dev"), site_builder.FONT_FILE
    )
    expected = segno.make(STORY_URL, error=social.QR_ERROR).matrix
    left, top, module = social.qr_geometry(len(expected))
    pixels = image.convert("L")
    for row, line in enumerate(expected):
        for col, dark in enumerate(line):
            centre = (left + col * module + module // 2, top + row * module + module // 2)
            assert (pixels.getpixel(centre) < 128) == bool(dark), (row, col)


def test_the_built_story_carries_the_instagram_url(built):
    lines = social.story_lines(COPY, "leaving-denver.pages.dev")
    expected = social.render_story(STORY_URL, lines, site_builder.FONT_FILE)
    with Image.open(built / "story.png") as story:
        assert story.convert("RGB").tobytes() == expected.tobytes()


def test_the_story_leaves_instagrams_bands_empty(built):
    with Image.open(built / "story.png") as story:
        rgb = story.convert("RGB")
        for box in (
            (0, 0, 1080, social.STORY_SAFE_TOP),
            (0, 1920 - social.STORY_SAFE_BOTTOM, 1080, 1920),
        ):
            colours = rgb.crop(box).getcolors()
            assert colours and len(colours) == 1, box
    assert (social.STORY_SAFE_TOP, social.STORY_SAFE_BOTTOM) == (250, 340)


# AC3: the collage.


def test_the_collage_takes_the_car_then_one_per_category_then_by_price():
    items = [
        item("lamp", "Living Room", 20),
        item("sofa", "Living Room", 220),
        item("tv", "Living Room", 85),
        item("bed", "Bedroom", 35),
        item("desk", "Home Office & Tech", 60),
        item("monitor", "Home Office & Tech", 95),
        item("car", "Vehicle", 11950),
    ]
    picked = [i["id"] for i in social.collage_items(items)]
    assert picked == ["car", "sofa", "monitor", "bed", "tv"]


def test_a_sold_item_is_never_in_the_collage_and_the_car_leaves_once_sold():
    items = [
        item("sofa", "Living Room", 220, "Sold"),
        item("tv", "Living Room", 85),
        item("car", "Vehicle", 11950, "Sold"),
    ]
    assert [i["id"] for i in social.collage_items(items)] == ["tv"]


def test_an_item_without_a_photo_is_skipped():
    no_photo = item("bare", "Bedroom", 500)
    no_photo["images"] = []
    assert [i["id"] for i in social.collage_items([no_photo, item("tv", "Living Room", 85)])] == [
        "tv"
    ]


@pytest.mark.parametrize("count", [1, 2, 3, 5])
def test_the_post_draws_as_many_cells_as_it_has_photos(tmp_path, count):
    photos = []
    for n in range(count):
        path = tmp_path / f"{n}.jpg"
        Image.new("RGB", (400, 300), (250, 0, 0)).save(path)
        photos.append(path)
    lines = social.post_lines(COPY, "leaving-denver.pages.dev", ["Bedroom"], None)
    image = social.render_post(photos, lines, site_builder.FONT_FILE).convert("RGB")
    assert image.size == (1080, 1350)
    cells = social.collage_cells(count)
    assert len(cells) == count
    for left, top, right, bottom in cells:
        r, g, b = image.getpixel(((left + right) // 2, (top + bottom) // 2))
        assert r > 200 and g < 60 and b < 60, (left, top)


# AC4: no contact, no price, no date; copy from the data.


def test_neither_the_page_nor_the_copy_holds_a_contact_a_price_or_a_date(built):
    page = (built / "index.html").read_text(encoding="utf-8")
    text = text_of(page)
    for form in PHONE_FORMS:
        assert form not in page, form
    assert "3035550100" not in re.sub(r"\D", "", page)
    assert not re.search(r"sms:|tel:|mailto:|[\w.+-]+@[\w-]+\.\w", page)
    assert "$" not in text
    assert not DATE.search(text), DATE.search(text)
    assert not URGENCY.search(text)


def test_the_copy_names_what_is_still_for_sale(public_dir):
    data = with_covers(public_dir, catalog_inventory())
    for i in data["items"]:
        if i["category"] in {"Bedroom", "Vehicle"}:
            i["status"] = "Sold"
    site_builder.build_public_site(data)
    text = text_of((public_dir / "social" / "index.html").read_text(encoding="utf-8"))
    assert "Bedroom" not in text and "Escape" not in text
    assert "Living room" in text


def test_the_caption_names_the_car_while_it_is_unsold(built):
    car = next(i for i in SOURCE["items"] if i["category"] == "Vehicle")
    text = text_of((built / "index.html").read_text(encoding="utf-8"))
    assert (car["short_title"] in text) == (car.get("status", "Available") != "Sold")


# AC5: end of sale.


def end_inventory():
    data = copy.deepcopy(SOURCE)
    data["seller"]["sale_over"] = True
    return data


def test_the_end_build_makes_no_social_directory_and_sweeps_a_stale_one(built, public_dir):
    assert (built / "post.jpg").is_file()
    site_builder.build_public_site(end_inventory())
    assert not (public_dir / "social").exists()
    rules = (public_dir / "_redirects").read_text(encoding="utf-8").splitlines()
    assert "/social / 302" in rules and "/social/* / 302" in rules


# AC7: hidden from the catalog, styled from the compiled stylesheet.


def test_nothing_else_links_to_the_social_page(built, public_dir):
    for path in public_dir.rglob("*.html"):
        if path.parent.name != "social":
            assert "social/" not in path.read_text(encoding="utf-8"), path
