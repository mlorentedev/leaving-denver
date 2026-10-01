"""
The car's verify sheet, run in headless Chrome over the built pages (FEAT-008). The car card's
"Verify it yourself" button opens it through the page's own sheet machinery, so it must behave
like the item, contact and bundle sheets: one history entry, closed by its button, Escape and
Back. test_verify_the_car.py checks what the sheet holds; this checks what a buyer can do with it.
Harness: browser_harness.py.
"""

import pytest
from browser_harness import needs_chrome, open_page, run_page

pytestmark = needs_chrome

PAGES = ["index.html", "es/index.html"]
CAR_ID = "2019-ford-escape-sel-awd"
OFFICIAL_HOSTS = {"nhtsa.gov", "ford.com", "nicb.org"}

OPEN = """
const button = document.querySelector('button[data-open-sheet="verifySheet"]');
const closedBefore = {
  open: sheets(),
  visible: document.querySelector('[data-role="verify-car"]').getClientRects().length > 0,
  state: history.state,
};
button.click();
await until(() => history.state);
"""

SETTLED = """
await until(() => history.state === null);
return { open: sheets(), state: history.state, page: location.pathname };
"""


def opened(tmp_path, page):
    steps = (
        OPEN
        + """
    const sheet = document.getElementById('verifySheet');
    const hosts = [...sheet.querySelectorAll('[data-role="verify-checks"] a')]
      .map(a => new URL(a.href).hostname);
    return { closedBefore, open: sheets(), state: history.state,
      visible: sheet.querySelector('[data-role="verify-car"]').getClientRects().length > 0,
      vin: sheet.querySelector('[data-role="vin"]').textContent, hosts,
      heading: sheet.querySelector('h3').textContent,
      focus: sheet.contains(document.activeElement) };
    """
    )
    return run_page(tmp_path, page, steps)


@pytest.mark.parametrize("page", PAGES)
def test_the_button_opens_the_sheet_with_the_vin_and_the_three_official_links(tmp_path, page):
    result = opened(tmp_path, page)
    assert result["closedBefore"] == {"open": [], "visible": False, "state": None}
    assert result["open"] == ["verifySheet"]
    assert result["state"] == {"sheet": "verifySheet"}
    assert result["visible"] is True
    assert len(result["vin"]) == 17
    assert result["focus"] is True
    assert len(result["hosts"]) == 3
    for domain in OFFICIAL_HOSTS:
        assert any(h == domain or h.endswith("." + domain) for h in result["hosts"]), domain


def assert_closed_onto_the_catalog(result):
    assert result["open"] == []
    assert result["state"] is None
    assert result["page"].endswith("index.html")


def test_the_close_button_closes_the_sheet_and_its_history_entry(tmp_path):
    steps = OPEN + "document.querySelector('#verifySheet [data-close-sheet]').click();" + SETTLED
    assert_closed_onto_the_catalog(run_page(tmp_path, "index.html", steps))


def test_back_closes_the_sheet_and_stays_on_the_catalog(tmp_path):
    steps = OPEN + "history.back();" + SETTLED
    assert_closed_onto_the_catalog(run_page(tmp_path, "index.html", steps))


def test_escape_closes_the_sheet_and_its_history_entry(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        browser.run(OPEN)
        browser.key("Escape", 27)
        assert_closed_onto_the_catalog(browser.run(SETTLED))


def test_a_press_on_the_backdrop_closes_the_sheet(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        browser.run(OPEN)
        browser.drag((5, 5), (5, 5))
        assert_closed_onto_the_catalog(browser.run(SETTLED))


def test_the_sheet_can_be_reopened_after_closing(tmp_path):
    steps = (
        OPEN
        + "history.back(); await until(() => history.state === null);"
        + "button.click(); await until(() => history.state);"
        + "return { open: sheets(), state: history.state };"
    )
    result = run_page(tmp_path, "index.html", steps)
    assert result == {"open": ["verifySheet"], "state": {"sheet": "verifySheet"}}


def test_the_cars_deep_link_still_opens_the_item_sheet_and_not_the_verify_sheet(tmp_path):
    steps = "return { open: sheets(), hash: location.hash, state: history.state };"
    result = run_page(tmp_path, "index.html", steps, fragment=CAR_ID)
    assert result == {"open": ["itemSheet"], "hash": "", "state": {"sheet": "itemSheet"}}
