"""
The not-found page (BUG-013): the build writes a top-level `404.html`, in the catalog build and in
the end-of-sale build alike. Without one, Cloudflare Pages treats the site as a single-page app
and answers every unknown path with the catalog and a 200 (the rule is in
specs/archive/BUG-013-not-found-page/proposal.md). Pages serves that one file for every missing path, at
the URL that was asked for, so it is bilingual, carries no contact or item data, and reaches its
own assets by root-absolute paths.

Every build here is a scratch copy of the real inventory, so the tests read nothing of the live
`build/public` and keep running when `seller.sale_over` is committed on.
"""

import copy
import re
import shutil
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import pytest
import yaml

from leaving_denver import site_builder
from leaving_denver.config import DATA_DIR

ROOT = Path(__file__).resolve().parents[1]
BUILT = ROOT / "build" / "public"
SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))
COPY = yaml.safe_load((ROOT / "locales" / "not_found.yaml").read_text(encoding="utf-8"))
ITEM_IDS = [entry["id"] for kind in ("items", "bundles") for entry in SOURCE[kind]]
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
# Pages serves the 404 at the requested URL, whatever its depth.
DEPTHS = ("/", "/es/", "/i/sofa-sleeper/", "/a/b/c/d/e")


def inventory(sale_over):
    data = copy.deepcopy(SOURCE)
    data["seller"].pop("sale_over", None)
    if sale_over:
        data["seller"]["sale_over"] = True
    return data


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", SENTINEL)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


@pytest.fixture(params=["catalog", "end"])
def mode(request):
    return request.param


@pytest.fixture
def built(public_dir, mode):
    site_builder.build_public_site(inventory(sale_over=mode == "end"))
    return public_dir


@pytest.fixture
def page(built):
    return (built / "404.html").read_text(encoding="utf-8")


def text_of(html):
    """What a reader sees: the body without tags, scripts and styles."""
    body = re.search(r"<body.*?</body>", html, flags=re.DOTALL).group(0)
    body = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", body, flags=re.DOTALL)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", body))).strip()


def references(html):
    """Every href and src of the page."""
    return re.findall(r'\b(?:href|src)="([^"]*)"', html)


# AC1: the page exists in both modes and says so in both languages.


def test_the_build_writes_a_top_level_404(built):
    assert (built / "404.html").is_file()


def test_the_page_says_so_in_both_languages(page):
    text = text_of(page)
    for language in ("en", "es"):
        assert COPY[language]["heading"] in text
        assert COPY[language]["body"] in text
        assert COPY[language]["home"] in text
    assert "<title>" + COPY["en"]["title"] in page
    assert COPY["es"]["title"] in re.search(r"<title>.*?</title>", page).group(0)


def test_each_language_links_to_its_own_home_page(page):
    english, spanish = re.findall(r"<section\b.*?</section>", page, flags=re.DOTALL)
    assert 'lang="en"' in english
    assert references(english).count("/") == 1
    assert 'lang="es"' in spanish
    assert references(spanish).count("/es/") == 1


def test_the_page_stays_out_of_search(page):
    assert re.search(r'<meta name="robots" content="[^"]*noindex', page)


# AC1: no contact and no item data, whatever the mode.


def test_the_page_carries_no_phone_in_any_form(built):
    page = (built / "404.html").read_text(encoding="utf-8")
    for form in PHONE_FORMS:
        assert form not in page, form
    assert not re.search(r"\bsms:|\btel:", page)
    assert "const _C" not in page
    assert "<script" not in page


def test_the_page_names_no_item_and_no_price(page):
    for item_id in ITEM_IDS:
        assert item_id not in page, item_id
    assert "data-item=" not in page
    assert "INVENTORY" not in page
    assert not re.search(r"\$\s?\d", page)


# AC1: it works at any depth.


@pytest.mark.parametrize("depth", DEPTHS)
def test_every_reference_resolves_to_the_same_place_from_any_depth(page, depth):
    # A relative path would resolve against /i/sofa-sleeper/ and miss the stylesheet.
    for ref in references(page):
        assert ref.startswith("/") and not ref.startswith("//"), ref
        assert urljoin(f"https://x.test{depth}", ref) == urljoin("https://x.test/", ref), ref


@pytest.mark.skipif(not (BUILT / "styles.css").exists(), reason="site not built")
def test_every_reference_is_a_file_of_the_site(built, page):
    shutil.copy2(BUILT / "styles.css", built / "styles.css")
    shutil.copytree(BUILT / "fonts", built / "fonts")
    for ref in references(page):
        path = ref.split("#")[0].lstrip("/")
        target = built / path
        assert target.is_file() or (target / "index.html").is_file() or path == "", ref


def test_the_page_uses_the_compiled_stylesheet(page):
    assert '<link rel="stylesheet" href="/styles.css">' in page
    assert "cdn.tailwindcss.com" not in page


# The end build's own contract (OPS-011) still holds with the page in it.


def test_the_end_build_keeps_the_page_when_it_sweeps_a_catalog_away(public_dir):
    site_builder.build_public_site(inventory(sale_over=False))
    assert (public_dir / "i" / "sofa-sleeper" / "index.html").is_file()
    site_builder.build_public_site(inventory(sale_over=True))
    assert (public_dir / "404.html").is_file()
    assert not (public_dir / "i").exists()


def test_the_end_redirects_do_not_swallow_the_page(public_dir):
    site_builder.build_public_site(inventory(sale_over=True))
    sources = [line.split()[0] for line in (public_dir / "_redirects").read_text().splitlines()]
    assert not any(source == "/404.html" or source in ("/*", "/:splat") for source in sources), (
        sources
    )


# The live build, whichever mode `make check` runs in.


@pytest.mark.skipif(not (BUILT / "index.html").exists(), reason="site not built")
def test_the_live_build_has_the_page():
    live = (BUILT / "404.html").read_text(encoding="utf-8")
    assert 'data-role="not-found"' in live
    assert "const _C" not in live
