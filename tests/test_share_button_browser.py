"""
The Share button's behaviour, run in headless Chrome over the built pages (FEAT-002 PR 2).
The Web Share API and the clipboard are stubbed per case, and the page's own openModal and
click handler run unchanged (harness: browser_harness.py).
"""

import json

import pytest
from browser_harness import needs_chrome, page_items, run_page

pytestmark = needs_chrome

# Written out, not read from the page: every shared link counts as word of mouth (FEAT-019).
SHARED = "?utm_source=share&utm_medium=referral&utm_campaign=moving-sale"

# navigator.share and navigator.clipboard become the case's stubs; the sheet opens and
# Share is clicked, and the steps report what was shared or copied and what the sheet shows.
STUBS = """
const CASE = %s, LOG = [];
const answer = outcome => outcome === 'ok' ? Promise.resolve()
  : Promise.reject(new DOMException('stubbed', outcome));
Object.defineProperty(navigator, 'share', { configurable: true, value: CASE.share
  && (data => { LOG.push('share ' + data.url); return answer(CASE.share); }) });
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: CASE.clipboard
  && { writeText: text => { LOG.push('copy ' + text); return answer(CASE.clipboard); } } });
"""

STEPS = """
openModal(CASE.item);
document.getElementById('modalShare').click();
await wait(50);
if (CASE.reopen) openModal(CASE.reopen);
const box = document.getElementById('modalShareUrl');
return {
  log: LOG,
  label: document.getElementById('modalShare').textContent.trim(),
  box: box.hidden ? null : box.textContent,
  selected: String(getSelection()),
};
"""


# The hero's Share: the same stubs, the catalog's own button and fallback box.
HERO_STEPS = """
document.getElementById('catalogShare').click();
await wait(50);
const box = document.getElementById('catalogShareUrl');
return {
  log: LOG,
  label: document.getElementById('catalogShare').textContent.trim(),
  box: box.hidden ? null : box.textContent,
  selected: String(getSelection()),
};
"""


def run(tmp_path, page, case, steps=STEPS):
    return run_page(tmp_path, page, steps, setup=STUBS % json.dumps(case))


@pytest.fixture(scope="module")
def en():
    _, og_url, items = page_items("index.html")
    return og_url, items


def test_a_cancelled_share_sheet_does_nothing(tmp_path, en):
    og_url, items = en
    result = run(
        tmp_path, "index.html", {"item": items[0], "share": "AbortError", "clipboard": "ok"}
    )
    assert result["log"] == [f"share {og_url}i/{items[0]}/{SHARED}"]
    assert result["label"] == "Share"
    assert result["box"] is None


def test_a_failed_share_copies_the_link(tmp_path, en):
    og_url, items = en
    url = f"{og_url}i/{items[0]}/{SHARED}"
    result = run(
        tmp_path, "index.html", {"item": items[0], "share": "NotAllowedError", "clipboard": "ok"}
    )
    assert result["log"] == [f"share {url}", f"copy {url}"]
    assert result["label"] == "Link copied"


def test_a_refused_clipboard_shows_the_link_selected(tmp_path, en):
    og_url, items = en
    url = f"{og_url}i/{items[0]}/{SHARED}"
    result = run(
        tmp_path, "index.html", {"item": items[0], "share": None, "clipboard": "NotAllowedError"}
    )
    assert result["log"] == [f"copy {url}"]
    assert result["box"] == url
    assert result["selected"] == url
    assert result["label"] == "Share"


def test_no_clipboard_at_all_shows_the_link(tmp_path, en):
    og_url, items = en
    result = run(tmp_path, "index.html", {"item": items[0], "share": None, "clipboard": None})
    assert result["box"] == f"{og_url}i/{items[0]}/{SHARED}"


def test_reopening_for_another_item_resets_the_button(tmp_path, en):
    _, items = en
    result = run(
        tmp_path,
        "index.html",
        {"item": items[0], "share": None, "clipboard": "NotAllowedError", "reopen": items[1]},
    )
    assert result["box"] is None
    assert result["label"] == "Share"


def test_the_spanish_page_shares_the_spanish_share_page(tmp_path):
    _, og_url, items = page_items("es/index.html")
    assert og_url.endswith("/es/")
    result = run(tmp_path, "es/index.html", {"item": items[0], "share": None, "clipboard": "ok"})
    assert result["log"] == [f"copy {og_url}i/{items[0]}/{SHARED}"]
    assert result["label"] == "Enlace copiado"


# The hero's Share (FEAT-019): the catalog itself, counted as word of mouth.


def test_the_hero_shares_the_catalog_as_word_of_mouth(tmp_path, en):
    og_url, _ = en
    result = run(tmp_path, "index.html", {"share": "ok", "clipboard": "ok"}, HERO_STEPS)
    assert result["log"] == [f"share {og_url}{SHARED}"]
    assert result["label"] == "Share this sale"


@pytest.mark.parametrize(
    ("case", "log", "label", "box"),
    [
        ({"share": "AbortError", "clipboard": "ok"}, ["share"], "Share this sale", False),
        ({"share": "NotAllowedError", "clipboard": "ok"}, ["share", "copy"], "Link copied", False),
        ({"share": None, "clipboard": "NotAllowedError"}, ["copy"], "Share this sale", True),
    ],
    ids=["cancelled", "failed share copies", "refused clipboard shows it"],
)
def test_the_hero_falls_back_like_the_item_sheet(tmp_path, en, case, log, label, box):
    url = f"{en[0]}{SHARED}"
    result = run(tmp_path, "index.html", case, HERO_STEPS)
    assert result["log"] == [f"{step} {url}" for step in log]
    assert result["label"] == label
    assert result["box"] == (url if box else None)
    if box:
        assert result["selected"] == url


def test_the_spanish_hero_shares_the_spanish_catalog(tmp_path):
    _, og_url, _ = page_items("es/index.html")
    result = run(tmp_path, "es/index.html", {"share": None, "clipboard": "ok"}, HERO_STEPS)
    assert result["log"] == [f"copy {og_url}{SHARED}"]
    assert result["label"] == "Enlace copiado"
