"""
The catalog's sheet and contact flows, run in headless Chrome over the built pages (TEST-001).
test_native_dialogs.py and test_desktop_contact.py check that the handlers are in the script;
these check what they do: which sheets are open, where history stands, and what a text link
does with and without a mouse. Escape and the backdrop are real key and mouse input.
Harness: browser_harness.py.
"""

import pytest
import yaml
from browser_harness import ROOT, needs_chrome, open_page, page_items, pointer, run_page

pytestmark = needs_chrome

EN = yaml.safe_load((ROOT / "locales" / "en.yaml").read_text(encoding="utf-8"))

# The top-left corner is backdrop in headless Chrome's window: a sheet is at most 672 px wide
# and 90% of the viewport tall. test_a_press_on_the_backdrop_closes_the_sheet checks it.
BACKDROP = (5, 5)

SETTLED = """
await until(() => history.state === null);
return { open: sheets(), state: history.state, page: location.pathname };
"""

# A text link records whether the page kept its default action (the native sms: hand-off). The
# window listener runs after the page's document listener, then stops the navigation itself.
CLICKS = """
const CLICKS = [];
window.addEventListener('click', e => {
  if (!e.target.closest('a[href^="sms:"]')) return;
  CLICKS.push(e.defaultPrevented);
  e.preventDefault();
});
"""

CLIPBOARD = """
const COPIED = [];
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
  writeText: text => { COPIED.push(text); return %s; } } });
"""


@pytest.fixture(scope="module")
def item():
    _, _, items = page_items("index.html")
    return items[0]


def open_item(browser, item):
    return browser.run(f"openModal({item!r}); await until(() => history.state); return sheets();")


def assert_closed_onto_the_catalog(result):
    assert result["open"] == []
    assert result["state"] is None
    assert result["page"].endswith("/index.html")


def test_the_close_button_closes_the_sheet_and_its_history_entry(tmp_path, item):
    with open_page(tmp_path, "index.html") as browser:
        assert open_item(browser, item) == ["itemSheet"]
        browser.run("document.querySelector('#itemSheet button[aria-label]').click();")
        assert_closed_onto_the_catalog(browser.run(SETTLED))


def test_escape_closes_the_sheet_and_its_history_entry(tmp_path, item):
    with open_page(tmp_path, "index.html") as browser:
        assert open_item(browser, item) == ["itemSheet"]
        browser.key("Escape", 27)
        assert_closed_onto_the_catalog(browser.run(SETTLED))


def test_a_press_on_the_backdrop_closes_the_sheet(tmp_path, item):
    with open_page(tmp_path, "index.html") as browser:
        assert open_item(browser, item) == ["itemSheet"]
        # The panel fills the dialog, so the only way to click the dialog itself is from its
        # ::backdrop (public.css); padding on the dialog would make a tap beside the panel close.
        boxes = browser.run(
            "const box = e => { const r = e.getBoundingClientRect();"
            "  return [r.left, r.top, r.width, r.height]; };"
            "const sheet = document.getElementById('itemSheet');"
            "return [box(sheet), box(sheet.firstElementChild)];"
        )
        dialog, panel = boxes
        assert dialog == panel
        assert dialog[0] > BACKDROP[0] and dialog[1] > BACKDROP[1], f"{BACKDROP} is in {dialog}"
        browser.drag(BACKDROP, BACKDROP)
        assert_closed_onto_the_catalog(browser.run(SETTLED))


def test_a_drag_from_the_panel_onto_the_backdrop_keeps_the_sheet(tmp_path, item):
    with open_page(tmp_path, "index.html") as browser:
        open_item(browser, item)
        title = browser.run(
            "const r = document.getElementById('modalTitle').getBoundingClientRect();"
            "return [r.left + 5, r.top + r.height / 2];"
        )
        browser.drag(tuple(title), BACKDROP)
        result = browser.run("await wait(200); return { open: sheets(), state: history.state };")
    assert result == {"open": ["itemSheet"], "state": {"sheet": "itemSheet"}}


