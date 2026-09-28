"""
Security and isolation regression tests.
Verifies that no private seller data leaks into the public distribution (build/public/).
"""

import json
import re
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "build" / "public"
DIST_PRIVATE_DIR = BASE_DIR / "build" / "private"


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
    public_html = (DIST_DIR / "index.html").read_text(encoding="utf-8")
    assert "firm_floor_price" not in public_html, "Leaked firm_floor_price in public HTML!"
    assert "floor_price" not in public_html, "Leaked floor_price in public HTML!"


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


def test_pages_headers():
    headers = (DIST_DIR / "_headers").read_text(encoding="utf-8")
    assert "X-Content-Type-Options: nosniff" in headers
    assert "/catalog/*" in headers
    assert "max-age=" in headers


def test_private_assistant_has_security_gate():
    if not (DIST_PRIVATE_DIR / "poster_assistant.html").exists():
        pytest.skip("private workspace not built (sops file not decryptable here)")
    private_html = (DIST_PRIVATE_DIR / "poster_assistant.html").read_text(encoding="utf-8")
    assert "pinGateModal" in private_html, "Missing PIN gate modal in seller workspace"
    assert "checkPin()" in private_html, "Missing PIN check logic"
    assert "Default: 8011" not in private_html, "Leaked default PIN in placeholder text"
    assert "defaults to DTC zip prefix" not in private_html, "Leaked default PIN hint text"


def test_static_image_paths_exist():
    """Every <img src> written into the page as plain HTML points at a built file."""
    public_html = (DIST_DIR / "index.html").read_text(encoding="utf-8")
    for src in re.findall(r'<img[^>]+src="(catalog/[^"]+)"', public_html):
        assert (DIST_DIR / src).is_file(), f"Broken image path in page: {src}"


def test_template_sees_only_sanitized_data(tmp_path, monkeypatch):
    """The page template gets the sanitized inventory and the phone parts, nothing else."""
    from leaving_denver import site_builder

    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    seen = {}
    real_render = site_builder.render

    def spy(template, **ctx):
        seen.update(ctx)
        return real_render(template, **ctx)

    monkeypatch.setattr(site_builder, "render", spy)

    data = site_builder.load_inventory_yaml()
    for item in data["items"]:
        item["firm_floor_price"] = 1
        item["internal_notes"] = "private note"
    data["seller"]["phone"] = "+15555550199"
    site_builder.build_public_site(data)

    assert set(seen) == {"inventory_json", "contact_json"}
    context = json.dumps(seen)
    for private in ("firm_floor_price", "internal_notes", "private note", "5555550199"):
        assert private not in context, f"{private} reached the page template"
