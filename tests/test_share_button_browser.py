"""
The Share button's behaviour, run in headless Chrome over the built pages (FEAT-002 PR 2).
The Web Share API and the clipboard are stubbed per case, and the page's own openModal and
click handler run unchanged (harness: browser_harness.py).
"""

import json

import pytest
from browser_harness import needs_chrome, page_items, run_page

pytestmark = needs_chrome

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


def run(tmp_path, page, case):
    return run_page(tmp_path, page, STEPS, setup=STUBS % json.dumps(case))


@pytest.fixture(scope="module")
def en():
    _, og_url, items = page_items("index.html")
    return og_url, items


def test_a_cancelled_share_sheet_does_nothing(tmp_path, en):
    og_url, items = en
    result = run(
        tmp_path, "index.html", {"item": items[0], "share": "AbortError", "clipboard": "ok"}
    )
    assert result["log"] == [f"share {og_url}i/{items[0]}/"]
    assert result["label"] == "Share"
    assert result["box"] is None


def test_a_failed_share_copies_the_link(tmp_path, en):
    og_url, items = en
    url = f"{og_url}i/{items[0]}/"
    result = run(
        tmp_path, "index.html", {"item": items[0], "share": "NotAllowedError", "clipboard": "ok"}
    )
    assert result["log"] == [f"share {url}", f"copy {url}"]
    assert result["label"] == "Link copied"


def test_a_refused_clipboard_shows_the_link_selected(tmp_path, en):
    og_url, items = en
    url = f"{og_url}i/{items[0]}/"
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
    assert result["box"] == f"{og_url}i/{items[0]}/"


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
    assert result["log"] == [f"copy {og_url}i/{items[0]}/"]
    assert result["label"] == "Enlace copiado"
