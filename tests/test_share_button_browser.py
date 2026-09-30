"""
The Share button's behaviour, run in headless Chrome over the built pages (FEAT-002 PR 2).
The Web Share API and the clipboard are stubbed per case, the page's own openModal and
click handler run unchanged, and the outcome is read back from the dumped DOM. Skipped
where no Chrome is installed; GitHub's ubuntu runners have one.
"""

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
CHROME = next(
    (p for p in map(shutil.which, ("google-chrome", "chromium", "chromium-browser")) if p), None
)
pytestmark = pytest.mark.skipif(CHROME is None, reason="no Chrome to run the page in")

# Runs before the page script. navigator.share and navigator.clipboard become the case's
# stubs; after the page's own DOMContentLoaded work, the sheet opens and Share is clicked.
HARNESS = """<script>
const CASE = %s, LOG = [];
const answer = outcome => outcome === 'ok' ? Promise.resolve()
  : Promise.reject(new DOMException('stubbed', outcome));
Object.defineProperty(navigator, 'share', { configurable: true, value: CASE.share
  && (data => { LOG.push('share ' + data.url); return answer(CASE.share); }) });
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: CASE.clipboard
  && { writeText: text => { LOG.push('copy ' + text); return answer(CASE.clipboard); } } });
document.addEventListener('DOMContentLoaded', () => setTimeout(async () => {
  openModal(CASE.item);
  document.getElementById('modalShare').click();
  await new Promise(done => setTimeout(done, 50));
  if (CASE.reopen) openModal(CASE.reopen);
  const box = document.getElementById('modalShareUrl');
  document.body.dataset.result = JSON.stringify({
    log: LOG,
    label: document.getElementById('modalShare').textContent.trim(),
    box: box.hidden ? null : box.textContent,
    selected: String(getSelection()),
  });
}));
</script>
"""


def page_items(page):
    html = (PUBLIC / page).read_text(encoding="utf-8")
    og_url = re.search(r'<meta property="og:url" content="([^"]+)"', html).group(1)
    return html, og_url, re.findall(r'data-item="([^"]+)"', html)


def run(tmp_path, page, case):
    html, _, _ = page_items(page)
    first_script = html.index("<script>")
    staged = tmp_path / page
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text(
        html[:first_script] + HARNESS % json.dumps(case) + html[first_script:], encoding="utf-8"
    )
    dom = subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=5000",
            "--dump-dom",
            staged.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    ).stdout
    found = re.search(r'data-result="([^"]*)"', dom)
    assert found, "the harness never reported: the page script failed before Share ran"
    return json.loads(unescape(found.group(1)))


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
