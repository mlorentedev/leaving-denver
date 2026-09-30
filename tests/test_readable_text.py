"""
Text meets WCAG AA (4.5:1) on the ground it sits on and is never under 12 px (FEAT-003).

On the light grounds neutral-400 (#a3a3a3) is 2.52:1 and emerald-600 is 3.76:1. On the
grey panels (neutral-100/200) neutral-500 drops to 4.35:1 as well. On the dark cards
(neutral-900) it runs the other way: neutral-400 is 7.1:1, neutral-500 3.78:1.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "src" / "leaving_denver" / "templates" / "index.html"
PAGES = (ROOT / "build" / "public" / "index.html", ROOT / "build" / "public" / "es" / "index.html")

UNDER_12PX = ("text-[9px]", "text-[10px]", "text-[11px]")
FAILS_ON = {
    "light": {"text-neutral-300", "text-neutral-400", "text-emerald-500", "text-emerald-600"},
    "dark": {"text-neutral-500", "text-neutral-600", "text-neutral-700"},
}
FAILS_ON["grey"] = FAILS_ON["light"] | {"text-neutral-500"}
DARK_GROUNDS = {"bg-neutral-800", "bg-neutral-900", "bg-black", "bg-black/50"}
GREY_GROUNDS = {"bg-neutral-100", "bg-neutral-200"}
GROUND_OF = {**dict.fromkeys(DARK_GROUNDS, "dark"), **dict.fromkeys(GREY_GROUNDS, "grey")}
# Only hover/focus states may change colour; a breakpoint colour would go unchecked below.
RESPONSIVE_COLOUR = re.compile(r"(sm|md|lg|xl|2xl):(text|bg)-(white|black|[a-z]+-\d)")
TEXT_COLOUR = re.compile(r"text-(white|black|[a-z]+-\d{2,3})(/\d+)?")
VOID = {"area", "br", "hr", "img", "input", "link", "meta", "source", "wbr"}


class GroundChecker(HTMLParser):
    """Each element's text colour, set or inherited, against the nearest background."""

    def __init__(self):
        super().__init__()
        self.stack = [("light", None)]
        self.failures = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = [c for c in (attrs.get("class") or "").split() if ":" not in c]
        grounds = [c for c in classes if c.startswith("bg-")]
        colours = [c for c in classes if TEXT_COLOUR.fullmatch(c)]
        ground, colour = self.stack[-1]
        if grounds:
            ground = GROUND_OF.get(grounds[-1], "light")
        if colours:
            colour = colours[-1]
        # Checked where the pair changes; decoration hidden from assistive tech (the EN / ES
        # slash) is exempt, as in WCAG 1.4.3.
        changed = grounds or colours
        if changed and colour in FAILS_ON[ground] and attrs.get("aria-hidden") != "true":
            self.failures.append(f"line {self.getpos()[0]}: {colour} on a {ground} ground")
        if tag not in VOID:
            self.stack.append((ground, colour))

    def handle_endtag(self, tag):
        if tag not in VOID and len(self.stack) > 1:
            self.stack.pop()


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_text_contrast_holds_on_its_ground(page):
    checker = GroundChecker()
    checker.feed(page.read_text(encoding="utf-8"))
    assert not checker.failures, "\n".join(checker.failures)


@pytest.mark.parametrize(
    "markup",
    [
        '<div class="bg-neutral-900"><p class="text-neutral-500">x</p></div>',
        '<div class="text-neutral-500"><p class="bg-neutral-900">inherits the grey</p></div>',
        '<div class="bg-neutral-900 text-neutral-400"><p class="bg-white">inherits the grey</p></div>',
        '<div class="bg-neutral-100"><p class="text-neutral-500">4.35:1</p></div>',
    ],
)
def test_checker_catches_set_and_inherited_colours(markup):
    checker = GroundChecker()
    checker.feed(markup)
    assert checker.failures


def test_colours_do_not_change_at_breakpoints():
    hits = RESPONSIVE_COLOUR.findall(TEMPLATE.read_text(encoding="utf-8"))
    assert not hits, hits


def test_script_built_text_is_readable():
    # Markup built in JS (the dialog's spec bullets) is not parsed above; it is all light.
    scripts = "".join(re.findall(r"<script>(.*?)</script>", TEMPLATE.read_text(), re.S))
    assert not FAILS_ON["light"] & set(re.split(r"[\s'\"`]+", scripts))


@pytest.mark.parametrize("utility", UNDER_12PX)
def test_no_text_under_12px(utility):
    html = TEMPLATE.read_text(encoding="utf-8")
    hits = [
        n
        for n, line in enumerate(html.splitlines(), 1)
        for token in re.split(r"[\s'\"`]+", line)
        if token.split(":")[-1] == utility
    ]
    assert not hits, f"{utility} on template lines {hits}"
