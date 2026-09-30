import xml.etree.ElementTree as ET

import pytest

from leaving_denver.config import DIST_DIR


@pytest.mark.parametrize(
    ("page", "href"),
    [("index.html", "favicon.svg"), ("es/index.html", "../favicon.svg")],
)
def test_public_catalog_locales_use_local_favicon(page, href):
    html = (DIST_DIR / page).read_text(encoding="utf-8")
    assert f'<link rel="icon" type="image/svg+xml" href="{href}">' in html
    assert (DIST_DIR / "favicon.svg").is_file()


def test_favicon_has_colorado_colors_without_external_assets():
    source = (DIST_DIR / "favicon.svg").read_text(encoding="utf-8")
    root = ET.fromstring(source)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert all(color in source for color in ("#003087", "#c8102e", "#f6b218", "#fff"))
    assert "http://" not in source.replace("http://www.w3.org/2000/svg", "")
    assert "https://" not in source
