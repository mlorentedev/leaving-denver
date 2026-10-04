"""
Security and isolation regression tests.
Verifies that no private seller data leaks into the public distribution (build/public/).
"""

import json
import re
import urllib.robotparser
from pathlib import Path

from conftest import sale_is_over

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "build" / "public"


def test_public_build_exists():
    assert DIST_DIR.exists()
    assert (DIST_DIR / "index.html").exists()
    assert (DIST_DIR / "robots.txt").exists()


def test_no_private_files_in_dist():
    for p in DIST_DIR.glob("**/*"):
        if p.is_file():
            name = p.name.lower()
            assert "poster" not in name, f"Private poster assistant leaked into dist: {p}"
            assert name != "inventory.json", f"Private inventory.json leaked into dist: {p}"


def test_no_floor_prices_in_public_html():
    for path in DIST_DIR.rglob("*.html"):
        public_html = path.read_text(encoding="utf-8")
        assert "firm_floor_price" not in public_html, f"Leaked firm_floor_price in {path}!"
        assert "floor_price" not in public_html, f"Leaked floor_price in {path}!"


def test_no_plain_phone_in_attributes():
    public_html = (DIST_DIR / "index.html").read_text(encoding="utf-8")
    # Verify no raw un-obfuscated phone in static hrefs
    assert not re.search(r'href="(sms|tel):\+?\d{10,}', public_html), (
        "Plaintext phone found in static href attribute"
    )


def test_robots_txt_disallow_all():
    robots = (DIST_DIR / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in robots
    assert "Disallow: /" in robots


def robots_parser():
    parser = urllib.robotparser.RobotFileParser()
    parser.parse((DIST_DIR / "robots.txt").read_text(encoding="utf-8").splitlines())
    return parser


# ADR-009: an assistant fetching the page because a person asked about it. Written out here,
# not imported from the builder, so the test fails if the builder's list widens or shrinks.
ASSISTANT_FETCHERS = ("ChatGPT-User", "Claude-User", "Perplexity-User", "MistralAI-User")
# Training and search crawlers stay out, along with everything not named.
TRAINING_AND_SEARCH = ("GPTBot", "ClaudeBot", "CCBot", "Google-Extended", "Googlebot", "Bingbot")


def test_assistants_a_person_asked_may_read_the_catalog():
    parser = robots_parser()
    for agent in ASSISTANT_FETCHERS:
        for path in ("/", "/es/", "/i/2019-ford-escape-sel-awd/"):
            assert parser.can_fetch(agent, f"https://leaving-denver.pages.dev{path}"), (agent, path)


def test_robots_txt_does_not_advertise_the_seller_tool():
    # Cloudflare Access guards /seller/ (ADR-007); a Disallow line would only point at it.
    assert "seller" not in (DIST_DIR / "robots.txt").read_text(encoding="utf-8")


def test_training_and_search_crawlers_stay_out():
    parser = robots_parser()
    for agent in TRAINING_AND_SEARCH:
        assert not parser.can_fetch(agent, "https://leaving-denver.pages.dev/"), agent


def test_pages_headers():
    headers = (DIST_DIR / "_headers").read_text(encoding="utf-8")
    assert "X-Content-Type-Options: nosniff" in headers
    assert "/catalog/*" in headers
    assert "max-age=" in headers


def test_no_pin_gate_and_no_private_workspace_remain():
    """The PIN-gated workspace is retired (ADR-007): the pin, the page and its folder are gone."""
    assert not (BASE_DIR / "build" / "private").exists()
    page = DIST_DIR / "seller" / "index.html"
    if sale_is_over():
        # The end build has no seller tool at all, so no PIN gate can be in it (OPS-011).
        assert not page.exists()
        return
    seller = page.read_text(encoding="utf-8")
    for gone in ("pinGateModal", "checkPin", "8011"):
        assert gone not in seller


def test_static_image_paths_exist():
    """Every <img src> written into the page as plain HTML points at a built file."""
    public_html = (DIST_DIR / "index.html").read_text(encoding="utf-8")
    for src in re.findall(r'<img[^>]+src="(catalog/[^"]+)"', public_html):
        assert (DIST_DIR / src).is_file(), f"Broken image path in page: {src}"


def test_template_sees_only_sanitized_data(tmp_path, monkeypatch):
    """The page template gets the sanitized inventory and the phone parts, nothing else;
    the share pages get less still: no inventory and no phone."""
    from leaving_denver import site_builder

    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    seen: dict[str, dict] = {}
    real_render = site_builder.render

    def spy(template, **ctx):
        seen.setdefault(template, {}).update(ctx)
        return real_render(template, **ctx)

    monkeypatch.setattr(site_builder, "render", spy)

    data = site_builder.load_inventory_yaml()
    for item in data["items"]:
        item["firm_floor_price"] = 1
        item["internal_notes"] = "private note"
    data["seller"]["phone"] = "+15555550199"
    site_builder.build_public_site(data)

    assert set(seen["share.html"]) == {"locale", "t", "og", "target"}
    assert set(seen["seller.html"]) == {"items_json", "config_json", "replies", "sealed_json"}
    assert set(seen["index.html"]) == {
        "inventory_json",
        "contact_json",
        "ui_json",
        "locale",
        "t",
        "asset_prefix",
        "build_sha",
        "language_links",
        "alternates",
        "seller",
        "copy",
        "vehicle",
        "items",
        "chips",
        "bundles",
        "everything",
        "og",
    }
    context = json.dumps(seen)
    for private in ("firm_floor_price", "internal_notes", "private note", "5555550199"):
        assert private not in context, f"{private} reached the page template"


def test_unpublished_items_absent_from_public_build():
    """Nothing held back with `published: false` is in the built public site."""
    import yaml

    data = yaml.safe_load((BASE_DIR / "data" / "inventory.yaml").read_text(encoding="utf-8"))
    hidden = {i["id"] for i in data["items"] if i.get("published", True) is False}
    for p in DIST_DIR.rglob("*"):
        text = str(p.relative_to(DIST_DIR))
        if p.is_file() and p.suffix in {".html", ".txt", ""}:
            text += p.read_text(encoding="utf-8")
        for item_id in hidden:
            assert item_id not in text, f"Unpublished {item_id} found in {p}"
