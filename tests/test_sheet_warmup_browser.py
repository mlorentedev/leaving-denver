"""
The first tap on a card is the slow one (INP, issue #213): it pays for the number formatter's
first use and for the sheet's first style pass. The page pays both once it has loaded and is idle,
so the tap does not. A timing assertion would be a flaky one; these check what the warm-up does
(it ran before any tap) and what it must not do (leave a trace on the page). Harness:
browser_harness.py.
"""

import pytest
from browser_harness import needs_chrome, run_page

pytestmark = needs_chrome

# Counts what the warm-up touches, before the page's own script: the formatter, and a layout read
# (`offsetHeight`) on the item sheet's first child, which is how the sheet is styled without being
# opened. Events the sheet fires are recorded too: opening it would fire none until closed, but a
# warm-up that opened and closed it would leave a `close`.
SPY = """
window.__fmt = 0;
window.__fmtAtLoad = null;
window.__layout = 0;
// Registered before the page's own load listener: what the formatter did by then is the page's
// rendering, not the warm-up, which only starts from that listener.
addEventListener('load', () => { window.__fmtAtLoad = window.__fmt; }, { once: true });
window.__sheetEvents = [];
window.__historyLength = history.length;
const toLocaleString = Number.prototype.toLocaleString;
Number.prototype.toLocaleString = function (...args) { window.__fmt++; return toLocaleString.apply(this, args); };
const offsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
  configurable: true,
  get() {
    if (this.parentElement && this.parentElement.id === 'itemSheet') window.__layout++;
    return offsetHeight.get.call(this);
  },
});
document.addEventListener('DOMContentLoaded', () => {
  for (const kind of ['close', 'cancel', 'toggle']) {
    document.getElementById('itemSheet').addEventListener(kind, () => window.__sheetEvents.push(kind));
  }
});
"""

WARMED = """
await until(() => window.__fmtAtLoad !== null && window.__fmt > window.__fmtAtLoad && window.__layout > 0, 8000);
await wait(300);
const sheet = document.getElementById('itemSheet');
return {
  formatted: window.__fmt, formattedAtLoad: window.__fmtAtLoad, layouts: window.__layout,
  open: sheet.open, sheets: sheets(), displayStyle: sheet.style.display,
  events: window.__sheetEvents, historyLength: history.length, was: window.__historyLength,
  state: history.state, focus: document.activeElement.tagName,
};
"""


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
def test_the_page_warms_the_sheet_before_any_tap_and_leaves_no_trace(tmp_path, page):
    result = run_page(tmp_path, page, WARMED, setup=SPY)
    # It ran: the formatter was used after load, and the sheet's subtree was laid out, with no tap.
    assert result["formatted"] > result["formattedAtLoad"]
    assert result["layouts"] > 0
    # And it left nothing: the sheet is closed, shows no inline display, fired no event, took no
    # history entry, and did not move focus off the page.
    assert result["open"] is False
    assert result["sheets"] == []
    assert result["displayStyle"] == ""
    assert result["events"] == []
    assert result["historyLength"] == result["was"]
    assert result["state"] is None
    assert result["focus"] == "BODY"


OPENS_AFTER = """
await until(() => window.__layout > 0, 8000);
await wait(300);
const item = INVENTORY.items.find(i => i.price > 999) || INVENTORY.items[0];
openModal(item.id);
return {
  sheets: sheets(), price: document.getElementById('modalPrice').textContent,
  expected: item.free ? item.note : '$' + item.price.toLocaleString(),
  title: document.getElementById('modalTitle').textContent, expectedTitle: item.title,
};
"""


def test_a_warmed_sheet_opens_with_the_same_content(tmp_path):
    result = run_page(tmp_path, "index.html", OPENS_AFTER, setup=SPY)
    assert result["sheets"] == ["itemSheet"]
    assert result["price"] == result["expected"]
    assert result["title"] == result["expectedTitle"]


# A sheet opened before the page is idle already paid: the warm-up stands down. A press that
# opens nothing (a scroll starts with one on a phone, on a card or not) leaves it armed.
BEFORE_IDLE = """
document.addEventListener('DOMContentLoaded', () => {
  %s
});
"""
OPENS_A_SHEET = "openModal(INVENTORY.items[0].id); document.getElementById('itemSheet').close();"
PRESSES = (
    "for (const target of [document.querySelector('.item-card'), document.body]) "
    "target.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));"
)

NOT_WARMED = """
await until(() => window.__fmtAtLoad !== null, 8000);
await wait(2500);
return { layouts: window.__layout };
"""


def test_a_sheet_opened_before_idle_skips_the_warm_up(tmp_path):
    result = run_page(tmp_path, "index.html", NOT_WARMED, setup=SPY + BEFORE_IDLE % OPENS_A_SHEET)
    assert result["layouts"] == 0


def test_a_press_that_opens_nothing_leaves_the_warm_up_armed(tmp_path):
    result = run_page(tmp_path, "index.html", WARMED, setup=SPY + BEFORE_IDLE % PRESSES)
    assert result["formatted"] > result["formattedAtLoad"]
    assert result["layouts"] > 0
