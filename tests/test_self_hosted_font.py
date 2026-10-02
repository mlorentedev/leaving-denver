"""The catalog font ships with each build (PERF-001): no third-party font requests."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
TEMPLATES = ROOT / "src" / "leaving_denver" / "templates"


@pytest.mark.parametrize(
    "path",
    [TEMPLATES / "index.html", TEMPLATES / "seller.html"],
    ids=["catalog", "seller"],
)
def test_no_google_fonts(path):
    html = path.read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html


@pytest.mark.parametrize("root", [PUBLIC], ids=["public"])
def test_stylesheet_font_face_points_at_a_built_file(root):
    css = (root / "styles.css").read_text(encoding="utf-8")
    faces = re.findall(r"@font-face\{[^}]*\}", css)
    assert any("Plus Jakarta Sans" in face for face in faces), "no @font-face for the theme font"
    for face in faces:
        for url in re.findall(r"url\(([^)]+)\)", face):
            assert (root / url.strip("\"'")).is_file(), f"@font-face names a missing file: {url}"


@pytest.mark.parametrize(
    "page", [PUBLIC / "index.html", PUBLIC / "es" / "index.html"], ids=["en", "es"]
)
def test_catalog_preloads_the_font(page):
    html = page.read_text(encoding="utf-8")
    preload = re.search(r'<link rel="preload" href="([^"]+\.woff2)" as="font"[^>]*>', html)
    assert preload, "font is not preloaded"
    assert "crossorigin" in preload.group(0), "a font preload without crossorigin is fetched twice"
    assert (page.parent / preload.group(1)).resolve().is_file()
