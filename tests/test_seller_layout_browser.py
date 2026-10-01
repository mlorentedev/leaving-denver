"""
The seller page on a phone, measured in headless Chrome over the built page
(harness: browser_harness.py).
"""

import pytest
from browser_harness import needs_chrome, open_page

pytestmark = needs_chrome

PHONE = {"width": 390, "height": 844, "deviceScaleFactor": 3, "mobile": True}


@pytest.mark.parametrize("width", [320, 390])
def test_the_seller_page_keeps_a_gutter_on_a_phone(tmp_path, width):
    """public.css pads <body> outside any layer, which outranks Tailwind's utilities, so a
    gutter written as a utility on <body> silently drops to 0 and the fields touch the edge."""
    with open_page(tmp_path, "seller/index.html") as browser:
        browser.send("Emulation.setDeviceMetricsOverride", **{**PHONE, "width": width})
        edges = browser.run(
            "await wait(50);"
            "const boxes = [...document.querySelectorAll('main h1, main select, main input,"
            " main textarea, main button')].map(e => e.getBoundingClientRect());"
            "return [Math.min(...boxes.map(r => r.left)),"
            " innerWidth - Math.max(...boxes.map(r => r.right))];"
        )
    assert min(edges) >= 16, edges
