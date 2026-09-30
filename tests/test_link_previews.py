"""
Link previews and per-item links (FEAT-002): preview crawlers may fetch the site, every
published item has a share page with Open Graph tags that sends people on to `/#<id>`,
and the preview image is a letterboxed 1200x630 JPEG rebuilt only when it changes.
"""

import re
from html import unescape
from urllib.robotparser import RobotFileParser

import pytest
from PIL import Image
from test_build_contract import inventory

from leaving_denver import image_processor, site_builder

PHONE = "+15555550100"
SITE = "https://leaving-denver.pages.dev"
PREVIEW_BOTS = ("facebookexternalhit", "Facebot", "Twitterbot", "TelegramBot", "WhatsApp")


def make_cover(path, size=(800, 800), colour=(200, 30, 30)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path, "JPEG", quality=90)


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.delenv("SITE_URL", raising=False)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


def with_photos(dist, hidden_published=False):
    """The contract inventory, with a built cover for each item."""
    data = inventory(hidden_published=hidden_published)
    for item in data["items"]:
        image = f"catalog/{item['id']}/cover.jpg"
        make_cover(dist / image)
        item["images"] = [image]
    data["items"][0]["status"] = "Sold"
    return data


def meta(html, prop):
    found = re.search(rf'<meta (?:property|name)="{re.escape(prop)}" content="([^"]*)"', html)
    return unescape(found.group(1)) if found else None


def test_robots_lets_preview_crawlers_in_and_keeps_everyone_else_out(public_dir):
    site_builder.build_public_site(with_photos(public_dir))
    robots = RobotFileParser()
    robots.parse((public_dir / "robots.txt").read_text(encoding="utf-8").splitlines())
    paths = ("/", "/i/shown-lamp/", "/es/i/shown-lamp/", "/catalog/shown-lamp/og/cover.jpg")
    for bot in PREVIEW_BOTS:
        agent = f"{bot}/1.1 (+https://example.com)"
        assert all(robots.can_fetch(agent, path) for path in paths), bot
    for bot in ("Googlebot/2.1", "bingbot/2.0", "GPTBot/1.0", "CCBot/2.0", "Slackbot"):
        assert not any(robots.can_fetch(bot, path) for path in paths), bot
    assert "X-Robots-Tag: noindex" in (public_dir / "_headers").read_text(encoding="utf-8")


@pytest.mark.parametrize(("prefix", "locale"), [("", "en_US"), ("es/", "es_ES")])
def test_each_published_item_has_a_share_page(public_dir, prefix, locale):
    site_builder.build_public_site(with_photos(public_dir))
    html = (public_dir / prefix / "i" / "shown-lamp" / "index.html").read_text(encoding="utf-8")
    assert meta(html, "og:title") == "Shown lamp"
    assert meta(html, "og:url") == f"{SITE}/{prefix}i/shown-lamp/"
    assert meta(html, "og:locale") == locale
    image = meta(html, "og:image")
    assert image == f"{SITE}/catalog/shown-lamp/og/cover.jpg"
    assert (public_dir / image.removeprefix(SITE + "/")).is_file()
    assert (meta(html, "og:image:width"), meta(html, "og:image:height")) == ("1200", "630")
    assert meta(html, "twitter:card") == "summary_large_image"
    description = meta(html, "og:description")
    assert "$10" in description
    assert ("Sold" if not prefix else "Vendido") in description
    # JS only: a crawler that followed a meta refresh or an HTTP redirect would read the
    # catalog's tags at `/`, where the hash is lost.
    assert "http-equiv" not in html.lower()
    assert 'location.replace("../../#shown-lamp")' in html
    assert 'href="../../#shown-lamp"' in html
    assert "noindex" in html


def test_share_pages_leak_nothing_unpublished_and_no_contact(public_dir):
    # A page left by an earlier build, when the item was still published.
    stale = public_dir / "es" / "i" / "hidden-widget" / "index.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("Hidden widget")
    site_builder.build_public_site(with_photos(public_dir))
    assert not (public_dir / "i" / "hidden-widget").exists()
    assert not (public_dir / "es" / "i" / "hidden-widget").exists()
    assert not (public_dir / "catalog" / "hidden-widget").exists()
    pages = list(public_dir.glob("**/i/*/index.html"))
    assert len(pages) == 2, pages
    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert "const _C" not in html
        assert "5550100" not in html


def test_markup_in_a_title_stays_text(public_dir):
    data = with_photos(public_dir)
    data["items"][0]["title"] = 'Lamp "Arc" & shade </script><b>'
    site_builder.build_public_site(data)
    html = (public_dir / "i" / "shown-lamp" / "index.html").read_text(encoding="utf-8")
    assert meta(html, "og:title") == 'Lamp "Arc" & shade </script><b>'
    assert "<b>" not in html
    assert html.count("</script>") == 1


