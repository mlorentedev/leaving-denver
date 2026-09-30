"""
Item and bundle sheets are native modal dialogs (FEAT-003 PR 2): Escape and the backdrop
close them, the page behind is inert and does not scroll, and Back closes an open sheet
instead of leaving the site (Facebook's in-app browser drops the buyer otherwise).
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / "build" / "public" / "index.html", ROOT / "build" / "public" / "es" / "index.html")
CSS = ROOT / "build" / "public" / "styles.css"


def script(html):
    return "".join(re.findall(r"<script>(.*?)</script>", html, re.S))


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_every_sheet_is_a_labelled_dialog(page):
    html = page.read_text(encoding="utf-8")
    item = re.search(r'<dialog id="itemSheet"[^>]*>', html)
    assert item, "item sheet is not a <dialog>"
    assert 'aria-labelledby="modalTitle"' in item.group(0)
    bundles = re.findall(r'<dialog id="sheet-([^"]+)"[^>]*aria-labelledby="sheet-title-\1"', html)
    assert bundles, "bundle sheets are not labelled <dialog>s"
    for bundle_id in bundles:
        assert f'id="sheet-title-{bundle_id}"' in html
    assert not re.search(r'<div id="(itemSheet|sheet-[^"]+)"', html), "a sheet is still a <div>"


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_sheets_open_modally_and_back_closes_them(page):
    js = script(page.read_text(encoding="utf-8"))
    assert ".showModal()" in js, "sheets must open modally (inert background, Escape)"
    assert "history.pushState" in js, "opening a sheet must add a history entry"
    assert "'popstate'" in js, "Back must close the open sheet"
    assert "history.back()" in js, "closing a sheet must drop its history entry"
    assert "classList.toggle('hidden'" not in js.split("function applyFilter")[0], (
        "sheets are still shown by toggling classes"
    )


def test_page_behind_an_open_dialog_does_not_scroll():
    css = CSS.read_text(encoding="utf-8")
    assert re.search(r"html:has\(dialog\[open\]\)\{overflow:hidden", css.replace(" ", ""))
