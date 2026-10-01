"""
The flyer on paper (FEAT-010): headless Chrome prints `/flyer/` the way the seller will, from a
browser's print dialog, and it must come out as exactly one US Letter sheet.

`public.css` pads `<body>` for the sticky bar with an unlayered rule (lesson-020); a flyer that
forgot to reset it would pass every markup check and still spill onto a second sheet.
"""

import base64
import re

from browser_harness import needs_chrome, open_page

PAGE = "flyer/index.html"
LETTER_PT = (612, 792)  # 8.5 x 11 in at 72 pt
# What @page { size: letter; margin: 0.5in } leaves for content, in CSS px (96 per inch).
CONTENT_WIDTH_PX, CONTENT_HEIGHT_PX = 720, 960


def printed(tmp_path):
    """The flyer printed to PDF with the page's own @page size, and the layout it printed from."""
    with open_page(tmp_path, PAGE) as browser:
        browser.send("Emulation.setEmulatedMedia", media="print")
        browser.send(
            "Emulation.setDeviceMetricsOverride",
            width=CONTENT_WIDTH_PX,
            height=CONTENT_HEIGHT_PX,
            deviceScaleFactor=1,
            mobile=False,
        )
        pdf = base64.b64decode(
            browser.send("Page.printToPDF", preferCSSPageSize=True, printBackground=True)["data"]
        )
        content = browser.run(
            "const m = document.querySelector('main').getBoundingClientRect();"
            "return {height: Math.ceil(m.bottom + scrollY), "
            "scrollHeight: document.documentElement.scrollHeight, "
            "scrollWidth: document.documentElement.scrollWidth};"
        )
    return pdf, content


@needs_chrome
def test_the_flyer_prints_on_exactly_one_letter_sheet(tmp_path):
    pdf, _ = printed(tmp_path)
    sheets = re.findall(rb"/Type\s*/Page(?![s\w])", pdf)
    assert len(sheets) == 1, f"the flyer prints on {len(sheets)} sheets"
    box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
    assert (round(float(box.group(1))), round(float(box.group(2)))) == LETTER_PT


@needs_chrome
def test_the_flyer_fits_the_letter_content_box(tmp_path):
    _, content = printed(tmp_path)
    assert content["scrollWidth"] <= CONTENT_WIDTH_PX, content
    assert content["scrollHeight"] <= CONTENT_HEIGHT_PX, content
