"""
The control panel never reaches the public build (FEAT-004).

It holds floors, targets, sale prices and listing history, so these tests fail if a panel file
lands under build/public/, if the build tolerates one there, or if any value of the fake
private fixture shows up in a public build made while that data is loaded.
"""

import re
from datetime import date
from pathlib import Path

import pytest
import yaml

from leaving_denver import panel, site_builder
from leaving_denver.config import PANEL_MARKER

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "private.example.yaml"
PUBLIC = ROOT / "build" / "public"
TEXT_SUFFIXES = {".html", ".txt", ".json", ".mjs", ".js", ""}


def private_fixture():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def fixture_values(private):
    """Every number and date the fixture holds for the owner's eyes only."""
    found: set[str] = set()

    def walk(node, under_seller=False):
        if isinstance(node, dict):
            for key, value in node.items():
                if key != "seller":
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, (int, str)):
            found.add(str(node))

    walk(private)
    return {v for v in found if re.fullmatch(r"\d+|\d{4}-\d{2}-\d{2}", v)}


def text_of(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8", errors="ignore")
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in TEXT_SUFFIXES
    }


def leaked(values, files):
    pattern = {v: re.compile(rf"(?<![\w.-]){re.escape(v)}(?![\w])") for v in values}
    return sorted(
        (v, name) for name, text in files.items() for v, p in pattern.items() if p.search(text)
    )


def test_the_built_public_site_has_no_panel_file():
    assert PUBLIC.exists(), "build the site first (make test does)"
    assert not [p for p in PUBLIC.rglob("*") if "panel" in p.name.lower()]
    assert PANEL_MARKER not in "".join(text_of(PUBLIC).values())


def test_the_build_fails_when_a_panel_file_is_in_the_public_dist(tmp_path, monkeypatch):
    monkeypatch.setattr(site_builder, "DIST_DIR", tmp_path)
    (tmp_path / "panel.html").write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SECURITY LEAK"):
        site_builder.verify_security_guarantees()


def test_the_build_fails_when_a_public_page_carries_the_panel(tmp_path, monkeypatch):
    monkeypatch.setattr(site_builder, "DIST_DIR", tmp_path)
    (tmp_path / "index.html").write_text(f"<html {PANEL_MARKER}>", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SECURITY LEAK"):
        site_builder.verify_security_guarantees()


def test_the_panel_refuses_to_be_written_under_the_public_build(tmp_path, monkeypatch):
    monkeypatch.setattr(panel, "DIST_DIR", tmp_path / "public")
    with pytest.raises(RuntimeError, match="public build"):
        panel.write_panel("x", tmp_path / "public" / "deep" / "panel.html")
    # A path that climbs back into the public dir is the same place.
    with pytest.raises(RuntimeError, match="public build"):
        panel.write_panel("x", tmp_path / "public" / ".." / "public" / "panel.html")
    assert not (tmp_path / "public").exists()


def test_the_default_panel_path_is_private_and_outside_the_public_build():
    out = panel.PRIVATE_PANEL_HTML.resolve()
    assert not out.is_relative_to(site_builder.DIST_DIR.resolve())
    assert out.is_relative_to(site_builder.DIST_PRIVATE_DIR.resolve())
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "build/" in ignored  # the whole of build/, so panel.html is never committed
    assert "build/public" in (ROOT / "wrangler.toml").read_text(encoding="utf-8")


def build_public(dist, monkeypatch, data):
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    site_builder.build_public_site(data)


def test_no_private_fixture_value_reaches_a_public_build(tmp_path, monkeypatch):
    """Build the public site twice, once clean and once with every private fixture value loaded
    (as decrypted data, as item fields and in a panel written beside it): the public trees match,
    and none of the fixture's numbers or dates is in the second."""
    private = private_fixture()
    clean = site_builder.load_inventory_yaml()
    build_public(tmp_path / "clean", monkeypatch, clean)
    baseline = text_of(tmp_path / "clean")

    loaded = site_builder.load_inventory_yaml()
    for item in loaded["items"]:
        item_id = item["id"]
        item["firm_floor_price"] = private["floors"].get(item_id)
        item["target"] = private["targets"].get(item_id)
        item["sale"] = private["sales"].get(item_id)
        item["tracking"] = private["tracking"].get(item_id)
    monkeypatch.setattr(site_builder, "load_private", lambda: private)
    monkeypatch.setattr(site_builder, "floors", lambda *a: private["floors"])
    build_public(tmp_path / "loaded", monkeypatch, loaded)
    rows = panel.panel_rows(loaded, private, date(2026, 10, 7))
    panel.write_panel(
        panel.render_panel(rows, date(2026, 10, 7)), tmp_path / "private" / "panel.html"
    )

    after = text_of(tmp_path / "loaded")
    assert after == baseline, "private data changed the public build"
    assert not [p for p in (tmp_path / "loaded").rglob("*") if "panel" in p.name.lower()]

    # Values that already appear in a clean build prove nothing; the rest must be absent.
    discriminating = {v for v in fixture_values(private) if not leaked({v}, baseline)}
    assert len(discriminating) >= 8, "the fixture no longer discriminates; pick distinctive numbers"
    assert leaked(discriminating, after) == []
    # The panel itself carries the marker the build guard looks for, and the values.
    assert PANEL_MARKER in text_of(tmp_path / "private")["panel.html"]
    # (that is, the scan is able to see them): the scan is able to see them.
    shown = text_of(tmp_path / "private")["panel.html"]
    assert leaked({"173", "191", "10650"}, {"panel.html": shown})
