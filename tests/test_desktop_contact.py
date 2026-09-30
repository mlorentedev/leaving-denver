"""
On a desktop `sms:` opens nothing, so a text link shows the number to text from a phone,
with a Copy button (FEAT-003 PR 3). The number is still assembled in JS on click (ADR-002).
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / "build" / "public" / "index.html", ROOT / "build" / "public" / "es" / "index.html")
KEYS = ("contact_heading", "contact_hint", "copy_number", "copied", "results")


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_contact_sheet_ships_empty(page):
    html = page.read_text(encoding="utf-8")
    sheet = re.search(r'<dialog id="contactSheet"[^>]*>(.*?)</dialog>', html, re.S)
    assert sheet, "no contact dialog"
    assert 'aria-labelledby="contactTitle"' in html
    # Filled in on click: no number in the static markup.
    assert re.search(r'<p id="contactNumber"[^>]*></p>', sheet.group(1))
    assert not re.search(r"\(\d{3}\) \d{3}-\d{4}", html)


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_fine_pointer_text_links_open_the_contact_sheet(page):
    js = "".join(re.findall(r"<script>(.*?)</script>", page.read_text(encoding="utf-8"), re.S))
    assert "matchMedia('(hover: hover) and (pointer: fine)')" in js
    assert 'a[href^="sms:"]' in js or "a[href^='sms:']" in js
    assert "navigator.clipboard.writeText" in js


@pytest.mark.parametrize("locale", ["en", "es"])
def test_contact_copy_is_translated(locale):
    copy = yaml.safe_load((ROOT / "locales" / f"{locale}.yaml").read_text(encoding="utf-8"))
    assert all(copy.get(key) for key in KEYS), [k for k in KEYS if not copy.get(k)]


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_sticky_bar_clears_the_home_indicator(page):
    html = page.read_text(encoding="utf-8")
    # env() is 0 unless the page extends under the notch / home indicator.
    assert re.search(r'<meta name="viewport" content="[^"]*viewport-fit=cover', html)
    sticky = re.search(r'<a [^>]*data-sms-role="sticky-text"[^>]*>', html).group(0)
    assert "env(safe-area-inset-bottom)" in sticky


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_filtering_announces_the_result_count(page):
    html = page.read_text(encoding="utf-8")
    assert re.search(r'<p id="resultCount"[^>]*aria-live="polite"', html)
    js = "".join(re.findall(r"<script>(.*?)</script>", html, re.S))
    assert "UI.results" in js and "getElementById('resultCount')" in js
