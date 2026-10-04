"""
The end-of-sale build (OPS-011): one switch, `seller.sale_over`, turns the site into a single
"the sale is over" page. No phone, no item, no photo, no share page and no seller tool are
published, and the build needs no secret. Shared links land on the end page instead of a 404.

The committed data keeps the switch off; every test here builds a scratch copy with it on.
"""

import copy
import re
from pathlib import Path

import pytest
import yaml

from leaving_denver import private_data, site_builder
from leaving_denver.config import DATA_DIR

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
SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))
ITEM_IDS = [entry["id"] for kind in ("items", "bundles") for entry in SOURCE[kind]]
# Everything an end build may publish, relative to the output root.
ALLOWED = {
    "index.html",
    "es/index.html",
    "404.html",
    "robots.txt",
    "_headers",
    "_redirects",
    "favicon.svg",
}


def end_inventory():
    """The real inventory with the switch on, in memory: the committed file is never touched."""
    data = copy.deepcopy(SOURCE)
    data["seller"]["sale_over"] = True
    return data


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    """A scratch build root, and a build environment with the sentinel phone only."""
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", SENTINEL)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


@pytest.fixture
def end_dir(public_dir):
    site_builder.build_public_site(end_inventory())
    return public_dir


def files_under(root):
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def everything_under(root):
    """Every path and every file body under root, as one string."""
    parts = []
    for path in sorted(root.rglob("*")):
        parts.append(path.relative_to(root).as_posix())
        if path.is_file():
            parts.append(path.read_bytes().decode("utf-8", errors="replace"))
    return "\n".join(parts)


def head_of(page):
    return re.search(r"<head>.*?</head>", page, flags=re.DOTALL).group(0)


# AC5: the default is unchanged.


def test_the_switch_is_off_until_the_owner_ends_the_sale():
    # A guard against flipping it in an ordinary change. Skipped once it is on, by conftest, so
    # the flip itself passes.
    assert SOURCE["seller"].get("sale_over", False) is False


@pytest.mark.parametrize("seller", [{}, {"sale_over": False}])
def test_the_switch_defaults_to_off(seller):
    assert site_builder.sale_over({"seller": seller}) is False


def test_the_switch_turns_on():
    assert site_builder.sale_over({"seller": {"sale_over": True}}) is True


@pytest.mark.parametrize("value", ["true", "yes", 1, 0, None, []])
def test_the_switch_must_be_a_boolean(value):
    # YAML reads `sale_over: yes` and `sale_over: "true"` as other types; a build that took
    # them as off would publish the catalog on the day the owner meant to close it.
    with pytest.raises(ValueError, match="sale_over"):
        site_builder.sale_over({"seller": {"sale_over": value}})


def test_with_the_switch_off_the_catalog_is_built(public_dir):
    data = copy.deepcopy(SOURCE)
    data["seller"].pop("sale_over", None)
    site_builder.build_public_site(data)
    page = (public_dir / "index.html").read_text(encoding="utf-8")
    assert 'data-role="sale-over"' not in page
    assert "const _C = " in page
    assert "i/sofa-sleeper/index.html" in files_under(public_dir)


# AC1: no phone, no item.


def test_no_file_carries_the_phone_in_any_form(end_dir):
    text = everything_under(end_dir)
    for form in PHONE_FORMS:
        assert form not in text, form
    assert not re.search(r"\bsms:|\btel:", text)
    assert "const _C" not in text


def test_no_file_names_an_item(end_dir):
    text = everything_under(end_dir)
    for item_id in ITEM_IDS:
        assert item_id not in text, item_id
    assert "data-item=" not in text
    assert "INVENTORY" not in text


def test_the_end_pages_collect_nothing(end_dir):
    """The sale metrics (ADR-011) end with the sale: no end page carries the beacon, so the
    phone-leak guard that is skipped in this mode has nothing to guard."""
    text = everything_under(end_dir)
    assert "sendBeacon" not in text
    assert "/api/hit" not in text


def test_nothing_but_the_end_page_and_its_plumbing_is_published(end_dir):
    assert files_under(end_dir) == ALLOWED


# AC2: the end page.


@pytest.mark.parametrize(
    ("page", "message", "other", "other_href"),
    [
        ("index.html", "The sale is over", "es", "es/"),
        ("es/index.html", "La venta terminó", "en", "../"),
    ],
)
def test_the_end_page_says_so_in_its_language(end_dir, page, message, other, other_href):
    html = (end_dir / page).read_text(encoding="utf-8")
    assert 'data-role="sale-over"' in html
    assert message in re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.DOTALL).group(1)
    assert message in re.search(r"<title>(.*?)</title>", html).group(1)
    assert message in re.search(r'og:title" content="([^"]*)"', html).group(1)
    assert f'hreflang="{other}"' in html
    assert f'href="{other_href}" hreflang="{other}"' in html


