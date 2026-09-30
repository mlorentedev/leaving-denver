"""
Text meets WCAG AA contrast on the catalog's light grounds and is never under 12 px (FEAT-003).
neutral-400 (#a3a3a3) is 2.52:1 on white and emerald-600 is 3.76:1; their -500/-700 steps pass.
"""

import re
from pathlib import Path

import pytest

TEMPLATE = (
    Path(__file__).resolve().parents[1] / "src" / "leaving_denver" / "templates" / "index.html"
)

# Text utilities under AA (4.5:1) on white/neutral-50, and font sizes under 12 px.
# neutral-300 is left out: the template uses it only on the dark pickup section.
FAILING = {
    "text-neutral-400": "2.52:1",
    "text-emerald-500": "2.54:1",
    "text-emerald-600": "3.76:1",
    "text-[9px]": "under 12 px",
    "text-[10px]": "under 12 px",
    "text-[11px]": "under 12 px",
}


@pytest.mark.parametrize("utility", FAILING)
def test_template_has_no_unreadable_text(utility):
    html = TEMPLATE.read_text(encoding="utf-8")
    # Whole class tokens only, so hover:/sm: variants and border utilities are included
    # when they are text utilities and ignored when they are not.
    hits = [
        n
        for n, line in enumerate(html.splitlines(), 1)
        for token in re.split(r"[\s'\"`]+", line)
        if token.split(":")[-1] == utility
    ]
    assert not hits, f"{utility} ({FAILING[utility]}) on template lines {hits}"