@pytest.mark.parametrize("opener", ["contact", "bundle"])
def test_the_close_button_of_other_sheets_closes_them(tmp_path, opener):
    open_it = {
        "contact": "document.querySelector('[data-sms-role=\"sticky-text\"]').click();",
        "bundle": "document.querySelector('.bundle-card').click();",
    }[opener]
    steps = f"""
    {open_it}
    await until(() => history.state);
    const opened = sheets();
    document.querySelector('dialog.sheet[open] [data-close-sheet]').click();
    {SETTLED}
    """
    result = run_page(tmp_path, "index.html", steps, setup=pointer(fine=True))
    assert_closed_onto_the_catalog(result)


def test_a_sheet_opened_twice_owns_one_history_entry(tmp_path, item):
    steps = f"""
    const before = history.length;
    openModal({item!r});
    openModal({item!r});
    await until(() => history.state);
    const added = history.length - before;
    history.back();
    {SETTLED.replace("return {", "return { added,")}
    """
    result = run_page(tmp_path, "index.html", steps)
    assert result["added"] == 1
    assert_closed_onto_the_catalog(result)


def test_a_reload_with_a_sheet_open_leaves_no_stale_entry(tmp_path, item):
    with open_page(tmp_path, "index.html") as browser:
        open_item(browser, item)
        browser.send("Page.reload")
        browser.wait_for("Page.loadEventFired")
        result = browser.run(
            "await until(() => document.readyState === 'complete' && history.state === null);"
            "return { open: sheets(), state: history.state, page: location.pathname };"
        )
    assert_closed_onto_the_catalog(result)


def test_back_closes_the_sheet_and_stays_on_the_catalog(tmp_path, item):
    with open_page(tmp_path, "index.html") as browser:
        open_item(browser, item)
        browser.run("history.back();")
        assert_closed_onto_the_catalog(browser.run(SETTLED))


def test_back_closes_a_contact_sheet_over_an_item_one_level_at_a_time(tmp_path, item):
    steps = f"""
    openModal({item!r});
    await until(() => history.state);
    document.getElementById('modalSmsLink').click();
    await until(() => history.state.sheet === 'contactSheet');
    const stacked = sheets();
    history.back();
    await until(() => sheets().length < 2);
    await wait(100);
    const first = {{ open: sheets(), state: history.state }};
    history.back();
    await until(() => history.state === null);
    return {{ stacked, first, second: {{ open: sheets(), state: history.state }} }};
    """
    result = run_page(tmp_path, "index.html", steps, setup=pointer(fine=True))
    assert result["stacked"] == ["itemSheet", "contactSheet"]
    assert result["first"] == {"open": ["itemSheet"], "state": {"sheet": "itemSheet"}}
    assert result["second"] == {"open": [], "state": None}


def test_escape_closes_a_contact_sheet_over_an_item_one_level(tmp_path, item):
    # The text link is clicked for real: Chrome groups dialogs opened with no user activation
    # in between, and one Escape then closes the whole group. A buyer always clicks.
    with open_page(tmp_path, "index.html", setup=pointer(fine=True)) as browser:
        link = browser.run(
            f"openModal({item!r}); await until(() => history.state);"
            "const text = document.getElementById('modalSmsLink');"
            "text.scrollIntoView({ block: 'center' });"
            "const r = text.getBoundingClientRect();"
            "return [r.left + r.width / 2, r.top + r.height / 2];"
        )
        browser.drag(tuple(link), tuple(link))
        assert browser.run(
            "await until(() => history.state.sheet === 'contactSheet'); return sheets();"
        ) == ["itemSheet", "contactSheet"]
        browser.key("Escape", 27)
        result = browser.run(
            "await until(() => history.state && history.state.sheet === 'itemSheet');"
            "await wait(100);"
            "return { open: sheets(), state: history.state };"
        )
    assert result == {"open": ["itemSheet"], "state": {"sheet": "itemSheet"}}