def test_a_shared_link_previews_as_sale_over(end_dir):
    # ADR-004: robots.txt still lets the preview crawlers in, so the card is the end message.
    robots = (end_dir / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: facebookexternalhit\nAllow: /" in robots
    html = (end_dir / "index.html").read_text(encoding="utf-8")
    assert 'og:url" content="https://leaving-denver.pages.dev/"' in html
    assert "og:image" not in html


def test_the_end_page_is_still_kept_out_of_search(end_dir):
    assert "noindex" in head_of((end_dir / "index.html").read_text(encoding="utf-8"))
    assert "X-Robots-Tag: noindex" in (end_dir / "_headers").read_text(encoding="utf-8")


# AC3: nothing else is served.


def test_old_share_links_land_on_the_end_page(end_dir):
    rules = (end_dir / "_redirects").read_text(encoding="utf-8").splitlines()
    assert "/i/* / 302" in rules
    assert "/es/i/* /es/ 302" in rules


def test_a_stale_catalog_is_swept_from_the_output(public_dir):
    # The output root outlives builds: a catalog built before the switch flipped is still in it.
    stale = [
        "catalog/sofa-sleeper/sofa-3.jpg",
        "catalog/sofa-sleeper/og/sofa-3.jpg",
        "i/sofa-sleeper/index.html",
        "es/i/sofa-sleeper/index.html",
        "seller/index.html",
        "seller/seller.mjs",
    ]
    for name in stale:
        path = public_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"stale")
    # What the stylesheet step wrote before the page build ran: it must survive.
    (public_dir / "styles.css").write_text("body{}")
    (public_dir / "fonts").mkdir()
    (public_dir / "fonts" / "plus-jakarta-sans-latin-wght-normal.woff2").write_bytes(b"font")

    site_builder.build_public_site(end_inventory())

    assert files_under(public_dir) == ALLOWED | {
        "styles.css",
        "fonts/plus-jakarta-sans-latin-wght-normal.woff2",
    }
    for directory in ("i", "es/i", "seller", "catalog"):
        assert not (public_dir / directory).exists(), directory


# AC4: builds with no secrets.


def test_the_end_build_needs_no_phone_and_no_private_data(tmp_path, monkeypatch):
    inventory = tmp_path / "inventory.yaml"
    inventory.write_text(yaml.safe_dump(end_inventory()), encoding="utf-8")
    dist = tmp_path / "public"
    monkeypatch.delenv("SELLER_PHONE", raising=False)
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", inventory)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    monkeypatch.setattr(site_builder, "build_stylesheets", lambda: None)

    def unreachable(*_args, **_kwargs):
        raise AssertionError("the end build reached for a secret or a photo")

    # The key is gone from the machine: nothing may even try to read the encrypted file.
    for name in ("seller_phone", "sync_all_photos"):
        monkeypatch.setattr(site_builder, name, unreachable)
    for name in ("load_private", "decrypt_private"):
        monkeypatch.setattr(private_data, name, unreachable)

    site_builder.build_all()

    assert files_under(dist) == ALLOWED


# What the suite skips when the switch is on is listed by test, and the list must stay honest: a
# misspelt name skips nothing and the flip goes red; a security test on it would stop guarding.

SECURITY_NAME = re.compile(r"phone|private|isolation|access|secret")


def skipped_in_end_mode():
    from conftest import CATALOG_TESTS

    return [f"{module}::{name}" for module, names in CATALOG_TESTS.items() for name in names]


def test_every_test_skipped_in_end_mode_exists():
    from conftest import CATALOG_TESTS

    tests_dir = Path(__file__).parent
    for module, names in CATALOG_TESTS.items():
        text = (tests_dir / module).read_text(encoding="utf-8")
        for name in names:
            assert re.search(rf"^def {name}\(", text, re.M), f"{module}::{name}"


def test_no_security_test_is_skipped_in_end_mode():
    from conftest import SKIPPED_DESPITE_ITS_NAME

    skipped = skipped_in_end_mode()
    flagged = {node for node in skipped if SECURITY_NAME.search(node)}
    assert flagged <= set(SKIPPED_DESPITE_ITS_NAME), sorted(flagged - set(SKIPPED_DESPITE_ITS_NAME))
    # An exemption for a test that is no longer skipped is stale.
    assert set(SKIPPED_DESPITE_ITS_NAME) <= set(skipped)


def test_a_tests_own_inventory_keeps_its_switch(tmp_path, monkeypatch):
    # conftest lets tests that build from the committed inventory mean the catalog; a test with
    # its own file, like the end-build ones, must still get what it wrote.
    own = tmp_path / "inventory.yaml"
    own.write_text(yaml.safe_dump(end_inventory()), encoding="utf-8")
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", own)
    assert site_builder.load_inventory_yaml()["seller"]["sale_over"] is True
