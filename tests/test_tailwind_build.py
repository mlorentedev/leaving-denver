"""Compiled CSS is shipped with each catalog and the private assistant."""

from pathlib import Path

import pytest

from leaving_denver import site_builder

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
        assert '<link rel="stylesheet" href="styles.css">' in html
        assert "cdn.tailwindcss.com" not in html
    assert not PUBLIC.joinpath("poster_assistant.html").exists()
    assert not PUBLIC.joinpath("inventory.json").exists()


def test_compiled_css_contains_v4_utilities():
    public = PUBLIC.joinpath("styles.css").read_text(encoding="utf-8")
    private = PRIVATE.joinpath("styles.css").read_text(encoding="utf-8")
    assert r".aspect-4\/3{aspect-ratio:4/3}" in public
    assert r".aspect-4\/3{aspect-ratio:4/3}" in private
    for rule in (
        ".shadow-2xs{--tw-shadow:",
        ".backdrop-blur-xs{--tw-backdrop-blur:",
        r".group-hover\:scale-101:is(:where(.group):hover *){--tw-scale-x:101%",
    ):
        assert rule in public
    assert ".shadow-2xs{" in private
    assert "Plus Jakarta Sans" in public
    assert "Plus Jakarta Sans" in private
    assert "firm_floor_price" not in public
    assert "firm_floor_price" not in private


def test_missing_cli_fails_direct_build(monkeypatch):
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
