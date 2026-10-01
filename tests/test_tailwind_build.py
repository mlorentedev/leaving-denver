"""Compiled CSS is shipped with each catalog and the private assistant."""

import json
from pathlib import Path

import pytest
from test_class_coverage import css_classes

from leaving_denver import site_builder
from leaving_denver.cli import resolve_request_path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
PRIVATE = ROOT / "build" / "private"


@pytest.mark.parametrize(
    "page,href",
    [(PUBLIC / "index.html", "styles.css"), (PUBLIC / "es" / "index.html", "../styles.css")],
)
def test_public_pages_ship_local_css(page, href):
    html = page.read_text(encoding="utf-8")
    assert f'<link rel="stylesheet" href="{href}">' in html
    assert "cdn.tailwindcss.com" not in html
    assert (page.parent / href).is_file()


def test_private_assistant_uses_local_css():
    template = (ROOT / "src" / "leaving_denver" / "templates" / "poster_assistant.html").read_text(
        encoding="utf-8"
    )
    assert "cdn.tailwindcss.com" not in template
    assert PRIVATE.joinpath("styles.css").is_file()
    if PRIVATE.joinpath("poster_assistant.html").exists():
        html = PRIVATE.joinpath("poster_assistant.html").read_text(encoding="utf-8")
        assert '<link rel="stylesheet" href="/private/styles.css">' in html
        assert resolve_request_path("/private/styles.css") == PRIVATE / "styles.css"
        assert "cdn.tailwindcss.com" not in html
    assert not PUBLIC.joinpath("poster_assistant.html").exists()
    assert not PUBLIC.joinpath("inventory.json").exists()


def test_compiled_css_contains_v4_utilities():
    # Parsed class sets, not minified bytes: a Tailwind bump may reorder declarations.
    public_css = PUBLIC.joinpath("styles.css").read_text(encoding="utf-8")
    private_css = PRIVATE.joinpath("styles.css").read_text(encoding="utf-8")
    public, private = css_classes(public_css), css_classes(private_css)
    assert {"aspect-4/3", "shadow-2xs", "backdrop-blur-xs", "group-hover:scale-101"} <= public
    assert {"aspect-4/3", "shadow-2xs"} <= private
    assert "Plus Jakarta Sans" in public_css
    assert "Plus Jakarta Sans" in private_css
    assert "firm_floor_price" not in public_css
    assert "firm_floor_price" not in private_css


def test_package_declares_the_node_it_needs():
    # @tailwindcss/oxide requires node >= 20; CI runs 24.
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["engines"]["node"] == ">=20"


def test_missing_cli_fails_direct_build(monkeypatch, tmp_path):
    # A stylesheet from an earlier build must not let a broken toolchain pass.
    stale = tmp_path / "public" / "styles.css"
    stale.parent.mkdir()
    stale.write_text(".old{}", encoding="utf-8")
    monkeypatch.setattr(site_builder, "DIST_DIR", stale.parent)
    monkeypatch.setattr(
        site_builder, "CSS_CLI", ROOT / "node_modules" / "nonexistent-cli", raising=False
    )
    monkeypatch.setattr(site_builder, "sync_all_photos", lambda: {})
    monkeypatch.setattr(site_builder, "load_inventory_yaml", lambda: {"items": []})
    monkeypatch.setattr(site_builder, "build_public_site", lambda _: None)
    monkeypatch.setattr(site_builder, "build_private_workspace", lambda _: None)
    monkeypatch.setattr(site_builder, "verify_security_guarantees", lambda: None)
    with pytest.raises(RuntimeError, match="npm ci"):
        site_builder.build_all()
    assert stale.read_text(encoding="utf-8") == ".old{}"