@pytest.mark.parametrize("item_id", ["../escape", "Shown-Lamp", "lamp/x", "lamp#x", "-lamp"])
def test_an_item_id_that_is_not_a_slug_fails(public_dir, item_id):
    data = with_photos(public_dir)
    data["items"][0]["id"] = item_id
    data["bundles"] = []
    with pytest.raises(RuntimeError, match="slug"):
        site_builder.build_public_site(data)
    assert not (public_dir.parent / "escape").exists()


def test_an_item_without_a_photo_has_no_preview_image(public_dir):
    site_builder.build_public_site(inventory())
    html = (public_dir / "i" / "shown-lamp" / "index.html").read_text(encoding="utf-8")
    assert meta(html, "og:title") == "Shown lamp"
    assert meta(html, "og:image") is None


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
def test_catalog_pages_carry_their_own_preview(public_dir, page):
    site_builder.build_public_site(with_photos(public_dir))
    html = (public_dir / page).read_text(encoding="utf-8")
    assert meta(html, "og:title")
    assert meta(html, "og:description")
    assert meta(html, "og:url") == f"{SITE}/{page.removesuffix('index.html')}"
    image = meta(html, "og:image")
    assert image and image.startswith(SITE + "/catalog/")
    assert (public_dir / image.removeprefix(SITE + "/")).is_file()


@pytest.mark.parametrize(
    "value", ["http://example.com", "https://example.com/sub", "https://example.com/", "example"]
)
def test_a_site_url_that_is_not_a_bare_https_origin_fails(public_dir, monkeypatch, value):
    monkeypatch.setenv("SITE_URL", value)
    with pytest.raises(ValueError, match="SITE_URL"):
        site_builder.build_public_site(with_photos(public_dir))


def test_site_url_comes_from_the_environment(public_dir, monkeypatch):
    monkeypatch.setenv("SITE_URL", "https://sale.example.com")
    site_builder.build_public_site(with_photos(public_dir))
    html = (public_dir / "i" / "shown-lamp" / "index.html").read_text(encoding="utf-8")
    assert meta(html, "og:url") == "https://sale.example.com/i/shown-lamp/"


def test_preview_image_is_letterboxed_not_cropped(tmp_path):
    cover = tmp_path / "catalog" / "desk" / "desk-1.jpg"
    make_cover(cover, size=(600, 900))
    preview = image_processor.write_share_image(cover)
    assert preview == cover.parent / "og" / "desk-1.jpg"
    with Image.open(preview) as img:
        assert img.size == (1200, 630)
        assert img.format == "JPEG"
        rgb = img.convert("RGB")
        # A tall photo keeps its whole height: bands of page background at the sides.
        for x in (5, 1194):
            assert all(
                abs(a - b) <= 3
                for a, b in zip(rgb.getpixel((x, 315)), (251, 251, 251), strict=True)
            )
        red, green, blue = rgb.getpixel((600, 315))
        assert red > 150 and green < 80 and blue < 80
        red, _, _ = rgb.getpixel((600, 5))
        assert red > 150, "the top of the photo was cropped"


def test_preview_image_is_rewritten_only_when_it_changes(tmp_path):
    cover = tmp_path / "catalog" / "desk" / "desk-1.jpg"
    make_cover(cover)
    preview = image_processor.write_share_image(cover)
    before = preview.stat().st_mtime_ns
    assert image_processor.write_share_image(cover) == preview
    assert preview.stat().st_mtime_ns == before
    make_cover(cover, colour=(20, 30, 200))
    image_processor.write_share_image(cover)
    with Image.open(preview) as img:
        assert img.convert("RGB").getpixel((600, 315))[2] > 150
    assert not list(preview.parent.glob("*.tmp"))


def test_a_new_cover_prunes_the_old_preview(tmp_path):
    folder = tmp_path / "catalog" / "desk"
    make_cover(folder / "desk-1.jpg")
    make_cover(folder / "desk-2.jpg")
    old = image_processor.write_share_image(folder / "desk-1.jpg")
    notes = folder / "og" / "notes.txt"
    notes.write_text("kept")
    new = image_processor.write_share_image(folder / "desk-2.jpg")
    assert new.is_file()
    assert not old.exists()
    assert notes.exists(), "only preview JPEGs are pruned"


def test_deep_link_opens_the_item_after_load():
    html = (site_builder.TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    ready = html.split("document.addEventListener('DOMContentLoaded'")[1]
    assert "const linked = location.hash.slice(1);" in ready
    # The hash goes before the sheet opens: a reload after closing shows the catalog.
    assert ready.index("history.replaceState(null, '', location.pathname") < ready.index(
        "openModal(linked)"
    )
