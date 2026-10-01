"""
The VIN's copy button in the car's verify sheet, run in headless Chrome over the built pages
(FEAT-008). A buyer pastes the VIN into NHTSA, Ford and NICB, so one tap must put exactly the
VIN on the clipboard, and a page without a clipboard must still leave it ready to copy.
Harness: browser_harness.py.
"""

import json

import pytest
from browser_harness import needs_chrome, run_page

pytestmark = needs_chrome

STUBS = """
const CASE = %s, LOG = [];
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: CASE.clipboard
  && { writeText: text => { LOG.push(text); return CASE.clipboard === 'ok'
    ? Promise.resolve() : Promise.reject(new DOMException('stubbed', 'NotAllowedError')); } } });
"""

STEPS = """
document.querySelector('button[data-open-sheet="verifySheet"]').click();
await until(() => history.state);
const button = document.getElementById('copyVin');
button.click();
await wait(50);
return {
  log: LOG,
  vin: document.querySelector('#verifySheet [data-role="vin"]').textContent,
  label: button.getAttribute('aria-label'),
  status: document.getElementById('copyVinStatus').textContent,
  selected: String(getSelection()),
};
"""

COPIED = {"index.html": "Copied", "es/index.html": "Copiado"}


def run(tmp_path, page, clipboard):
    return run_page(tmp_path, page, STEPS, setup=STUBS % json.dumps({"clipboard": clipboard}))


@pytest.mark.parametrize("page", COPIED)
def test_the_copy_button_puts_the_vin_on_the_clipboard(tmp_path, page):
    result = run(tmp_path, page, "ok")
    assert len(result["vin"]) == 17
    assert result["log"] == [result["vin"]]
    assert result["status"] == COPIED[page]
    assert result["label"] and "VIN" in result["label"]


@pytest.mark.parametrize("clipboard", [None, "denied"])
def test_without_a_clipboard_the_vin_is_selected_to_copy_by_hand(tmp_path, clipboard):
    result = run(tmp_path, "index.html", clipboard)
    assert result["selected"] == result["vin"]
    assert "Ctrl+C" in result["status"]