def contact(tmp_path, clipboard):
    steps = """
    const link = document.querySelector('[data-sms-role="sticky-text"]');
    link.click();
    const shown = {
      open: sheets(),
      number: document.getElementById('contactNumber').textContent,
      message: document.getElementById('contactMessage').textContent,
      native: document.getElementById('contactSms').href === link.href,
    };
    const button = document.getElementById('contactCopy');
    const before = button.textContent;
    button.click();
    await until(() => button.textContent !== before);
    return { ...shown, clicks: CLICKS, copied: COPIED, label: button.textContent,
      selected: String(getSelection()) };
    """
    return run_page(
        tmp_path,
        "index.html",
        steps,
        setup=pointer(fine=True) + CLICKS + CLIPBOARD % clipboard,
    )


def digits(text):
    return "".join(ch for ch in text if ch.isdigit())


def test_a_text_link_with_a_mouse_opens_the_contact_sheet(tmp_path):
    result = contact(tmp_path, "Promise.resolve()")
    assert result["clicks"] == [True]
    assert result["open"] == ["contactSheet"]
    assert len(digits(result["number"])) == 10
    assert result["message"] == EN["sms_generic"]
    assert result["native"] is True
    assert len(result["copied"]) == 1
    assert digits(result["copied"][0]).endswith(digits(result["number"]))
    assert result["label"] == EN["copied"]


def test_a_refused_clipboard_selects_the_number(tmp_path):
    result = contact(tmp_path, "Promise.reject(new DOMException('stubbed', 'NotAllowedError'))")
    assert result["selected"] == result["number"]
    assert result["label"] == EN["copy_fallback"]


def test_an_item_text_link_carries_its_message_into_the_contact_sheet(tmp_path):
    steps = """
    const link = document.querySelector('[data-sms-intent]');
    link.click();
    return { open: sheets(), message: document.getElementById('contactMessage').textContent,
      intent: link.getAttribute('data-sms-intent') };
    """
    result = run_page(tmp_path, "index.html", steps, setup=pointer(fine=True))
    assert result["open"] == ["contactSheet"]
    assert result["message"] == result["intent"]


def test_the_contact_sheets_own_link_hands_off_to_messages(tmp_path):
    steps = """
    document.querySelector('[data-sms-role="sticky-text"]').click();
    document.getElementById('contactSms').click();
    await wait(100);
    return { open: sheets(), clicks: CLICKS };
    """
    result = run_page(tmp_path, "index.html", steps, setup=pointer(fine=True) + CLICKS)
    assert result["clicks"] == [True, False]
    assert result["open"] == ["contactSheet"]


def test_a_text_link_on_a_touch_screen_keeps_the_native_hand_off(tmp_path):
    steps = """
    document.querySelector('[data-sms-role="sticky-text"]').click();
    document.querySelector('[data-sms-intent]').click();
    await wait(100);
    return { open: sheets(), clicks: CLICKS, state: history.state };
    """
    result = run_page(tmp_path, "index.html", steps, setup=pointer(fine=False) + CLICKS)
    assert result == {"open": [], "clicks": [False, False], "state": None}


def test_a_linked_item_opens_and_drops_the_hash(tmp_path, item):
    steps = """
    return { open: sheets(), hash: location.hash, state: history.state,
      title: document.getElementById('modalTitle').textContent,
      expected: INVENTORY.items.find(i => i.id === %r).title };
    """
    result = run_page(tmp_path, "index.html", steps % item, fragment=item)
    assert result["open"] == ["itemSheet"]
    assert result["hash"] == ""
    assert result["state"] == {"sheet": "itemSheet"}
    assert result["title"] == result["expected"]


def test_an_unknown_linked_item_opens_nothing(tmp_path):
    steps = "return { open: sheets(), hash: location.hash, state: history.state };"
    result = run_page(tmp_path, "index.html", steps, fragment="no-such-item")
    assert result == {"open": [], "hash": "", "state": None}
